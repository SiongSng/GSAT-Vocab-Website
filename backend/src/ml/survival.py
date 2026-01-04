"""
Survival Analysis model for GSAT vocabulary testing cycle prediction.

This module implements a Cox Proportional Hazards model to predict
when a word will be tested next, based on "time since last tested"
and vocabulary features.
"""

import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.utils import concordance_index


@dataclass
class SurvivalMetrics:
    """Metrics for survival model evaluation"""

    concordance_index: float
    partial_auc: float
    median_survival_time: float | None


class TestingCycleModel:
    """
    Survival Analysis model for predicting vocabulary testing cycles.

    Models the "hazard" of a word being tested based on:
    - Duration: Years since last tested
    - Event: Whether the word was tested in the target year
    - Covariates: Vocabulary features

    This captures the "cooling off" effect where recently tested words
    may be less likely to be tested again, and helps predict optimal
    study timing.
    """

    def __init__(
        self,
        penalizer: float = 0.1,
        l1_ratio: float = 0.0,
        min_variance: float = 0.01,
    ):
        """
        Initialize the TestingCycleModel.

        Args:
            penalizer: L2 regularization strength (higher = more regularization)
            l1_ratio: L1/L2 ratio for elastic net (0 = pure L2, 1 = pure L1)
            min_variance: Minimum variance threshold for feature selection
        """
        self.penalizer = penalizer
        self.l1_ratio = l1_ratio
        self.min_variance = min_variance
        self.model: CoxPHFitter | None = None
        self.feature_names: list[str] = []
        self.selected_features: list[str] = []
        self.feature_mask: np.ndarray | None = None

    def _select_features(self, features: np.ndarray, feature_names: list[str]) -> tuple[np.ndarray, list[str]]:
        """Filter out low-variance features to avoid singular matrix issues.

        Args:
            features: Feature matrix (n_samples, n_features)
            feature_names: Names of feature columns

        Returns:
            Tuple of (filtered features, selected feature names)
        """
        variances = np.var(features, axis=0)
        mask = variances >= self.min_variance

        # Also remove features that are constant or nearly constant
        for i in range(features.shape[1]):
            unique_vals = np.unique(features[:, i])
            if len(unique_vals) <= 2:
                mask[i] = False

        self.feature_mask = mask
        self.selected_features = [name for name, keep in zip(feature_names, mask) if keep]

        return features[:, mask], self.selected_features

    def prepare_data(
        self,
        features: np.ndarray,
        durations: np.ndarray,
        events: np.ndarray,
        feature_names: list[str] | None = None,
    ) -> pd.DataFrame:
        """
        Prepare data for Cox PH fitting.

        Args:
            features: Feature matrix (n_samples, n_features)
            durations: Time since last tested (in years)
            events: Whether word was tested (1) or not (0)
            feature_names: Names of feature columns

        Returns:
            DataFrame ready for CoxPHFitter
        """
        if feature_names:
            self.feature_names = feature_names
        else:
            self.feature_names = [f"feature_{i}" for i in range(features.shape[1])]

        # Filter low-variance features
        filtered_features, selected_names = self._select_features(features, self.feature_names)

        df = pd.DataFrame(filtered_features, columns=selected_names)
        df["duration"] = durations
        df["event"] = events

        # Handle edge cases
        df["duration"] = df["duration"].clip(lower=0.5)  # Minimum 0.5 years
        df = df.dropna()

        return df

    def fit(
        self,
        features: np.ndarray,
        durations: np.ndarray,
        events: np.ndarray,
        feature_names: list[str] | None = None,
    ) -> SurvivalMetrics:
        """
        Fit the Cox Proportional Hazards model.

        Args:
            features: Feature matrix (n_samples, n_features)
            durations: Time since last tested (in years)
            events: Whether word was tested (1) or not (0)
            feature_names: Names of feature columns

        Returns:
            SurvivalMetrics with model performance
        """
        df = self.prepare_data(features, durations, events, feature_names)

        if len(self.selected_features) == 0:
            raise ValueError("No features with sufficient variance for survival model")

        self.model = CoxPHFitter(
            penalizer=self.penalizer,
            l1_ratio=self.l1_ratio,
        )

        self.model.fit(
            df,
            duration_col="duration",
            event_col="event",
            show_progress=False,
        )

        # Compute metrics
        c_index = self.model.concordance_index_

        # Partial AUC (using model's internal scoring)
        partial_auc = self._compute_partial_auc(df)

        # Median survival time (if computable)
        try:
            median_time = self.model.median_survival_time_
        except Exception:
            median_time = None

        return SurvivalMetrics(
            concordance_index=c_index,
            partial_auc=partial_auc,
            median_survival_time=median_time,
        )

    def predict_hazard(self, features: np.ndarray) -> np.ndarray:
        """
        Predict hazard scores for samples.

        Higher hazard = more likely to be "tested" soon.

        Args:
            features: Feature matrix (n_samples, n_features) - must match original feature count

        Returns:
            Hazard scores (higher = more likely to be tested)
        """
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")

        # Apply the same feature mask used during training
        if self.feature_mask is not None:
            features = features[:, self.feature_mask]

        df = pd.DataFrame(features, columns=self.selected_features)

        # Get partial hazard (relative risk)
        hazard = self.model.predict_partial_hazard(df)
        return hazard.values.flatten()

    def predict_survival_probability(
        self,
        features: np.ndarray,
        times: list[float] | None = None,
    ) -> pd.DataFrame:
        """
        Predict survival probability at given times.

        Args:
            features: Feature matrix (n_samples, n_features) - must match original feature count
            times: Time points to predict (default: [1, 2, 3, 5])

        Returns:
            DataFrame with survival probabilities
        """
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")

        if times is None:
            times = [1.0, 2.0, 3.0, 5.0]

        # Apply the same feature mask used during training
        if self.feature_mask is not None:
            features = features[:, self.feature_mask]

        df = pd.DataFrame(features, columns=self.selected_features)
        survival_func = self.model.predict_survival_function(df, times=times)
        return survival_func

    def get_feature_importance(self) -> dict[str, dict[str, float]]:
        """
        Get feature coefficients and hazard ratios.

        Returns:
            Dictionary mapping feature names to {coef, hazard_ratio, p_value}
        """
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")

        summary = self.model.summary

        importance = {}
        for feature in self.selected_features:
            if feature in summary.index:
                row = summary.loc[feature]
                importance[feature] = {
                    "coefficient": row["coef"],
                    "hazard_ratio": row["exp(coef)"],
                    "p_value": row["p"],
                }

        return importance

    def _compute_partial_auc(self, df: pd.DataFrame) -> float:
        """Compute partial AUC score using concordance index"""
        try:
            if self.model is None:
                return 0.0
            predicted_hazard = self.model.predict_partial_hazard(df)
            c_index = concordance_index(
                df["duration"],
                -predicted_hazard,  # Negative because higher hazard = shorter time
                df["event"],
            )
            return c_index
        except Exception:
            return 0.0

    def save(self, path: Path) -> None:
        """Save model to file"""
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")

        data = {
            "model": self.model,
            "penalizer": self.penalizer,
            "l1_ratio": self.l1_ratio,
            "min_variance": self.min_variance,
            "feature_names": self.feature_names,
            "selected_features": self.selected_features,
            "feature_mask": self.feature_mask,
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: Path) -> "TestingCycleModel":
        """Load model from file"""
        with open(path, "rb") as f:
            data = pickle.load(f)

        model_obj = cls(
            penalizer=data["penalizer"],
            l1_ratio=data["l1_ratio"],
            min_variance=data.get("min_variance", 0.01),
        )
        model_obj.model = data["model"]
        model_obj.feature_names = data["feature_names"]
        model_obj.selected_features = data.get("selected_features", data["feature_names"])
        model_obj.feature_mask = data.get("feature_mask")
        return model_obj


def compute_duration_from_word_data(
    years_tested: set[int],
    target_year: int,
    max_duration: int = 20,
) -> float:
    """
    Compute duration (years since last tested) for survival analysis.

    Args:
        years_tested: Set of years when word was tested
        target_year: Year we're predicting
        max_duration: Maximum duration to cap at

    Returns:
        Duration in years
    """
    past_tested = [y for y in years_tested if y < target_year]

    if not past_tested:
        return float(max_duration)

    last_tested = max(past_tested)
    duration = target_year - last_tested

    return min(duration, max_duration)
