"""
Evaluation metrics for GSAT vocabulary prediction model.

Implements specialized metrics for vocabulary distribution prediction:
- NDCG@K (Normalized Discounted Cumulative Gain): Primary metric
- Precision@K: Fraction of top-K words that were actually tested
- Recall@K: Fraction of tested words found in top-K
- KL Divergence: Distribution similarity
"""

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import ndcg_score


@dataclass
class EvaluationMetrics:
    ndcg_50: float
    ndcg_100: float
    ndcg_200: float
    precision_100: float
    recall_100: float
    kl_divergence: float


def compute_metrics(
    y_true: np.ndarray,
    y_pred_scores: np.ndarray,
    k_list: list[int] | None = None,
) -> EvaluationMetrics:
    """
    Compute comprehensive evaluation metrics.

    Args:
        y_true: Binary ground truth (1 = tested, 0 = not tested)
        y_pred_scores: Predicted importance scores
        k_list: List of K values for @K metrics (default: [50, 100, 200])

    Returns:
        EvaluationMetrics object
    """
    if k_list is None:
        k_list = [50, 100, 200]

    # Handle empty/invalid inputs
    if len(y_true) == 0 or np.sum(y_true) == 0:
        return EvaluationMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    # NDCG scores
    ndcg_50 = ndcg_score([y_true], [y_pred_scores], k=50)
    ndcg_100 = ndcg_score([y_true], [y_pred_scores], k=100)
    ndcg_200 = ndcg_score([y_true], [y_pred_scores], k=200)

    # Sort indices by score descending
    sorted_indices = np.argsort(y_pred_scores)[::-1]
    top_100_indices = sorted_indices[:100]

    # Precision@100
    tp_100 = np.sum(y_true[top_100_indices])
    precision_100 = tp_100 / 100

    # Recall@100
    total_positives = np.sum(y_true)
    recall_100 = tp_100 / max(1, total_positives)

    # KL Divergence (Distribution comparision)
    # Convert scores to probability distribution via softmax
    # This is a proxy for comparing "expected distribution" vs "actual distribution"
    kl_div = _compute_kl_divergence(y_true, y_pred_scores)

    return EvaluationMetrics(
        ndcg_50=ndcg_50,
        ndcg_100=ndcg_100,
        ndcg_200=ndcg_200,
        precision_100=precision_100,
        recall_100=recall_100,
        kl_divergence=kl_div,
    )


def _compute_kl_divergence(y_true: np.ndarray, y_scores: np.ndarray) -> float:
    """
    Compute KL Divergence between predicted distribution and true distribution.
    Uses softmax to convert scores to probabilities.
    """
    # Softmax for prediction distribution
    exp_scores = np.exp(y_scores - np.max(y_scores))
    p_pred = exp_scores / np.sum(exp_scores)

    # Normalize ground truth to probability distribution
    # Add epsilon to avoid zero probabilities if needed, but ground truth usually sparse
    total_true = np.sum(y_true)
    if total_true == 0:
        return 0.0

    p_true = y_true / total_true

    # KL(P || Q) = sum(P(x) * log(P(x) / Q(x)))
    # We only sum where P(x) > 0
    epsilon = 1e-10
    mask = p_true > 0
    kl = np.sum(p_true[mask] * np.log(p_true[mask] / (p_pred[mask] + epsilon)))

    return float(kl)
