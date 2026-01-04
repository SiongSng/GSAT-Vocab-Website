"""
Unified modern ML pipeline for GSAT vocabulary prediction.

Integrates all components:
- TOPSIS/EVL value estimation
- Embedding features
- Graph-based features
- Sense-level survival analysis
- Two-stage ensemble ranking
- Business-oriented evaluation

Usage:
    uv run python -m src.ml.pipeline --data extracted.json --vocab vocab.json
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from ..models.exam import AnnotationRole, ExamType

from .business_metrics import (
    BusinessMetrics,
    TemporalValidationResult,
    compute_business_metrics,
    generate_evaluation_report,
)
from .embeddings import EmbeddingFeatureExtractor, VocabEmbedder
from .ensemble import EnsembleConfig, EnsembleVocabRanker
from .features import FeatureExtractor, get_feature_names, WordFeatureData
from .graph import GraphFeatureExtractor, VocabGraph
from .sense_survival import SenseLevelSurvival
from .survival import TestingCycleModel
from .value import VocabValueEstimator

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False, show_path=False)],
)
logger = logging.getLogger(__name__)
console = Console()


@dataclass
class PipelineConfig:
    """Configuration for the modern ML pipeline"""

    # Target
    target_year: int = 116
    target_mode: str = "tested"  # tested, active_tested, answer_only

    # Training
    training_lookback_years: int = 10
    validation_years: list[int] | None = None  # Default: [111, 112, 113, 114]

    # Features
    use_embeddings: bool = True
    use_graph: bool = True
    use_sense_survival: bool = True
    use_value_estimation: bool = True

    # Ensemble
    ensemble_stage1_top_k: int = 500
    ensemble_stage1_recall_bias: float = 5.0

    # Output
    output_dir: Path = Path("data/output")
    save_model: bool = True


class ModernVocabPipeline:
    """
    Modern ML pipeline for GSAT vocabulary prediction.

    Orchestrates all components for training, validation, and prediction.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config

        # Ensemble ranker
        ensemble_config = EnsembleConfig(
            stage1_top_k=config.ensemble_stage1_top_k,
            stage1_recall_bias=config.ensemble_stage1_recall_bias,
            use_embeddings=config.use_embeddings,
            use_graph=config.use_graph,
            use_sense_survival=config.use_sense_survival,
            use_value_estimation=config.use_value_estimation,
        )
        self.ranker = EnsembleVocabRanker(config=ensemble_config)

        # Feature extraction
        self.base_extractor = FeatureExtractor(current_year=config.target_year)

        # Results tracking
        self.training_info: dict[str, Any] = {}
        self.validation_results: TemporalValidationResult | None = None

    def load_data(
        self,
        extracted_path: Path,
        vocab_path: Path | None = None,
    ) -> list[dict]:
        """
        Load and merge data from extracted.json and vocab.json.
        """
        console.print(f"[cyan]Loading data from {extracted_path}...[/]")

        with open(extracted_path, encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("words", []) + data.get("phrases", [])
        console.print(f"  Loaded {len(entries)} entries")

        # Merge with vocab.json for semantic data
        if vocab_path and vocab_path.exists():
            console.print(f"[cyan]Merging semantic data from {vocab_path}...[/]")

            with open(vocab_path, encoding="utf-8") as f:
                vocab_data = json.load(f)

            vocab_map = {}
            for w in vocab_data.get("words", []):
                vocab_map[w["lemma"]] = w
            for p in vocab_data.get("phrases", []):
                vocab_map[p["lemma"]] = p

            merged = 0
            for entry in entries:
                lemma = entry.get("lemma")
                if lemma in vocab_map:
                    v = vocab_map[lemma]
                    entry["senses"] = v.get("senses", [])
                    entry["synonyms"] = v.get("synonyms", [])
                    entry["antonyms"] = v.get("antonyms", [])
                    merged += 1

            console.print(f"  Merged semantic data for {merged} entries")

        return entries

    def prepare_features(
        self,
        entries: list[dict],
        target_years: list[int],
    ) -> tuple[np.ndarray, np.ndarray, list[dict]]:
        """
        Prepare feature matrix for training/prediction.

        Returns:
            X: Feature matrix
            y: Labels
            meta: Metadata for each sample
        """
        X_list = []
        y_list = []
        meta_list = []

        feature_names = get_feature_names()

        for year in target_years:
            extractor = FeatureExtractor(current_year=year)

            for entry in entries:
                word_data = extractor.extract_word_data(entry)

                features = extractor.extract_feature_vector(
                    word_data,
                    target_year=year,
                    external_features=None
                )

                if features is None:
                    continue

                label = extractor.get_target_label(
                    word_data, year, self.config.target_mode
                )

                X_list.append(features)
                y_list.append(label)
                meta_list.append({
                    "lemma": word_data.lemma,
                    "level": word_data.level,
                    "year": year,
                    "entry": entry,
                })

        X = np.array(X_list)
        y = np.array(y_list)

        console.print(f"  Prepared {len(X)} samples, {sum(y)} positives")

        return X, y, meta_list

    def train(
        self,
        entries: list[dict],
        validate: bool = True,
    ) -> dict[str, Any]:
        """
        Train the full ensemble model.
        """
        console.print("\n[bold cyan]═══ Training Modern ML Pipeline ═══[/]")

        target_year = self.config.target_year

        # Prepare training data
        training_years = list(range(
            max(105, target_year - self.config.training_lookback_years),
            target_year
        ))
        console.print(f"Training years: {training_years}")

        X_train, y_train, meta_train = self.prepare_features(entries, training_years)

        if len(X_train) == 0:
            raise ValueError("No training data available")

        # Extract entries for feature extractors
        train_entries = [m["entry"] for m in meta_train]

        # Train ensemble
        console.print("\n[cyan]Training ensemble model...[/]")
        feature_names = get_feature_names()

        metrics = self.ranker.train(
            vocab_data=train_entries,
            base_features=X_train,
            y=y_train,
            groups=None,
            base_feature_names=feature_names,
            target_year=target_year,
        )

        console.print(f"  Coverage@100: {metrics.get('coverage_at_100', 0):.4f}")
        console.print(f"  NDCG@100: {metrics.get('ndcg_at_100', 0):.4f}")
        console.print(f"  Total features: {metrics.get('n_features', 0)}")

        # Temporal validation
        if validate:
            validation_years = self.config.validation_years or [111, 112, 113, 114]
            validation_years = [y for y in validation_years if y < target_year]

            if validation_years:
                console.print(f"\n[cyan]Running temporal validation on {validation_years}...[/]")
                self.validation_results = self._temporal_validation(
                    entries, validation_years
                )

        # Feature importance
        importance = self.ranker.get_feature_importance()
        top_features = sorted(
            importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]

        # Store training info
        self.training_info = {
            "target_year": target_year,
            "target_mode": self.config.target_mode,
            "training_years": training_years,
            "n_samples": len(X_train),
            "n_positives": int(sum(y_train)),
            "n_features": metrics.get("n_features", 0),
            "metrics": metrics,
            "top_features": [
                {"name": name, "importance": float(imp)}
                for name, imp in top_features
            ],
            "ensemble_weights": self.ranker.ensemble_weights,
            "generated_at": datetime.now(UTC).isoformat(),
        }

        # Print top features
        self._print_top_features(top_features)

        return self.training_info

    def _temporal_validation(
        self,
        entries: list[dict],
        test_years: list[int],
    ) -> TemporalValidationResult:
        """
        Perform temporal cross-validation.
        """
        result = TemporalValidationResult(years=test_years)
        coverages = []
        ndcgs = []

        for val_year in test_years:
            console.print(f"  Validating year {val_year}...")

            # Train on years before val_year
            train_years = list(range(max(105, val_year - 5), val_year))
            X_train, y_train, meta_train = self.prepare_features(entries, train_years)

            # Prepare validation data
            X_val, y_val, meta_val = self.prepare_features(entries, [val_year])

            if len(X_val) < 100 or sum(y_val) < 5:
                console.print(f"    [yellow]Skipping: insufficient data[/]")
                continue

            # Train a fresh model for this fold
            fold_ranker = EnsembleVocabRanker(config=self.ranker.config)
            train_entries = [m["entry"] for m in meta_train]

            fold_ranker.train(
                vocab_data=train_entries,
                base_features=X_train,
                y=y_train,
                groups=None,
                base_feature_names=get_feature_names(),
                target_year=val_year,
            )

            # Predict on validation
            val_entries = [m["entry"] for m in meta_val]
            y_pred = fold_ranker.predict(val_entries, X_val, val_year)

            # Compute metrics
            levels = np.array([m["level"] or 3 for m in meta_val])
            metrics = compute_business_metrics(y_val, y_pred, word_levels=levels)

            result.metrics_per_year[val_year] = metrics
            coverages.append(metrics.coverage_at_100)
            ndcgs.append(metrics.ndcg_at_100)

            console.print(
                f"    Coverage@100={metrics.coverage_at_100:.4f}, "
                f"NDCG@100={metrics.ndcg_at_100:.4f}, "
                f"Positives={metrics.total_positives}"
            )

        if coverages:
            result.avg_coverage_100 = float(np.mean(coverages))
            result.avg_ndcg_100 = float(np.mean(ndcgs))
            result.std_coverage_100 = float(np.std(coverages))
            result.std_ndcg_100 = float(np.std(ndcgs))

            console.print(f"\n  [bold]Average Coverage@100: {result.avg_coverage_100:.4f} ± {result.std_coverage_100:.4f}[/]")
            console.print(f"  [bold]Average NDCG@100: {result.avg_ndcg_100:.4f} ± {result.std_ndcg_100:.4f}[/]")

        return result

    def predict(
        self,
        entries: list[dict],
    ) -> list[dict]:
        """
        Generate predictions for vocabulary entries.

        Returns list of (lemma, level, score) sorted by score descending.
        """
        console.print(f"\n[cyan]Generating predictions for year {self.config.target_year}...[/]")

        # Prepare features
        X, _, meta = self.prepare_features(entries, [self.config.target_year])

        if len(X) == 0:
            return []

        # Predict
        entry_list = [m["entry"] for m in meta]
        scores = self.ranker.predict(entry_list, X, self.config.target_year)

        # Build results
        results = []
        for i, m in enumerate(meta):
            results.append({
                "lemma": m["lemma"],
                "level": m["level"],
                "score": float(scores[i]),
            })

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        return results

    def _print_top_features(self, top_features: list[tuple[str, float]]):
        """Print top features table"""
        table = Table(title="Top 20 Features by Importance")
        table.add_column("Rank", style="cyan", justify="right")
        table.add_column("Feature", style="magenta")
        table.add_column("Importance", style="green", justify="right")

        for i, (name, imp) in enumerate(top_features):
            table.add_row(str(i + 1), name, f"{imp:.4f}")

        console.print(table)

    def print_predictions(self, predictions: list[dict], top_k: int = 50):
        """Print top predictions"""
        table = Table(title=f"Top {top_k} Predictions for Year {self.config.target_year}")
        table.add_column("Rank", style="cyan", justify="right")
        table.add_column("Lemma", style="magenta")
        table.add_column("Level", justify="center")
        table.add_column("Score", style="green", justify="right")

        for i, pred in enumerate(predictions[:top_k]):
            table.add_row(
                str(i + 1),
                pred["lemma"],
                str(pred["level"] or "?"),
                f"{pred['score']:.4f}"
            )

        console.print(table)

    def save(self, output_dir: Path | None = None):
        """Save model and training info"""
        output_dir = output_dir or self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save model
        model_path = output_dir / "ensemble_model.pkl"
        self.ranker.save(model_path)
        console.print(f"[green]✓[/] Model saved to {model_path}")

        # Save training info
        info_path = output_dir / "training_info.json"
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(self.training_info, f, ensure_ascii=False, indent=2)
        console.print(f"[green]✓[/] Training info saved to {info_path}")

        # Save validation results
        if self.validation_results:
            val_path = output_dir / "validation_results.json"
            val_data = {
                "years": self.validation_results.years,
                "avg_coverage_100": self.validation_results.avg_coverage_100,
                "avg_ndcg_100": self.validation_results.avg_ndcg_100,
                "std_coverage_100": self.validation_results.std_coverage_100,
                "per_year": {
                    str(y): {
                        "coverage_at_100": m.coverage_at_100,
                        "ndcg_at_100": m.ndcg_at_100,
                        "total_positives": m.total_positives,
                    }
                    for y, m in self.validation_results.metrics_per_year.items()
                }
            }
            with open(val_path, "w", encoding="utf-8") as f:
                json.dump(val_data, f, indent=2)
            console.print(f"[green]✓[/] Validation results saved to {val_path}")

    @classmethod
    def load(cls, model_path: Path, config: PipelineConfig | None = None) -> "ModernVocabPipeline":
        """Load saved pipeline"""
        config = config or PipelineConfig()
        pipeline = cls(config)
        pipeline.ranker = EnsembleVocabRanker.load(model_path)
        return pipeline


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Modern ML Pipeline for GSAT Vocabulary Prediction"
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/intermediate/extracted.json"),
        help="Path to extracted.json",
    )
    parser.add_argument(
        "--vocab",
        type=Path,
        default=Path("data/output/vocab.json"),
        help="Path to vocab.json (for semantic data)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/output"),
        help="Output directory",
    )
    parser.add_argument(
        "--target-year",
        type=int,
        default=116,
        help="Target year for prediction",
    )
    parser.add_argument(
        "--target-mode",
        choices=["tested", "active_tested", "answer_only"],
        default="tested",
        help="Target mode",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip temporal validation",
    )
    parser.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Disable embedding features",
    )
    parser.add_argument(
        "--no-graph",
        action="store_true",
        help="Disable graph features",
    )
    args = parser.parse_args()

    # Configure
    config = PipelineConfig(
        target_year=args.target_year,
        target_mode=args.target_mode,
        output_dir=args.output,
        use_embeddings=not args.no_embeddings,
        use_graph=not args.no_graph,
    )

    # Create pipeline
    pipeline = ModernVocabPipeline(config)

    # Load data
    entries = pipeline.load_data(args.data, args.vocab)

    # Train
    pipeline.train(entries, validate=not args.skip_validation)

    # Generate predictions
    predictions = pipeline.predict(entries)
    pipeline.print_predictions(predictions)

    # Save
    pipeline.save()


if __name__ == "__main__":
    main()
