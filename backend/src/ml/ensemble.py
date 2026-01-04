"""
Multi-objective ensemble ranker for GSAT vocabulary prediction.

Combines multiple prediction perspectives:
1. Traditional ML features (historical patterns)
2. Value estimation (TOPSIS/EVL)
3. Embedding similarity
4. Graph-based features
5. Sense-level survival analysis

Uses two-stage architecture:
- Stage 1: High-recall coarse filter
- Stage 2: Precision-focused fine ranking
"""

import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

from .business_metrics import compute_business_metrics
from .embeddings import EMBEDDING_FEATURE_NAMES, EmbeddingFeatureExtractor
from .graph import GRAPH_FEATURE_NAMES, GraphFeatureExtractor
from .sense_survival import SENSE_SURVIVAL_FEATURE_NAMES, SenseLevelSurvival
from .value import VocabValueEstimator

logger = logging.getLogger(__name__)


@dataclass
class EnsembleConfig:
    """Configuration for ensemble ranker"""

    # Stage 1: Coarse filter
    stage1_top_k: int = 500  # Keep top 500 candidates
    stage1_recall_bias: float = 5.0  # Class weight for positive class

    # Stage 2: Fine ranking
    stage2_n_estimators: int = 200
    stage2_learning_rate: float = 0.05
    stage2_num_leaves: int = 31

    # Ensemble weights (learned or fixed)
    use_learned_weights: bool = True
    default_weights: dict[str, float] = field(default_factory=lambda: {
        "ml_score": 0.35,
        "value_score": 0.25,
        "embedding_score": 0.15,
        "graph_score": 0.10,
        "sense_survival_score": 0.15,
    })

    # Feature selection
    use_embeddings: bool = True
    use_graph: bool = True
    use_sense_survival: bool = True
    use_value_estimation: bool = True


class TwoStageRanker:
    """
    Two-stage ranking model:
    - Stage 1: Logistic regression with high recall (filter)
    - Stage 2: LightGBM LambdaRank (fine ranking)
    """

    def __init__(self, config: EnsembleConfig):
        self.config = config

        # Stage 1: High recall filter
        self.stage1_model = LogisticRegression(
            C=0.1,
            class_weight={0: 1, 1: config.stage1_recall_bias},
            max_iter=1000,
            random_state=42,
        )

        # Stage 2: Fine ranker
        self.stage2_model: lgb.Booster | None = None
        self.stage2_params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [50, 100, 200],
            "num_leaves": config.stage2_num_leaves,
            "learning_rate": config.stage2_learning_rate,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "min_child_samples": 20,
            "random_state": 42,
            "verbose": -1,
        }

        self.scaler = StandardScaler()
        self.feature_names: list[str] = []

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        groups: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> dict[str, float]:
        """
        Train two-stage model.
        """
        self.feature_names = feature_names or []

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Stage 1: Train filter
        logger.info("Training Stage 1 (high-recall filter)...")
        self.stage1_model.fit(X_scaled, y)

        # Get stage 1 predictions
        stage1_probs = self.stage1_model.predict_proba(X_scaled)[:, 1]

        # Select top candidates for stage 2 training
        # We want to train stage 2 on a balanced subset
        top_indices = np.argsort(stage1_probs)[-self.config.stage1_top_k:]

        X_stage2 = X_scaled[top_indices]
        y_stage2 = y[top_indices]

        # If groups provided, need to handle properly
        if groups is not None:
            groups_stage2 = np.array([len(X_stage2)])  # Single group for now
        else:
            groups_stage2 = np.array([len(X_stage2)])

        # Stage 2: Train ranker
        logger.info(f"Training Stage 2 (fine ranker) on {len(X_stage2)} candidates...")

        train_data = lgb.Dataset(
            X_stage2,
            label=y_stage2,
            group=groups_stage2,
            feature_name=feature_names if feature_names else "auto",
        )

        self.stage2_model = lgb.train(
            self.stage2_params,
            train_data,
            num_boost_round=self.config.stage2_n_estimators,
        )

        # Evaluate
        y_pred = self.predict(X)
        metrics = compute_business_metrics(y, y_pred, k_list=[50, 100, 200])

        return {
            "coverage_at_100": metrics.coverage_at_100,
            "ndcg_at_100": metrics.ndcg_at_100,
            "stage1_positive_rate": y_stage2.mean(),
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Two-stage prediction.
        """
        X_scaled = self.scaler.transform(X)

        # Stage 1: Get candidates
        stage1_probs = self.stage1_model.predict_proba(X_scaled)[:, 1]

        # Identify candidates (top K + positive probability threshold)
        threshold = np.percentile(stage1_probs, 100 - (self.config.stage1_top_k / len(X) * 100))
        candidates = stage1_probs >= threshold

        # Stage 2: Fine rank candidates
        scores = np.zeros(len(X))

        if self.stage2_model is not None and candidates.any():
            stage2_scores = self.stage2_model.predict(X_scaled[candidates])
            scores[candidates] = stage2_scores

            # For non-candidates, use stage1 probability (lower scores)
            scores[~candidates] = stage1_probs[~candidates] * 0.1
        else:
            scores = stage1_probs

        return scores

    def get_feature_importance(self) -> dict[str, float]:
        """Get feature importance from stage 2 model"""
        if self.stage2_model is None:
            return {}

        importance = self.stage2_model.feature_importance(importance_type="gain")

        if self.feature_names:
            return dict(zip(self.feature_names, importance, strict=False))
        return {f"feature_{i}": v for i, v in enumerate(importance)}


class EnsembleVocabRanker:
    """
    Multi-objective ensemble ranker combining all feature sources.
    """

    def __init__(self, config: EnsembleConfig | None = None):
        self.config = config or EnsembleConfig()

        # Core ranking model
        self.ranker = TwoStageRanker(self.config)

        # Feature extractors
        self.value_estimator: VocabValueEstimator | None = None
        self.embedding_extractor: EmbeddingFeatureExtractor | None = None
        self.graph_extractor: GraphFeatureExtractor | None = None
        self.sense_survival: SenseLevelSurvival | None = None

        # Ensemble meta-learner (learns optimal weights)
        self.meta_model: Ridge | None = None
        self.ensemble_weights: dict[str, float] = self.config.default_weights.copy()

        # Feature tracking
        self.base_feature_names: list[str] = []
        self.all_feature_names: list[str] = []

    def build_extended_features(
        self,
        vocab_data: list[dict],
        base_features: np.ndarray,
        base_feature_names: list[str],
        target_year: int,
    ) -> tuple[np.ndarray, list[str]]:
        """
        Build extended feature matrix with all feature sources.
        """
        extended_features = [base_features]
        extended_names = list(base_feature_names)

        # 1. Value estimation features
        if self.config.use_value_estimation and self.value_estimator:
            logger.info("Extracting value estimation features...")
            value_features = []
            for w in vocab_data:
                value = self.value_estimator.estimate_value(w)
                value_features.append([
                    value.evl_score,
                    value.recognition.raw_value,
                    value.production.raw_value,
                    value.discrimination.raw_value,
                    value.sense_coverage,
                ])
            extended_features.append(np.array(value_features))
            extended_names.extend([
                "value_evl", "value_recognition", "value_production",
                "value_discrimination", "value_sense_coverage"
            ])

        # 2. Embedding features
        if self.config.use_embeddings and self.embedding_extractor:
            logger.info("Extracting embedding features...")
            lemmas = [w.get("lemma", "") for w in vocab_data]
            emb_features = self.embedding_extractor.extract_batch(lemmas)
            emb_matrix = np.array([
                [f[k] for k in EMBEDDING_FEATURE_NAMES]
                for f in emb_features
            ])
            extended_features.append(emb_matrix)
            extended_names.extend(EMBEDDING_FEATURE_NAMES)

        # 3. Graph features
        if self.config.use_graph and self.graph_extractor:
            logger.info("Extracting graph features...")
            lemmas = [w.get("lemma", "") for w in vocab_data]
            graph_features = self.graph_extractor.extract_batch(lemmas)
            graph_matrix = np.array([
                [f[k] for k in GRAPH_FEATURE_NAMES]
                for f in graph_features
            ])
            extended_features.append(graph_matrix)
            extended_names.extend(GRAPH_FEATURE_NAMES)

        # 4. Sense-level survival features
        if self.config.use_sense_survival and self.sense_survival:
            logger.info("Extracting sense survival features...")
            sense_features = []
            for w in vocab_data:
                sf = self.sense_survival.extract_features(w, target_year)
                sense_features.append([sf[k] for k in SENSE_SURVIVAL_FEATURE_NAMES])
            extended_features.append(np.array(sense_features))
            extended_names.extend(SENSE_SURVIVAL_FEATURE_NAMES)

        # Combine all features
        X_extended = np.hstack(extended_features)
        self.all_feature_names = extended_names

        logger.info(f"Extended features: {base_features.shape[1]} -> {X_extended.shape[1]}")

        return X_extended, extended_names

    def fit_feature_extractors(
        self,
        vocab_data: list[dict],
        target_year: int,
        tested_lemmas: set[str],
    ):
        """
        Fit all feature extractors before training.
        """
        # Value estimator
        if self.config.use_value_estimation:
            self.value_estimator = VocabValueEstimator(target_year=target_year)

        # Embedding extractor
        if self.config.use_embeddings:
            from .embeddings import VocabEmbedder
            embedder = VocabEmbedder()
            self.embedding_extractor = EmbeddingFeatureExtractor(embedder=embedder)

            recent_tested = {
                lemma for lemma in tested_lemmas
                # Additional filtering could be added here
            }
            self.embedding_extractor.fit(
                vocab_data, target_year, tested_lemmas, recent_tested
            )

        # Graph extractor
        if self.config.use_graph:
            from .graph import VocabGraph
            graph = VocabGraph()

            embeddings = None
            if self.embedding_extractor and self.embedding_extractor._all_embeddings is not None:
                embeddings = self.embedding_extractor._all_embeddings

            graph.build(vocab_data, embeddings=embeddings)
            self.graph_extractor = GraphFeatureExtractor()
            self.graph_extractor.fit(graph, tested_lemmas, target_year)

        # Sense-level survival
        if self.config.use_sense_survival:
            self.sense_survival = SenseLevelSurvival()
            self.sense_survival.fit(vocab_data, target_year)

    def train(
        self,
        vocab_data: list[dict],
        base_features: np.ndarray,
        y: np.ndarray,
        groups: np.ndarray | None,
        base_feature_names: list[str],
        target_year: int,
    ) -> dict[str, Any]:
        """
        Train the full ensemble model.
        """
        self.base_feature_names = base_feature_names

        # Build tested lemmas set
        tested_lemmas = {
            vocab_data[i].get("lemma", "")
            for i in range(len(y)) if y[i] == 1
        }

        # Fit feature extractors
        logger.info("Fitting feature extractors...")
        self.fit_feature_extractors(vocab_data, target_year, tested_lemmas)

        # Build extended features
        X_extended, extended_names = self.build_extended_features(
            vocab_data, base_features, base_feature_names, target_year
        )

        # Train main ranker
        logger.info("Training two-stage ranker...")
        metrics = self.ranker.train(
            X_extended, y, groups, feature_names=extended_names
        )

        # Learn ensemble weights (meta-learning)
        if self.config.use_learned_weights:
            self._learn_ensemble_weights(X_extended, y, extended_names)

        return {
            **metrics,
            "n_features": X_extended.shape[1],
            "ensemble_weights": self.ensemble_weights,
        }

    def _learn_ensemble_weights(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str],
    ):
        """
        Learn optimal ensemble weights from validation data.
        """
        # Group features by source
        feature_groups = {
            "base": [],
            "value": [],
            "embedding": [],
            "graph": [],
            "sense": [],
        }

        for i, name in enumerate(feature_names):
            if name.startswith("value_"):
                feature_groups["value"].append(i)
            elif name.startswith("emb_"):
                feature_groups["embedding"].append(i)
            elif name.startswith("graph_"):
                feature_groups["graph"].append(i)
            elif name.startswith("sense_"):
                feature_groups["sense"].append(i)
            else:
                feature_groups["base"].append(i)

        # Compute per-group scores
        group_scores = {}
        for group_name, indices in feature_groups.items():
            if indices:
                group_X = X[:, indices]
                # Simple average as group score
                group_scores[group_name] = group_X.mean(axis=1)

        # Stack group scores
        if group_scores:
            stacked = np.column_stack(list(group_scores.values()))
            group_names = list(group_scores.keys())

            # Fit meta-model
            self.meta_model = Ridge(alpha=1.0)
            self.meta_model.fit(stacked, y)

            # Extract weights (positive coefficients only)
            coefs = np.maximum(self.meta_model.coef_, 0)
            if coefs.sum() > 0:
                coefs = coefs / coefs.sum()

            for i, name in enumerate(group_names):
                self.ensemble_weights[f"{name}_score"] = float(coefs[i])

    def predict(
        self,
        vocab_data: list[dict],
        base_features: np.ndarray,
        target_year: int,
    ) -> np.ndarray:
        """
        Predict ranking scores for vocabulary.
        """
        # Build extended features
        X_extended, _ = self.build_extended_features(
            vocab_data, base_features, self.base_feature_names, target_year
        )

        # Two-stage prediction
        scores = self.ranker.predict(X_extended)

        return scores

    def get_feature_importance(self) -> dict[str, float]:
        """Get combined feature importance"""
        return self.ranker.get_feature_importance()

    def save(self, path: Path):
        """Save ensemble model"""
        data = {
            "config": self.config,
            "ranker": self.ranker,
            "value_estimator": self.value_estimator,
            "embedding_extractor": self.embedding_extractor,
            "graph_extractor": self.graph_extractor,
            "sense_survival": self.sense_survival,
            "meta_model": self.meta_model,
            "ensemble_weights": self.ensemble_weights,
            "base_feature_names": self.base_feature_names,
            "all_feature_names": self.all_feature_names,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: Path) -> "EnsembleVocabRanker":
        """Load ensemble model"""
        with open(path, "rb") as f:
            data = pickle.load(f)

        obj = cls(config=data["config"])
        obj.ranker = data["ranker"]
        obj.value_estimator = data["value_estimator"]
        obj.embedding_extractor = data["embedding_extractor"]
        obj.graph_extractor = data["graph_extractor"]
        obj.sense_survival = data["sense_survival"]
        obj.meta_model = data["meta_model"]
        obj.ensemble_weights = data["ensemble_weights"]
        obj.base_feature_names = data["base_feature_names"]
        obj.all_feature_names = data["all_feature_names"]

        return obj
