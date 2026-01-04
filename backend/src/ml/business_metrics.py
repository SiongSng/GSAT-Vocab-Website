"""
Business-oriented evaluation metrics for GSAT vocabulary prediction.

Key insight: The real goal is "maximize student score per hour of study"

Metrics:
1. Coverage@K: If a student studies top-K words, what % of exam words are covered?
2. Precision@K: What % of top-K predictions actually appear in exam?
3. ROI@K: Expected score gain per word studied
4. Level distribution analysis: Are predictions well-distributed across difficulty?
"""

import logging
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.metrics import ndcg_score, average_precision_score

from ..models.exam import AnnotationRole, ExamType, SectionType

logger = logging.getLogger(__name__)


@dataclass
class BusinessMetrics:
    """Comprehensive evaluation metrics with business focus"""

    # Coverage metrics (most important for students)
    coverage_at_50: float = 0.0
    coverage_at_100: float = 0.0
    coverage_at_200: float = 0.0
    coverage_at_500: float = 0.0

    # Precision metrics
    precision_at_50: float = 0.0
    precision_at_100: float = 0.0
    precision_at_200: float = 0.0

    # Ranking quality
    ndcg_at_50: float = 0.0
    ndcg_at_100: float = 0.0
    ndcg_at_200: float = 0.0

    # Mean Average Precision
    map_score: float = 0.0

    # ROI metrics (score gain / study effort)
    estimated_roi_at_100: float = 0.0

    # Distribution analysis
    level_distribution_kl: float = 0.0  # KL divergence from actual
    role_coverage: dict[str, float] = field(default_factory=dict)

    # Detailed breakdown
    true_positives_at_100: int = 0
    false_positives_at_100: int = 0
    total_positives: int = 0

    # Per-level metrics
    coverage_by_level: dict[int, float] = field(default_factory=dict)


def compute_coverage_at_k(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    k: int,
) -> float:
    """
    Coverage@K: What fraction of actual positives are in top-K predictions?

    This is the key metric for students:
    "If I study the top K recommended words, what % of exam words will I know?"
    """
    if y_true.sum() == 0:
        return 0.0

    top_k_indices = np.argsort(y_pred)[-k:]
    covered = y_true[top_k_indices].sum()
    total_positive = y_true.sum()

    return float(covered / total_positive)


def compute_precision_at_k(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    k: int,
) -> float:
    """
    Precision@K: What fraction of top-K predictions are actual positives?
    """
    top_k_indices = np.argsort(y_pred)[-k:]
    hits = y_true[top_k_indices].sum()

    return float(hits / k)


def compute_roi_at_k(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    word_levels: np.ndarray,
    k: int,
) -> float:
    """
    ROI@K: Expected score gain per unit of study effort.

    Effort is modeled as proportional to word difficulty level.
    Score gain is proportional to test probability.
    """
    top_k_indices = np.argsort(y_pred)[-k:]

    # Estimate score gain (assume each correct word = 1 point)
    expected_score = y_true[top_k_indices].sum()

    # Estimate effort (higher level = more effort)
    # L1=0.6, L6=1.5 effort units
    levels = word_levels[top_k_indices]
    effort_per_word = 0.4 + 0.2 * np.clip(levels, 1, 6)
    total_effort = effort_per_word.sum()

    if total_effort == 0:
        return 0.0

    return float(expected_score / total_effort)


def compute_level_distribution_kl(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    word_levels: np.ndarray,
    k: int,
) -> float:
    """
    KL divergence between predicted and actual level distributions.

    Lower is better - predictions should match actual exam distribution.
    """
    # Actual distribution of tested words
    actual_indices = np.where(y_true == 1)[0]
    actual_levels = word_levels[actual_indices]
    actual_dist = np.bincount(actual_levels.astype(int), minlength=7)[1:7]  # L1-L6
    actual_dist = actual_dist / actual_dist.sum() if actual_dist.sum() > 0 else np.ones(6) / 6

    # Predicted distribution
    top_k_indices = np.argsort(y_pred)[-k:]
    pred_levels = word_levels[top_k_indices]
    pred_dist = np.bincount(pred_levels.astype(int), minlength=7)[1:7]
    pred_dist = pred_dist / pred_dist.sum() if pred_dist.sum() > 0 else np.ones(6) / 6

    # Add small epsilon to avoid log(0)
    eps = 1e-10
    actual_dist = actual_dist + eps
    pred_dist = pred_dist + eps

    # KL divergence
    kl = np.sum(actual_dist * np.log(actual_dist / pred_dist))

    return float(kl)


def compute_business_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    word_levels: np.ndarray | None = None,
    word_roles: list[dict] | None = None,
    k_list: list[int] | None = None,
) -> BusinessMetrics:
    """
    Compute comprehensive business-oriented metrics.

    Args:
        y_true: Binary labels (1 = tested, 0 = not tested)
        y_pred: Prediction scores (higher = more likely)
        word_levels: Difficulty levels (1-6) for each word
        word_roles: Role information for each word
        k_list: List of K values to evaluate

    Returns:
        BusinessMetrics dataclass with all computed metrics
    """
    if k_list is None:
        k_list = [50, 100, 200, 500]

    metrics = BusinessMetrics()

    # Basic counts
    metrics.total_positives = int(y_true.sum())

    # Coverage metrics (most important!)
    for k in k_list:
        if k <= len(y_pred):
            cov = compute_coverage_at_k(y_true, y_pred, k)
            setattr(metrics, f"coverage_at_{k}", cov)

    # Precision metrics
    for k in [50, 100, 200]:
        if k <= len(y_pred):
            prec = compute_precision_at_k(y_true, y_pred, k)
            setattr(metrics, f"precision_at_{k}", prec)

    # NDCG metrics
    try:
        for k in [50, 100, 200]:
            if k <= len(y_pred):
                ndcg = ndcg_score([y_true], [y_pred], k=k)
                setattr(metrics, f"ndcg_at_{k}", ndcg)
    except Exception as e:
        logger.warning(f"NDCG computation failed: {e}")

    # Mean Average Precision
    try:
        metrics.map_score = float(average_precision_score(y_true, y_pred))
    except Exception:
        metrics.map_score = 0.0

    # ROI metrics (if levels provided)
    if word_levels is not None:
        word_levels_arr = np.array(word_levels)
        metrics.estimated_roi_at_100 = compute_roi_at_k(
            y_true, y_pred, word_levels_arr, 100
        )
        metrics.level_distribution_kl = compute_level_distribution_kl(
            y_true, y_pred, word_levels_arr, 100
        )

        # Per-level coverage
        for level in range(1, 7):
            level_mask = word_levels_arr == level
            if level_mask.sum() > 0 and y_true[level_mask].sum() > 0:
                level_coverage = compute_coverage_at_k(
                    y_true[level_mask], y_pred[level_mask], min(50, level_mask.sum())
                )
                metrics.coverage_by_level[level] = level_coverage

    # True/false positives at K=100
    top_100 = np.argsort(y_pred)[-100:]
    metrics.true_positives_at_100 = int(y_true[top_100].sum())
    metrics.false_positives_at_100 = 100 - metrics.true_positives_at_100

    return metrics


@dataclass
class TemporalValidationResult:
    """Results from temporal cross-validation"""
    years: list[int] = field(default_factory=list)
    metrics_per_year: dict[int, BusinessMetrics] = field(default_factory=dict)

    # Aggregated metrics
    avg_coverage_100: float = 0.0
    avg_ndcg_100: float = 0.0
    avg_precision_100: float = 0.0

    std_coverage_100: float = 0.0
    std_ndcg_100: float = 0.0

    # Trend analysis
    coverage_trend: float = 0.0  # Positive = improving over time


def temporal_cross_validate(
    prepare_fn,
    train_fn,
    predict_fn,
    entries: list[dict],
    test_years: list[int],
    lookback_years: int = 5,
) -> TemporalValidationResult:
    """
    Perform temporal (expanding window) cross-validation.

    Args:
        prepare_fn: Function to prepare features (entries, years) -> (X, y, meta)
        train_fn: Function to train model (X_train, y_train) -> model
        predict_fn: Function to predict (model, X_test) -> scores
        entries: All vocabulary entries
        test_years: Years to validate on
        lookback_years: How many years to look back for training

    Returns:
        TemporalValidationResult with per-year and aggregated metrics
    """
    result = TemporalValidationResult(years=test_years)

    coverages = []
    ndcgs = []
    precisions = []

    for target_year in test_years:
        logger.info(f"Temporal CV: Validating year {target_year}")

        # Training years
        train_years = list(range(max(105, target_year - lookback_years), target_year))

        # Prepare data
        X_train, y_train, meta_train = prepare_fn(entries, train_years)
        X_test, y_test, meta_test = prepare_fn(entries, [target_year])

        if len(X_test) == 0 or y_test.sum() < 5:
            logger.warning(f"  Skipping {target_year}: insufficient data")
            continue

        # Train and predict
        model = train_fn(X_train, y_train)
        y_pred = predict_fn(model, X_test)

        # Extract levels from metadata
        levels = np.array([m.get("level", 3) for m in meta_test])

        # Compute metrics
        metrics = compute_business_metrics(
            y_test, y_pred, word_levels=levels, k_list=[50, 100, 200, 500]
        )

        result.metrics_per_year[target_year] = metrics

        coverages.append(metrics.coverage_at_100)
        ndcgs.append(metrics.ndcg_at_100)
        precisions.append(metrics.precision_at_100)

        logger.info(
            f"  Year {target_year}: Coverage@100={metrics.coverage_at_100:.4f}, "
            f"NDCG@100={metrics.ndcg_at_100:.4f}, Positives={metrics.total_positives}"
        )

    # Aggregated metrics
    if coverages:
        result.avg_coverage_100 = float(np.mean(coverages))
        result.avg_ndcg_100 = float(np.mean(ndcgs))
        result.avg_precision_100 = float(np.mean(precisions))

        result.std_coverage_100 = float(np.std(coverages))
        result.std_ndcg_100 = float(np.std(ndcgs))

        # Trend analysis (linear regression slope)
        if len(coverages) >= 3:
            x = np.arange(len(coverages))
            slope = np.polyfit(x, coverages, 1)[0]
            result.coverage_trend = float(slope)

    return result


def compare_models(
    model_results: dict[str, TemporalValidationResult],
) -> dict[str, Any]:
    """
    Compare multiple models based on temporal CV results.

    Returns summary with ranking and statistical comparison.
    """
    comparison: dict[str, Any] = {
        "model_ranking": [],
        "best_model": None,
        "metrics_table": {},
    }

    # Rank by average coverage@100
    ranked = sorted(
        model_results.items(),
        key=lambda x: x[1].avg_coverage_100,
        reverse=True
    )

    comparison["model_ranking"] = [name for name, _ in ranked]
    comparison["best_model"] = ranked[0][0] if ranked else None

    # Build metrics table
    for name, result in model_results.items():
        comparison["metrics_table"][name] = {
            "avg_coverage_100": result.avg_coverage_100,
            "std_coverage_100": result.std_coverage_100,
            "avg_ndcg_100": result.avg_ndcg_100,
            "avg_precision_100": result.avg_precision_100,
            "coverage_trend": result.coverage_trend,
        }

    # Statistical significance test (paired t-test if applicable)
    if len(model_results) >= 2:
        from scipy import stats

        best_name = comparison["best_model"]
        if best_name is not None:
            best_coverages = [
                model_results[best_name].metrics_per_year[y].coverage_at_100
                for y in model_results[best_name].years
                if y in model_results[best_name].metrics_per_year
            ]

            comparison["significance_tests"] = {}
            for name, result in model_results.items():
                if name == best_name:
                    continue

                other_coverages = [
                    result.metrics_per_year[y].coverage_at_100
                    for y in result.years
                    if y in result.metrics_per_year
                ]

                if len(best_coverages) == len(other_coverages) and len(best_coverages) >= 3:
                    t_stat, p_value = stats.ttest_rel(best_coverages, other_coverages)
                    comparison["significance_tests"][f"{best_name}_vs_{name}"] = {
                        "t_statistic": float(t_stat),
                        "p_value": float(p_value),
                        "significant_at_0.05": p_value < 0.05,
                    }

    return comparison


def generate_evaluation_report(
    metrics: BusinessMetrics,
    model_name: str = "Model",
    target_year: int = 115,
) -> str:
    """
    Generate human-readable evaluation report.
    """
    lines = [
        f"=== Evaluation Report: {model_name} (Target Year: {target_year}) ===",
        "",
        "📊 Coverage Metrics (Most Important for Students)",
        f"   Coverage@50:  {metrics.coverage_at_50:.1%} of exam words in top 50",
        f"   Coverage@100: {metrics.coverage_at_100:.1%} of exam words in top 100",
        f"   Coverage@200: {metrics.coverage_at_200:.1%} of exam words in top 200",
        f"   Coverage@500: {metrics.coverage_at_500:.1%} of exam words in top 500",
        "",
        "🎯 Precision Metrics",
        f"   Precision@100: {metrics.precision_at_100:.1%} of top 100 are actual exam words",
        f"   True Positives:  {metrics.true_positives_at_100}",
        f"   False Positives: {metrics.false_positives_at_100}",
        "",
        "📈 Ranking Quality",
        f"   NDCG@100: {metrics.ndcg_at_100:.4f}",
        f"   MAP:      {metrics.map_score:.4f}",
        "",
        "💰 ROI Metrics",
        f"   Estimated ROI@100: {metrics.estimated_roi_at_100:.3f} points/effort unit",
        f"   Level Distribution KL: {metrics.level_distribution_kl:.4f} (lower is better)",
        "",
        f"📝 Total Exam Words: {metrics.total_positives}",
    ]

    if metrics.coverage_by_level:
        lines.append("")
        lines.append("📚 Coverage by Level:")
        for level, cov in sorted(metrics.coverage_by_level.items()):
            lines.append(f"   L{level}: {cov:.1%}")

    return "\n".join(lines)
