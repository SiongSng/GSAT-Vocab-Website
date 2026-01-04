"""
LightGBM LambdaRank model for GSAT vocabulary importance ranking.

This module implements a Learning-to-Rank approach using LightGBM's LambdaRank
objective, which directly optimizes NDCG for ranking vocabulary by testing probability.
"""

import pickle
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
from sklearn.model_selection import GroupKFold


@dataclass
class RankerMetrics:
    """Metrics for ranking model evaluation"""

    ndcg_at_50: float
    ndcg_at_100: float
    ndcg_at_200: float
    cv_ndcg_mean: float
    cv_ndcg_std: float


class VocabRanker:
    """
    Learning-to-Rank model for vocabulary importance prediction.

    Uses LightGBM's LambdaRank objective to directly optimize NDCG,
    which is more suitable for predicting vocabulary distributions
    than binary classification.
    """

    def __init__(
        self,
        objective: str = "lambdarank",
        num_leaves: int = 31,
        learning_rate: float = 0.05,
        n_estimators: int = 200,
        feature_fraction: float = 0.8,
        bagging_fraction: float = 0.8,
        bagging_freq: int = 5,
        min_child_samples: int = 20,
        ndcg_eval_at: list[int] | None = None,
        random_state: int = 42,
    ):
        """
        Initialize the VocabRanker.

        Args:
            objective: LightGBM ranking objective ('lambdarank' or 'rank_xendcg')
            num_leaves: Maximum number of leaves in one tree
            learning_rate: Boosting learning rate
            n_estimators: Number of boosting iterations
            feature_fraction: Subsample ratio of features
            bagging_fraction: Subsample ratio of data
            bagging_freq: Frequency of bagging
            min_child_samples: Minimum samples in a leaf
            ndcg_eval_at: NDCG evaluation positions (default: [50, 100, 200])
            random_state: Random seed for reproducibility
        """
        self.params = {
            "objective": objective,
            "metric": "ndcg",
            "ndcg_eval_at": ndcg_eval_at or [50, 100, 200],
            "num_leaves": num_leaves,
            "learning_rate": learning_rate,
            "feature_fraction": feature_fraction,
            "bagging_fraction": bagging_fraction,
            "bagging_freq": bagging_freq,
            "min_child_samples": min_child_samples,
            "random_state": random_state,
            "verbose": -1,
        }
        self.n_estimators = n_estimators
        self.model: lgb.Booster | None = None
        self.feature_names: list[str] = []

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        groups: np.ndarray | None = None,
        feature_names: list[str] | None = None,
        cv_folds: int = 5,
    ) -> RankerMetrics:
        """
        Train the ranking model.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Relevance labels (higher = more relevant, e.g., 0/1 or graded)
            groups: Group sizes for ranking (if None, treat all as one group)
            feature_names: Names of features for interpretability
            cv_folds: Number of cross-validation folds

        Returns:
            RankerMetrics with training and CV performance
        """
        if groups is None:
            # Treat all samples as one ranking group
            groups = np.array([len(X)])

        if feature_names:
            self.feature_names = feature_names

        # Create LightGBM dataset
        train_data = lgb.Dataset(
            X,
            label=y,
            group=groups,
            feature_name=feature_names if feature_names else "auto",
        )

        # Cross-validation
        cv_results = lgb.cv(
            self.params,
            train_data,
            num_boost_round=self.n_estimators,
            nfold=cv_folds,
            stratified=False,  # Ranking CV should not stratify
            return_cvbooster=False,
        )

        # Extract NDCG@100 from CV (key format: 'valid ndcg@100-mean')
        ndcg_key = "valid ndcg@100-mean"
        cv_ndcg_values = cv_results.get(ndcg_key, [0.0])
        cv_ndcg_mean = max(cv_ndcg_values) if cv_ndcg_values else 0.0

        ndcg_std_key = "valid ndcg@100-stdv"
        cv_ndcg_std_values = cv_results.get(ndcg_std_key, [0.0])
        cv_ndcg_std = cv_ndcg_std_values[-1] if cv_ndcg_std_values else 0.0

        # Train final model on full data
        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=self.n_estimators,
        )

        # Evaluate on training data
        y_pred = self.model.predict(X)
        if not isinstance(y_pred, np.ndarray):
            y_pred = np.array(y_pred)
        metrics = self._compute_ndcg_metrics(y, y_pred, groups)

        return RankerMetrics(
            ndcg_at_50=metrics["ndcg@50"],
            ndcg_at_100=metrics["ndcg@100"],
            ndcg_at_200=metrics["ndcg@200"],
            cv_ndcg_mean=cv_ndcg_mean,
            cv_ndcg_std=cv_ndcg_std,
        )

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict ranking scores for samples.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            Ranking scores (higher = more likely to be tested)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        result = self.model.predict(X)
        if not isinstance(result, np.ndarray):
            return np.array(result)
        return result

    def get_feature_importance(self, importance_type: str = "gain") -> dict[str, float]:
        """
        Get feature importance scores.

        Args:
            importance_type: 'gain', 'split', or 'cover'

        Returns:
            Dictionary mapping feature names to importance scores
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        importance = self.model.feature_importance(importance_type=importance_type)

        if self.feature_names:
            return dict(zip(self.feature_names, importance, strict=False))
        return {f"feature_{i}": v for i, v in enumerate(importance)}

    def _compute_ndcg_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        groups: np.ndarray,
    ) -> dict[str, float]:
        """Compute NDCG at various cutoffs"""
        from sklearn.metrics import ndcg_score

        # For single group, compute NDCG directly
        if len(groups) == 1:
            return {
                "ndcg@50": ndcg_score([y_true], [y_pred], k=50),
                "ndcg@100": ndcg_score([y_true], [y_pred], k=100),
                "ndcg@200": ndcg_score([y_true], [y_pred], k=200),
            }

        # For multiple groups, average across groups
        ndcg_50_list = []
        ndcg_100_list = []
        ndcg_200_list = []

        start_idx = 0
        for group_size in groups:
            end_idx = start_idx + group_size
            y_true_group = y_true[start_idx:end_idx]
            y_pred_group = y_pred[start_idx:end_idx]

            if len(y_true_group) > 0 and y_true_group.sum() > 0:
                ndcg_50_list.append(ndcg_score([y_true_group], [y_pred_group], k=50))
                ndcg_100_list.append(ndcg_score([y_true_group], [y_pred_group], k=100))
                ndcg_200_list.append(ndcg_score([y_true_group], [y_pred_group], k=200))

            start_idx = end_idx

        return {
            "ndcg@50": np.mean(ndcg_50_list) if ndcg_50_list else 0.0,
            "ndcg@100": np.mean(ndcg_100_list) if ndcg_100_list else 0.0,
            "ndcg@200": np.mean(ndcg_200_list) if ndcg_200_list else 0.0,
        }

    def save(self, path: Path) -> None:
        """Save model to file"""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        data = {
            "model": self.model,
            "params": self.params,
            "n_estimators": self.n_estimators,
            "feature_names": self.feature_names,
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: Path) -> "VocabRanker":
        """Load model from file"""
        with open(path, "rb") as f:
            data = pickle.load(f)

        ranker = cls()
        ranker.model = data["model"]
        ranker.params = data["params"]
        ranker.n_estimators = data["n_estimators"]
        ranker.feature_names = data["feature_names"]
        return ranker
