"""
ML model training and inference for GSAT vocabulary importance prediction.

Provides both training and runtime inference capabilities using Gradient Boosting.

Supports multiple target modes:
- "appeared": Word appeared anywhere in the exam (easiest to predict, less useful)
- "tested": Word was tested as answer, keyword, or distractor (harder, more useful)
- "active_tested": Word was answer or keyword only (hardest, most valuable)
- "answer_only": Word was the correct answer (strictest)
"""

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

from .features import FeatureExtractor, get_feature_names

logger = logging.getLogger(__name__)

MODEL_VERSION = "2.0.0"


@dataclass
class ModelMetrics:
    auc: float
    accuracy: float
    precision: float
    recall: float
    f1: float
    cv_auc_mean: float
    cv_auc_std: float


class ImportanceModel:
    def __init__(self, target_mode: str = "tested"):
        self.model: GradientBoostingClassifier | None = None
        self.scaler: StandardScaler | None = None
        self.feature_names: list[str] = get_feature_names()
        self.metrics: ModelMetrics | None = None
        self.version: str = MODEL_VERSION
        self.target_mode: str = target_mode

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_estimators: int = 200,
        max_depth: int = 4,
        min_samples_leaf: int = 15,
        learning_rate: float = 0.05,
    ) -> ModelMetrics:
        logger.info(f"Training model on {len(X)} samples...")

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = GradientBoostingClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            learning_rate=learning_rate,
            subsample=0.8,
            random_state=42,
        )

        cv_scores = cross_val_score(self.model, X_scaled, y, cv=5, scoring="roc_auc")
        logger.info(f"5-Fold CV AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

        self.model.fit(X_scaled, y)

        y_pred = self.model.predict(X_scaled)
        y_prob = self.model.predict_proba(X_scaled)[:, 1]

        from sklearn.metrics import (
            accuracy_score,
            precision_recall_fscore_support,
            roc_auc_score,
        )

        auc = roc_auc_score(y, y_prob)
        accuracy = accuracy_score(y, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y, y_pred, average="binary", zero_division="warn"
        )

        self.metrics = ModelMetrics(
            auc=float(auc),
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1=float(f1),
            cv_auc_mean=float(cv_scores.mean()),
            cv_auc_std=float(cv_scores.std()),
        )

        logger.info(f"Training complete. AUC: {auc:.4f}, CV AUC: {cv_scores.mean():.4f}")

        return self.metrics

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained. Call train() or load() first.")

        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)[:, 1]

    def predict_importance(self, features: list[float]) -> float:
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained. Call train() or load() first.")

        X = np.array([features])
        return float(self.predict_proba(X)[0])

    def predict_batch(self, feature_list: list[list[float]]) -> list[float]:
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained. Call train() or load() first.")

        X = np.array(feature_list)
        return self.predict_proba(X).tolist()

    def get_feature_importance(self) -> dict[str, float]:
        if self.model is None:
            raise ValueError("Model not trained.")

        importances = self.model.feature_importances_.tolist()
        return dict(zip(self.feature_names, importances, strict=False))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            "version": self.version,
            "model": self.model,
            "scaler": self.scaler,
            "feature_names": self.feature_names,
            "target_mode": self.target_mode,
            "metrics": {
                "auc": self.metrics.auc if self.metrics else None,
                "accuracy": self.metrics.accuracy if self.metrics else None,
                "precision": self.metrics.precision if self.metrics else None,
                "recall": self.metrics.recall if self.metrics else None,
                "f1": self.metrics.f1 if self.metrics else None,
                "cv_auc_mean": self.metrics.cv_auc_mean if self.metrics else None,
                "cv_auc_std": self.metrics.cv_auc_std if self.metrics else None,
            },
        }

        with open(path, "wb") as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {path}")

    def load(self, path: Path) -> None:
        with open(path, "rb") as f:
            model_data = pickle.load(f)

        self.version = model_data.get("version", "unknown")
        self.model = model_data["model"]
        self.scaler = model_data["scaler"]
        self.feature_names = model_data.get("feature_names", get_feature_names())
        self.target_mode = model_data.get("target_mode", "tested")

        metrics_data = model_data.get("metrics", {})
        if metrics_data and metrics_data.get("auc") is not None:
            self.metrics = ModelMetrics(
                auc=metrics_data["auc"],
                accuracy=metrics_data["accuracy"],
                precision=metrics_data["precision"],
                recall=metrics_data["recall"],
                f1=metrics_data["f1"],
                cv_auc_mean=metrics_data["cv_auc_mean"],
                cv_auc_std=metrics_data["cv_auc_std"],
            )

        logger.info(f"Model loaded from {path} (version: {self.version})")


def load_model(path: Path) -> ImportanceModel:
    model = ImportanceModel()
    model.load(path)
    return model


def train_model(
    entries: list[dict[str, Any]],
    distractor_groups: list[dict],
    essay_topics: list[dict] | None = None,
    target_year: int = 114,
    lookback_years: int = 15,
    target_mode: str = "tested",
    gsat_only: bool = False,
) -> tuple[ImportanceModel, dict[str, Any]]:
    """
    Train an importance prediction model.

    Args:
        entries: List of vocabulary entries from extracted.json
        distractor_groups: List of distractor groups
        essay_topics: List of essay topics with suggested words (NEW)
        target_year: Year to predict for
        lookback_years: How many years of history to use
        target_mode: One of:
            - "appeared": Word appeared anywhere in exam (easiest)
            - "tested": Word was answer/keyword/distractor (recommended)
            - "active_tested": Word was answer/keyword only (harder)
            - "answer_only": Word was correct answer (strictest)
        gsat_only: If True, filter out AST-only occurrences
    """
    logger.info(f"Preparing training data for target year {target_year} (mode: {target_mode})...")

    extractor = FeatureExtractor(current_year=target_year)

    X_data: list[list[float]] = []
    y_data: list[int] = []
    lemmas: list[str] = []

    for entry in entries:
        if gsat_only:
            filtered_contexts = [
                ctx
                for ctx in entry.get("contexts", [])
                if ctx.get("source", {}).get("exam_type", "").startswith("gsat")
            ]
            if not filtered_contexts:
                continue
            entry = {**entry, "contexts": filtered_contexts}

        word_data = extractor.extract_word_data(entry)
        features = extractor.extract_feature_vector(
            word_data, target_year=target_year
        )

        if features is None:
            continue

        label = extractor.get_target_label(word_data, target_year, target_mode)

        X_data.append(features)
        y_data.append(label)
        lemma = entry.get("lemma") or entry.get("word") or ""
        lemmas.append(str(lemma))

    X = np.array(X_data)
    y = np.array(y_data)

    logger.info(
        f"Training data: {len(X)} samples, {sum(y)} positive ({100 * sum(y) / len(y):.1f}%)"
    )

    model = ImportanceModel(target_mode=target_mode)
    metrics = model.train(X, y)

    feature_importance = model.get_feature_importance()
    top_features = sorted(feature_importance.items(), key=lambda x: -x[1])[:10]

    training_info = {
        "target_year": target_year,
        "target_mode": target_mode,
        "gsat_only": gsat_only,
        "training_samples": len(X),
        "positive_samples": int(sum(y)),
        "positive_rate": sum(y) / len(y),
        "metrics": {
            "auc": metrics.auc,
            "accuracy": metrics.accuracy,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1": metrics.f1,
            "cv_auc_mean": metrics.cv_auc_mean,
            "cv_auc_std": metrics.cv_auc_std,
        },
        "top_features": [{"name": name, "importance": imp} for name, imp in top_features],
    }

    return model, training_info


class ImportanceScorer:
    def __init__(
        self,
        model: ImportanceModel | None = None,
        current_year: int = 114,
    ):
        self.model = model
        self.extractor = FeatureExtractor(current_year=current_year)
        self.current_year = current_year

    def score_entry(self, entry: dict[str, Any]) -> float | None:
        if self.model is None:
            return None

        word_data = self.extractor.extract_word_data(entry)
        features = self.extractor.extract_feature_vector(word_data, target_year=self.current_year)

        if features is None:
            return None

        return self.model.predict_importance(features)

    def score_entries(self, entries: list[dict[str, Any]]) -> dict[str, float]:
        if self.model is None:
            return {}

        results: dict[str, float] = {}
        batch_features: list[list[float]] = []
        batch_lemmas: list[str] = []

        for entry in entries:
            word_data = self.extractor.extract_word_data(entry)
            features = self.extractor.extract_feature_vector(word_data, target_year=self.current_year)

            if features is not None:
                batch_features.append(features)
                batch_lemmas.append(entry["lemma"])

        if batch_features:
            scores = self.model.predict_batch(batch_features)
            for lemma, score in zip(batch_lemmas, scores, strict=False):
                results[lemma] = score

        return results
