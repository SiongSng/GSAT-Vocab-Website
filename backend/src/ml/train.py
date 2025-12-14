"""
CLI tool for training GSAT vocabulary importance prediction model.

Usage:
    uv run python -m src.ml.train \
        --data data/intermediate/cleaned.json \
        --output data/output/importance_model.pkl \
        --target-mode tested

Target modes:
    - "appeared": Word appeared anywhere in exam (easiest, inflated metrics)
    - "tested": Word was answer/keyword/distractor (recommended, honest metrics)
    - "active_tested": Word was answer/keyword only (harder, more valuable)
    - "answer_only": Word was correct answer (strictest)

This trains a Gradient Boosting model to predict which words are likely
to be tested in future exams, based on historical patterns.
"""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .features import FeatureExtractor, get_feature_names
from .model import ImportanceModel, train_model
from .weights import CURRICULUM_CUTOFF_YEAR, TRIAL_YEARS

TARGET_MODES = ["appeared", "tested", "active_tested", "answer_only"]

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False, show_path=False)],
)
logger = logging.getLogger(__name__)
console = Console()


def load_cleaned_data(path: Path) -> dict:
    console.print(f"[cyan]Loading data from {path}...[/]")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def analyze_data(data: dict) -> dict:
    entries = data.get("entries", [])
    distractor_groups = data.get("distractor_groups", [])
    essay_topics = data.get("essay_topics", [])

    all_years = set()
    tier_counts = {}
    role_counts = {}
    exam_type_counts = {}

    for entry in entries:
        tier = entry.get("tier", "unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

        for occ in entry.get("occurrences", []):
            year = occ.get("source", {}).get("year", 0)
            if year > 0:
                all_years.add(year)
            role = occ.get("role", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1
            exam_type = occ.get("source", {}).get("exam_type", "unknown")
            exam_type_counts[exam_type] = exam_type_counts.get(exam_type, 0) + 1

    essay_word_count = sum(len(t.get("suggested_words", [])) for t in essay_topics)

    return {
        "total_entries": len(entries),
        "distractor_groups": len(distractor_groups),
        "essay_topics": len(essay_topics),
        "essay_suggested_words": essay_word_count,
        "year_range": (min(all_years), max(all_years)) if all_years else (0, 0),
        "tier_counts": tier_counts,
        "role_counts": role_counts,
        "exam_type_counts": exam_type_counts,
    }


def temporal_validation(
    entries: list[dict],
    distractor_groups: list[dict],
    essay_topics: list[dict],
    test_years: list[int],
    target_mode: str = "tested",
    gsat_only: bool = False,
) -> dict:
    import numpy as np
    from sklearn.metrics import roc_auc_score

    results = {
        "year": [],
        "auc": [],
        "cv_auc": [],
        "samples": [],
        "positive": [],
        "positive_rate": [],
    }

    for target_year in test_years:
        console.print(f"  [dim]Validating year {target_year}...[/]")

        extractor = FeatureExtractor(current_year=target_year)
        extractor.build_distractor_index(distractor_groups)
        extractor.build_essay_index(essay_topics)

        X_data = []
        y_data = []

        for entry in entries:
            if gsat_only:
                filtered_occurrences = [
                    occ
                    for occ in entry.get("occurrences", [])
                    if occ.get("source", {}).get("exam_type", "").startswith("gsat")
                ]
                if not filtered_occurrences:
                    continue
                entry = {**entry, "occurrences": filtered_occurrences}

            word_data = extractor.extract_word_data(entry)
            features = extractor.extract_feature_vector(
                word_data, target_year=target_year, lookback_years=15
            )

            if features is None:
                continue

            label = extractor.get_target_label(word_data, target_year, target_mode)
            X_data.append(features)
            y_data.append(label)

        if len(X_data) < 100 or sum(y_data) < 5:
            console.print(f"    [yellow]Skipping: only {sum(y_data)} positive samples[/]")
            continue

        X = np.array(X_data)
        y = np.array(y_data)

        model = ImportanceModel(target_mode=target_mode)
        metrics = model.train(X, y, n_estimators=100, max_depth=3)

        y_prob = model.predict_proba(X)
        auc = roc_auc_score(y, y_prob)

        results["year"].append(target_year)
        results["auc"].append(auc)
        results["cv_auc"].append(metrics.cv_auc_mean)
        results["samples"].append(len(X))
        results["positive"].append(sum(y_data))
        results["positive_rate"].append(sum(y_data) / len(y_data))

    return results


def compare_target_modes(
    entries: list[dict],
    distractor_groups: list[dict],
    essay_topics: list[dict],
    test_years: list[int],
    gsat_only: bool = False,
) -> dict[str, dict]:
    import numpy as np

    all_results = {}

    for mode in TARGET_MODES:
        console.print(f"\n[cyan]Testing mode: {mode}[/]")
        results = temporal_validation(
            entries,
            distractor_groups,
            essay_topics,
            test_years,
            target_mode=mode,
            gsat_only=gsat_only,
        )

        if results["year"]:
            avg_auc = np.mean(results["auc"])
            avg_cv_auc = np.mean(results["cv_auc"])
            avg_positive_rate = np.mean(results["positive_rate"])
            all_results[mode] = {
                "avg_auc": avg_auc,
                "avg_cv_auc": avg_cv_auc,
                "avg_positive_rate": avg_positive_rate,
                "yearly_results": results,
            }
            console.print(f"  CV AUC: {avg_cv_auc:.4f}, Positive rate: {avg_positive_rate:.1%}")

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Train GSAT vocabulary importance prediction model"
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/intermediate/cleaned.json"),
        help="Path to cleaned.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/output/importance_model.pkl"),
        help="Output path for trained model",
    )
    parser.add_argument(
        "--output-info",
        type=Path,
        default=None,
        help="Output path for training info JSON (optional)",
    )
    parser.add_argument(
        "--target-year",
        type=int,
        default=114,
        help="Target year for prediction (default: 114)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip temporal cross-validation",
    )
    parser.add_argument(
        "--target-mode",
        type=str,
        choices=TARGET_MODES,
        default="active_tested",
        help="Target mode (default: active_tested)",
    )
    parser.add_argument(
        "--compare-modes",
        action="store_true",
        help="Compare all target modes before training",
    )
    parser.add_argument(
        "--gsat-only",
        action="store_true",
        help="Filter out AST data, train on GSAT only",
    )
    args = parser.parse_args()

    if not args.data.exists():
        console.print(f"[red]Error: Data file not found: {args.data}[/]")
        console.print("\nPlease run the pipeline first to generate cleaned.json:")
        console.print("  uv run python -m src.cli run")
        sys.exit(1)

    data = load_cleaned_data(args.data)
    analysis = analyze_data(data)

    table = Table(title="Data Summary", show_header=False)
    table.add_column(style="dim")
    table.add_column(style="bold")
    table.add_row("Total entries", str(analysis["total_entries"]))
    table.add_row("Distractor groups", str(analysis["distractor_groups"]))
    table.add_row("Essay topics", str(analysis["essay_topics"]))
    table.add_row("Essay suggested words", str(analysis["essay_suggested_words"]))
    table.add_row("Year range", f"{analysis['year_range'][0]} - {analysis['year_range'][1]}")
    table.add_row("Curriculum cutoff", f"Year {CURRICULUM_CUTOFF_YEAR}")
    table.add_row("Trial years", ", ".join(str(y) for y in sorted(TRIAL_YEARS)))
    console.print(table)
    console.print()

    if args.gsat_only:
        console.print("[yellow]GSAT-only mode enabled: filtering out AST data[/]")
        console.print()

    entries = data.get("entries", [])
    distractor_groups = data.get("distractor_groups", [])
    essay_topics = data.get("essay_topics", [])
    max_year = analysis["year_range"][1]
    test_years = list(range(max(110, max_year - 4), max_year + 1))

    if args.compare_modes:
        console.print("[cyan]Comparing all target modes...[/]")
        mode_comparison = compare_target_modes(
            entries, distractor_groups, essay_topics, test_years, gsat_only=args.gsat_only
        )

        comparison_table = Table(title="Target Mode Comparison")
        comparison_table.add_column("Mode", style="cyan")
        comparison_table.add_column("CV AUC", style="green")
        comparison_table.add_column("Positive Rate", style="yellow")
        comparison_table.add_column("Interpretation", style="dim")

        interpretations = {
            "appeared": "Predicting if word appears anywhere (too easy)",
            "tested": "Predicting if word is tested (balanced)",
            "active_tested": "Predicting if word is answer/keyword (recommended)",
            "answer_only": "Predicting if word is correct answer (strictest)",
        }

        for mode, result in mode_comparison.items():
            comparison_table.add_row(
                mode,
                f"{result['avg_cv_auc']:.4f}",
                f"{result['avg_positive_rate']:.1%}",
                interpretations.get(mode, ""),
            )

        console.print(comparison_table)
        console.print()

    if not args.skip_validation:
        console.print(f"[cyan]Running temporal validation (mode: {args.target_mode})...[/]")

        val_results = temporal_validation(
            entries,
            distractor_groups,
            essay_topics,
            test_years,
            target_mode=args.target_mode,
            gsat_only=args.gsat_only,
        )

        if val_results["year"]:
            val_table = Table(title=f"Temporal Validation (mode: {args.target_mode})")
            val_table.add_column("Year", style="cyan")
            val_table.add_column("Train AUC", style="dim")
            val_table.add_column("CV AUC", style="green")
            val_table.add_column("Samples", style="dim")
            val_table.add_column("Positive", style="dim")
            val_table.add_column("Rate", style="yellow")

            for i, year in enumerate(val_results["year"]):
                val_table.add_row(
                    str(year),
                    f"{val_results['auc'][i]:.4f}",
                    f"{val_results['cv_auc'][i]:.4f}",
                    str(val_results["samples"][i]),
                    str(val_results["positive"][i]),
                    f"{val_results['positive_rate'][i]:.1%}",
                )

            import numpy as np

            avg_cv_auc = np.mean(val_results["cv_auc"])
            avg_rate = np.mean(val_results["positive_rate"])
            val_table.add_row(
                "Average", "", f"[bold]{avg_cv_auc:.4f}[/]", "", "", f"{avg_rate:.1%}"
            )

            console.print(val_table)
            console.print()

    console.print(
        f"[cyan]Training final model (target: year {args.target_year}, mode: {args.target_mode})...[/]"
    )

    model, training_info = train_model(
        entries=entries,
        distractor_groups=distractor_groups,
        essay_topics=essay_topics,
        target_year=args.target_year,
        lookback_years=20,
        target_mode=args.target_mode,
        gsat_only=args.gsat_only,
    )

    metrics_table = Table(title="Model Performance")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", style="green")

    metrics = training_info["metrics"]
    metrics_table.add_row("Training AUC", f"{metrics['auc']:.4f}")
    metrics_table.add_row(
        "CV AUC", f"[bold]{metrics['cv_auc_mean']:.4f}[/] ± {metrics['cv_auc_std']:.4f}"
    )
    metrics_table.add_row("Accuracy", f"{metrics['accuracy']:.4f}")
    metrics_table.add_row("Precision", f"{metrics['precision']:.4f}")
    metrics_table.add_row("Recall", f"{metrics['recall']:.4f}")
    metrics_table.add_row("F1 Score", f"{metrics['f1']:.4f}")

    console.print(metrics_table)
    console.print()

    feat_table = Table(title="Top 10 Feature Importance")
    feat_table.add_column("Rank", style="dim")
    feat_table.add_column("Feature", style="cyan")
    feat_table.add_column("Importance", style="green")

    for i, feat in enumerate(training_info["top_features"], 1):
        feat_table.add_row(str(i), feat["name"], f"{feat['importance']:.4f}")

    console.print(feat_table)
    console.print()

    model.save(args.output)
    console.print(f"[green]✓[/] Model saved to {args.output}")

    output_info_path = args.output_info or args.output.with_suffix(".json").with_name(
        "model_info.json"
    )
    training_info["generated_at"] = datetime.now(UTC).isoformat()
    training_info["model_path"] = str(args.output)
    training_info["feature_count"] = len(get_feature_names())

    with open(output_info_path, "w", encoding="utf-8") as f:
        json.dump(training_info, f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/] Training info saved to {output_info_path}")


if __name__ == "__main__":
    main()
