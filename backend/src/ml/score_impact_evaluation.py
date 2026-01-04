"""
Score Impact Evaluation for GSAT Vocabulary Prediction

This script evaluates ML predictions based on actual SCORE IMPACT rather than
binary tested/not-tested classification.

Key insight from IMPROVEMENT_PLAN.md:
- Different contexts have different score values
- Correct answers are worth more than just appearing in reading passages
- Translation keywords are the highest value (student must produce the word)

Score Impact Model:
- correct_answer (vocabulary/cloze): Direct scoring opportunity
- tested_keyword (translation): Highest value - must produce word
- distractor: Recognition value only
- reading passage: Context understanding

Usage:
    uv run python -m src.ml.score_impact_evaluation
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .business_metrics import compute_business_metrics, BusinessMetrics
from .features import FeatureExtractor, get_feature_names
from .ranker import VocabRanker
from .survival import TestingCycleModel

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False, show_path=False)],
)
logger = logging.getLogger(__name__)
console = Console()


# Score impact weights based on GSAT scoring
ROLE_SCORE_IMPACT = {
    "tested_keyword": 3.0,      # Translation: must produce word
    "correct_answer": 2.0,      # Must choose/fill correct answer
    "question_prompt": 1.0,     # Understanding context
    "distractor": 0.5,          # Recognition only
    "passage_word": 0.3,        # Reading comprehension context
    "option": 0.3,              # Recognition in options
    "none": 0.1,                # Background vocabulary
}

SECTION_MULTIPLIER = {
    "vocabulary": 1.5,      # Direct vocab test
    "cloze": 1.3,           # Contextual understanding + production
    "translation": 2.0,     # Highest: must produce correct word
    "reading": 0.8,         # Recognition + comprehension
    "discourse": 1.0,       # Structural understanding
    "essay": 1.5,           # Production ability
}


@dataclass
class ScoreImpactMetrics:
    """Metrics based on potential score impact"""

    # Total potential score impact captured
    total_impact_at_50: float = 0.0
    total_impact_at_100: float = 0.0
    total_impact_at_200: float = 0.0

    # Impact coverage (% of total potential impact captured)
    impact_coverage_at_50: float = 0.0
    impact_coverage_at_100: float = 0.0
    impact_coverage_at_200: float = 0.0

    # High-value word coverage (translation/answer keywords)
    high_value_coverage_at_100: float = 0.0

    # ROI metrics
    impact_per_word_at_100: float = 0.0

    # Breakdown by section
    section_coverage: dict[str, float] = field(default_factory=dict)

    # Breakdown by role
    role_coverage: dict[str, float] = field(default_factory=dict)

    # Reference comparison
    actual_tested_count: int = 0
    actual_total_impact: float = 0.0


def compute_word_score_impact(
    contexts: list[dict],
    target_year: int,
) -> float:
    """Compute the score impact value of a word for a specific year."""
    impact = 0.0

    for ctx in contexts:
        source = ctx.get("source", {})
        year = source.get("year", 0)

        if year != target_year:
            continue

        role = source.get("role", "none")
        section = source.get("section_type", "")

        role_weight = ROLE_SCORE_IMPACT.get(role, 0.1)
        section_mult = SECTION_MULTIPLIER.get(section, 1.0)

        impact += role_weight * section_mult

    return impact


def compute_score_impact_from_frequency(
    frequency: dict,
    target_year: int,
) -> dict:
    """Compute score impact breakdown from frequency data."""
    # Check if year is in frequency
    years = frequency.get("years", [])
    if target_year not in years:
        return {"total": 0.0, "by_role": {}, "by_section": {}}

    # Estimate impact from by_role and by_section
    by_role = frequency.get("by_role", {})
    by_section = frequency.get("by_section", {})

    total = 0.0
    role_impact = {}
    section_impact = {}

    for role, count in by_role.items():
        w = ROLE_SCORE_IMPACT.get(role, 0.1)
        impact = w * count
        role_impact[role] = impact
        total += impact

    for section, count in by_section.items():
        m = SECTION_MULTIPLIER.get(section, 1.0)
        section_impact[section] = count * m

    return {
        "total": total,
        "by_role": role_impact,
        "by_section": section_impact,
    }


def evaluate_score_impact(
    entries: list[dict],
    predictions: list[tuple[str, float]],  # [(lemma, score), ...]
    target_year: int,
    k_list: list[int] | None = None,
) -> ScoreImpactMetrics:
    """
    Evaluate predictions based on score impact.

    Args:
        entries: All vocabulary entries with contexts
        predictions: Sorted predictions [(lemma, score), ...] highest first
        target_year: Year to evaluate
        k_list: K values for evaluation
    """
    if k_list is None:
        k_list = [50, 100, 200]

    # Build entry lookup
    entry_map = {e.get("lemma", ""): e for e in entries}

    # Compute actual score impact for all words
    word_impacts = {}
    total_actual_impact = 0.0
    high_value_words = set()  # Words with high impact roles

    for entry in entries:
        lemma = entry.get("lemma", "")
        contexts = entry.get("contexts", [])

        impact = compute_word_score_impact(contexts, target_year)
        word_impacts[lemma] = impact
        total_actual_impact += impact

        # Check for high-value roles (answer/keyword)
        for ctx in contexts:
            source = ctx.get("source", {})
            if source.get("year") == target_year:
                role = source.get("role", "")
                if role in ["tested_keyword", "correct_answer"]:
                    high_value_words.add(lemma)
                    break

    # Count actual tested words
    actual_tested = sum(1 for imp in word_impacts.values() if imp > 0)

    metrics = ScoreImpactMetrics(
        actual_tested_count=actual_tested,
        actual_total_impact=total_actual_impact,
    )

    # Compute metrics at each K
    pred_lemmas = [p[0] for p in predictions]

    for k in k_list:
        if k > len(pred_lemmas):
            continue

        top_k = pred_lemmas[:k]

        # Total impact captured
        impact_captured = sum(word_impacts.get(lemma, 0) for lemma in top_k)

        # Coverage
        coverage = impact_captured / total_actual_impact if total_actual_impact > 0 else 0

        setattr(metrics, f"total_impact_at_{k}", impact_captured)
        setattr(metrics, f"impact_coverage_at_{k}", coverage)

        if k == 100:
            # High-value coverage
            high_value_captured = sum(1 for lemma in top_k if lemma in high_value_words)
            high_value_coverage = high_value_captured / len(high_value_words) if high_value_words else 0
            metrics.high_value_coverage_at_100 = high_value_coverage

            # Impact per word
            metrics.impact_per_word_at_100 = impact_captured / k

    return metrics


def run_temporal_evaluation(
    data_path: Path,
    test_years: list[int],
    target_mode: str = "tested",
) -> dict:
    """Run evaluation on historical years."""

    console.print(f"[cyan]Loading data from {data_path}...[/]")
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("words", []) + data.get("phrases", [])
    console.print(f"[green]✓[/] Loaded {len(entries)} entries")

    feature_names = get_feature_names()

    results = {
        "years": [],
        "business_metrics": {},
        "score_impact_metrics": {},
    }

    for target_year in test_years:
        console.print(f"\n[bold cyan]=== Evaluating Year {target_year} ===[/]")

        # Training years (expanding window)
        train_years = list(range(max(105, target_year - 10), target_year))
        console.print(f"[dim]Training on years: {train_years}[/]")

        # 1. Train Survival Model
        surv_model = _train_survival_model(entries, min(train_years))

        # 2. Build synonym history
        future_ex = FeatureExtractor(current_year=200)
        lemma_history = {}
        for entry in entries:
            wd = future_ex.extract_word_data(entry)
            lemma_history[wd.lemma.lower()] = wd.years_tested

        # 3. Prepare training data
        X_train_list = []
        y_train_list = []
        groups_list = []

        for year in train_years:
            extractor = FeatureExtractor(current_year=year)
            year_X = []
            year_y = []

            for entry in entries:
                wd = extractor.extract_word_data(entry)
                feats = extractor.extract_feature_vector(wd, target_year=year)

                if feats is None:
                    continue

                # External features
                feats[-3] = 0.5  # survival_hazard placeholder
                feats[-2] = 0.0  # synonym_tested_freq placeholder

                label = extractor.get_target_label(wd, year, target_mode)
                year_X.append(feats)
                year_y.append(label)

            if year_X:
                X_train_list.append(np.array(year_X))
                y_train_list.append(np.array(year_y))
                groups_list.append(len(year_X))

        if not X_train_list:
            console.print(f"[yellow]No training data for year {target_year}[/]")
            continue

        X_train = np.vstack(X_train_list)
        y_train = np.concatenate(y_train_list)
        groups = np.array(groups_list)

        console.print(f"[dim]Training samples: {len(X_train)}, Positives: {int(y_train.sum())}[/]")

        # 4. Train ranker
        ranker = VocabRanker(n_estimators=200, learning_rate=0.05)
        ranker.train(X_train, y_train, groups, feature_names=feature_names)

        # 5. Predict for target year
        extractor = FeatureExtractor(current_year=target_year)
        predictions = []
        y_true = []
        word_levels = []

        for entry in entries:
            wd = extractor.extract_word_data(entry)
            feats = extractor.extract_feature_vector(wd, target_year=target_year)

            if feats is None:
                continue

            # External features
            if surv_model and surv_model.model:
                try:
                    h = surv_model.predict_hazard(np.array([feats]))
                    feats[-3] = float(h[0])
                except:
                    feats[-3] = 0.5
            else:
                feats[-3] = 0.5

            syn_cnt = 0
            for s in entry.get("synonyms", []):
                sl = s.lower()
                if sl in lemma_history:
                    syn_cnt += sum(1 for y in lemma_history[sl] if target_year - 5 <= y < target_year)
            feats[-2] = float(syn_cnt)

            score = ranker.predict(np.array([feats]))[0]
            predictions.append((wd.lemma, score, entry))

            label = extractor.get_target_label(wd, target_year, target_mode)
            y_true.append(label)
            word_levels.append(wd.level or 3)

        # Sort by score
        predictions.sort(key=lambda x: x[1], reverse=True)
        y_pred = np.array([p[1] for p in predictions])
        y_true = np.array(y_true)
        word_levels = np.array(word_levels)

        # Reorder y_true to match prediction order
        pred_order = [entries.index(p[2]) for p in predictions if p[2] in entries]

        # 6. Compute business metrics
        biz_metrics = compute_business_metrics(
            y_true, y_pred, word_levels=word_levels, k_list=[50, 100, 200, 500]
        )

        # 7. Compute score impact metrics
        pred_tuples = [(p[0], p[1]) for p in predictions]
        entry_list = [p[2] for p in predictions]
        impact_metrics = evaluate_score_impact(entry_list, pred_tuples, target_year)

        results["years"].append(target_year)
        results["business_metrics"][target_year] = biz_metrics
        results["score_impact_metrics"][target_year] = impact_metrics

        # Print results
        _print_year_results(target_year, biz_metrics, impact_metrics, predictions[:30])

    # Summary
    _print_summary(results)

    return results


def _train_survival_model(entries: list[dict], cutoff_year: int) -> TestingCycleModel:
    """Train survival model for hazard prediction."""
    extractor = FeatureExtractor(current_year=cutoff_year)

    X_list = []
    durations = []
    events = []

    for entry in entries:
        wd = extractor.extract_word_data(entry)
        tested_years = sorted([y for y in wd.years_tested if y < cutoff_year])

        if len(tested_years) >= 2:
            start_year = tested_years[-2]
            end_year = tested_years[-1]
            duration = end_year - start_year

            feat = extractor.extract_feature_vector(wd, target_year=start_year)
            if feat is not None:
                X_list.append(feat)
                durations.append(duration)
                events.append(1)

    model = TestingCycleModel()
    if X_list:
        try:
            model.fit(np.array(X_list), np.array(durations), np.array(events))
        except Exception as e:
            console.print(f"[yellow]Survival model training failed: {e}[/]")

    return model


def _print_year_results(
    year: int,
    biz: BusinessMetrics,
    impact: ScoreImpactMetrics,
    top_predictions: list,
):
    """Print evaluation results for a single year."""

    # Business metrics table
    console.print(f"\n[bold]Year {year} - Business Metrics[/]")

    biz_table = Table(show_header=True, header_style="bold")
    biz_table.add_column("Metric", style="cyan")
    biz_table.add_column("@50", justify="right")
    biz_table.add_column("@100", justify="right")
    biz_table.add_column("@200", justify="right")

    biz_table.add_row(
        "Coverage",
        f"{biz.coverage_at_50:.1%}",
        f"{biz.coverage_at_100:.1%}",
        f"{biz.coverage_at_200:.1%}",
    )
    biz_table.add_row(
        "Precision",
        f"{biz.precision_at_50:.1%}",
        f"{biz.precision_at_100:.1%}",
        f"{biz.precision_at_200:.1%}",
    )
    biz_table.add_row(
        "NDCG",
        f"{biz.ndcg_at_50:.4f}",
        f"{biz.ndcg_at_100:.4f}",
        f"{biz.ndcg_at_200:.4f}",
    )

    console.print(biz_table)
    console.print(f"[dim]Total tested words: {biz.total_positives}[/]")

    # Score impact metrics table
    console.print(f"\n[bold]Year {year} - Score Impact Metrics[/]")

    impact_table = Table(show_header=True, header_style="bold")
    impact_table.add_column("Metric", style="magenta")
    impact_table.add_column("@50", justify="right")
    impact_table.add_column("@100", justify="right")
    impact_table.add_column("@200", justify="right")

    impact_table.add_row(
        "Impact Coverage",
        f"{impact.impact_coverage_at_50:.1%}",
        f"{impact.impact_coverage_at_100:.1%}",
        f"{impact.impact_coverage_at_200:.1%}",
    )
    impact_table.add_row(
        "Total Impact",
        f"{impact.total_impact_at_50:.1f}",
        f"{impact.total_impact_at_100:.1f}",
        f"{impact.total_impact_at_200:.1f}",
    )

    console.print(impact_table)
    console.print(f"[dim]Actual total impact: {impact.actual_total_impact:.1f}[/]")
    console.print(f"[dim]High-value coverage @100: {impact.high_value_coverage_at_100:.1%}[/]")

    # Top predictions
    console.print(f"\n[bold]Top 30 Predictions[/]")
    pred_table = Table(show_header=True, header_style="bold dim")
    pred_table.add_column("Rank", justify="right", style="dim")
    pred_table.add_column("Lemma", style="cyan")
    pred_table.add_column("Level", justify="center")
    pred_table.add_column("Score", justify="right", style="green")
    pred_table.add_column("Actual", justify="center")

    for i, (lemma, score, entry) in enumerate(top_predictions):
        # Check if actually tested
        contexts = entry.get("contexts", [])
        was_tested = any(
            ctx.get("source", {}).get("year") == year and
            ctx.get("source", {}).get("role") in ["correct_answer", "tested_keyword", "distractor"]
            for ctx in contexts
        )

        pred_table.add_row(
            str(i + 1),
            lemma,
            str(entry.get("level", "?")),
            f"{score:.4f}",
            "✓" if was_tested else "",
        )

    console.print(pred_table)


def _print_summary(results: dict):
    """Print summary across all years."""
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]EVALUATION SUMMARY[/]")
    console.print("=" * 60)

    years = results["years"]

    # Average business metrics
    avg_cov_100 = np.mean([
        results["business_metrics"][y].coverage_at_100
        for y in years
    ])
    avg_ndcg_100 = np.mean([
        results["business_metrics"][y].ndcg_at_100
        for y in years
    ])
    avg_prec_100 = np.mean([
        results["business_metrics"][y].precision_at_100
        for y in years
    ])

    # Average score impact metrics
    avg_impact_cov_100 = np.mean([
        results["score_impact_metrics"][y].impact_coverage_at_100
        for y in years
    ])
    avg_hv_cov = np.mean([
        results["score_impact_metrics"][y].high_value_coverage_at_100
        for y in years
    ])

    summary_table = Table(title="Average Metrics Across All Years", show_header=True)
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Value", justify="right", style="green")

    summary_table.add_row("Coverage@100 (Binary)", f"{avg_cov_100:.1%}")
    summary_table.add_row("NDCG@100", f"{avg_ndcg_100:.4f}")
    summary_table.add_row("Precision@100", f"{avg_prec_100:.1%}")
    summary_table.add_row("---", "---")
    summary_table.add_row("Impact Coverage@100", f"{avg_impact_cov_100:.1%}")
    summary_table.add_row("High-Value Coverage@100", f"{avg_hv_cov:.1%}")

    console.print(summary_table)

    # Per-year breakdown
    year_table = Table(title="Per-Year Results", show_header=True)
    year_table.add_column("Year", style="cyan")
    year_table.add_column("Cov@100", justify="right")
    year_table.add_column("NDCG@100", justify="right")
    year_table.add_column("Impact Cov", justify="right")
    year_table.add_column("HV Cov", justify="right")
    year_table.add_column("Tested", justify="right", style="dim")

    for y in years:
        biz = results["business_metrics"][y]
        imp = results["score_impact_metrics"][y]
        year_table.add_row(
            str(y),
            f"{biz.coverage_at_100:.1%}",
            f"{biz.ndcg_at_100:.4f}",
            f"{imp.impact_coverage_at_100:.1%}",
            f"{imp.high_value_coverage_at_100:.1%}",
            str(biz.total_positives),
        )

    console.print(year_table)

    # Interpretation
    console.print("\n[bold]Interpretation:[/]")

    if avg_cov_100 >= 0.5:
        console.print(f"[green]✓[/] Coverage@100 = {avg_cov_100:.1%}: Good! Top 100 words cover >50% of tested words")
    else:
        console.print(f"[yellow]![/] Coverage@100 = {avg_cov_100:.1%}: Below 50% target")

    if avg_impact_cov_100 >= 0.5:
        console.print(f"[green]✓[/] Impact Coverage@100 = {avg_impact_cov_100:.1%}: Capturing high-value words well")
    else:
        console.print(f"[yellow]![/] Impact Coverage@100 = {avg_impact_cov_100:.1%}: Missing high-impact words")

    if avg_hv_cov >= 0.4:
        console.print(f"[green]✓[/] High-Value Coverage = {avg_hv_cov:.1%}: Good coverage of answer/keyword words")
    else:
        console.print(f"[red]✗[/] High-Value Coverage = {avg_hv_cov:.1%}: Missing critical answer words")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Score Impact Evaluation for GSAT Vocab Prediction")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/intermediate/extracted.json"),
        help="Path to extracted.json",
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=[112, 113, 114],
        help="Years to evaluate",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="tested",
        choices=["tested", "active_tested", "answer_only"],
        help="Target mode for training",
    )
    args = parser.parse_args()

    run_temporal_evaluation(args.data, args.years, args.mode)


if __name__ == "__main__":
    main()
