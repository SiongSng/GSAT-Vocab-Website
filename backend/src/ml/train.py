"""
CLI tool for training GSAT vocabulary importance prediction model.

Usage:
    uv run python -m src.ml.train \
        --data data/output/vocab.json \
        --output data/output/importance_model.pkl \
        --target-mode tested

Target modes:
    - "appeared": Word appeared anywhere in exam (easiest, inflated metrics)
    - "tested": Word was answer/keyword/distractor (recommended, honest metrics)
    - "active_tested": Word was answer/keyword only (harder, more valuable)
    - "answer_only": Word was correct answer (strictest)

This trains a Gradient Boosting model to predict which words are likely
to be tested in future exams, based on historical patterns.

Data source: vocab.json (Stage 5+ output with WSD-assigned senses)
"""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from src.models.cleaned import CleanedVocabData
from src.models.vocab import PhraseEntry, VocabEntry, WordEntry

from .evaluation import EvaluationMetrics, compute_metrics
from .features import FeatureExtractor, get_feature_names
from .ranker import VocabRanker
from .survival import TestingCycleModel, compute_duration_from_word_data
from .weights import CURRICULUM_CUTOFF_YEAR, TRIAL_YEARS

TARGET_MODES = ["appeared", "tested", "active_tested", "answer_only"]

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False, show_path=False)],
)
logger = logging.getLogger(__name__)
console = Console()


def load_vocab_data(vocab_path: Path) -> dict:
    """Load vocab.json which contains WSD-assigned senses.

    vocab.json structure:
    - words: list[WordEntry] with senses[].examples[] containing source info
    - phrases: list[PhraseEntry] with same structure
    - patterns: list[PatternEntry] (ignored for ML)
    """
    console.print(f"[cyan]Loading vocab data from {vocab_path}...[/]")
    with open(vocab_path, encoding="utf-8") as f:
        data = json.load(f)

    words = data.get("words", [])
    phrases = data.get("phrases", [])

    # Mark phrases for feature extraction
    for p in phrases:
        p["_is_phrase"] = True

    entries = words + phrases
    console.print(f"[green]✓[/] Loaded {len(words)} words + {len(phrases)} phrases = {len(entries)} entries")

    return {"entries": entries, "metadata": data.get("metadata", {})}


def analyze_data(data: dict) -> dict:
    entries = data.get("entries", [])

    all_years = set()
    role_counts: dict[str, int] = {}
    section_counts: dict[str, int] = {}

    for entry in entries:
        freq = entry.get("frequency", {})
        for y in freq.get("years", []):
            if y > 0:
                all_years.add(y)
        for role, count in freq.get("by_role", {}).items():
            role_counts[role] = role_counts.get(role, 0) + count
        for section, count in freq.get("by_section", {}).items():
            section_counts[section] = section_counts.get(section, 0) + count

    return {
        "total_entries": len(entries),
        "year_range": (min(all_years), max(all_years)) if all_years else (0, 0),
        "role_counts": role_counts,
        "section_counts": section_counts,
    }




def _train_survival_model(
    entries: list[dict], 
    cutoff_year: int
) -> TestingCycleModel:
    """Train a survival model using most recent completed cycles before cutoff_year."""
    extractor = FeatureExtractor(current_year=cutoff_year)
    
    X_list = []
    durations = []
    events = []
    
    # Limit to a subset to speed up training if needed, but 8000 is small.
    for entry in entries:
        wd = extractor.extract_word_data(entry)
        # Get tested years strictly before cutoff
        tested_years = sorted([y for y in wd.years_tested if y < cutoff_year])
        
        if len(tested_years) >= 2:
            # Use the most recent completed interval
            start_year = tested_years[-2]
            end_year = tested_years[-1]
            duration = end_year - start_year
            
            # Extract features at the START of the interval
            # Note: We must restrict data to be before or at start_year
            # But feature extractor uses `target_year` to filter data `< target_year`? 
            # Or `<= target_year`? 
            # `is_valid_for_prediction` returns True if `exam_year < target_year`.
            # So if we pass `target_year=start_year`, it uses data `< start_year`. 
            # Correct for prediction state at `start_year`.
            
            # However, we want to include the 'event' at start_year implies it was tested?
            # No, 'start_year' is when the previous test happened.
            # We want to predict how long until 'end_year'.
            # State at 'start_year' includes the fact that it was tested at 'start_year'.
            # So we should use features available just after start_year exam?
            # Or simplify: usage state at `start_year + 1`.
            # Let's use `target_year = start_year`. It uses history UP TO start_year.
            # `recency` will be 0 (since it was tested at start_year).
            
            feat = extractor.extract_feature_vector(wd, target_year=start_year)
            
            # We must output raw features (no external features yet to avoid recursion)
            if feat is not None:
                # We need to filter features to match current FEATURE_NAMES?
                # extract_feature_vector returns vector matching FEATURE_NAMES.
                # But FEATURE_NAMES now includes 'survival_hazard'.
                # We explicitly pass external_features=None, so it fills 0.0.
                # Valid for recursive training? 
                # Yes, Base Model uses 0.0 hazard.
                X_list.append(feat)
                durations.append(duration)
                events.append(1) # Event occurred
                
    model = TestingCycleModel()
    if X_list:
        try:
            model.fit(np.array(X_list), np.array(durations), np.array(events))
        except Exception as e:
            print(f"Warning: Survival model training failed: {e}")
            
    return model


def prepare_ranking_dataset(
    entries: list[dict],
    distractor_groups: list[dict],
    essay_topics: list[dict],
    target_years: list[int],
    target_mode: str = "tested",
    gsat_only: bool = False,
    feature_names: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Prepare dataset for Learning-to-Rank (LambdaRank).
    
    Includes Survival Analysis and Synonym Testing frequency features.
    """
    if feature_names is None:
        feature_names = get_feature_names()
        
    # 1. Train Survival Model ONCE using data prior to the EARLIEST target year.
    min_year = min(target_years) if target_years else 115
    console.print(f"Training Survival Model using data prior to {min_year}...")
    survival_model = _train_survival_model(entries, min_year)
    
    # 2. Pre-compute tested history for synonyms
    lemma_tested_history = {}
    future_ex = FeatureExtractor(current_year=120)
    for entry in entries:
        wd = future_ex.extract_word_data(entry)
        lemma_tested_history[wd.lemma.lower()] = wd.years_tested

    X_list = []
    y_list = []
    groups_list = []

    for year in target_years:
        extractor = FeatureExtractor(current_year=year)

        year_X = []
        year_y = []

        processed = 0
        skipped = 0
        for entry in entries:
            word_data = extractor.extract_word_data(entry)
            
            # --- External Features Calculation ---
            ext_feats = {}
            
            # A. Survival Hazard
            # Extract features first (with 0.0 placeholders for now)
            # Note: extract_feature_vector signature changed to accept external_features
            raw_features = extractor.extract_feature_vector(
                word_data, target_year=year, external_features=None
            )
            
            if raw_features is None:
                skipped += 1
                continue
            
            if survival_model and survival_model.model:
                try:
                    # Survival model predict_hazard expects numpy array
                    hazards = survival_model.predict_hazard(np.array([raw_features]))
                    ext_feats["survival_hazard"] = float(hazards[0])
                except Exception:
                    ext_feats["survival_hazard"] = 0.5
            else:
                ext_feats["survival_hazard"] = 0.5

            # B. Synonym Tested Freq
            syn_tested_count = 0
            synonyms = entry.get("synonyms", [])
            for syn in synonyms:
                syn_lemma = syn.lower()
                if syn_lemma in lemma_tested_history:
                    hist = lemma_tested_history[syn_lemma]
                    # Recently tested synonym (last 5 years)
                    count_in_window = sum(1 for y in hist if year - 5 <= y < year)
                    syn_tested_count += count_in_window
            
            ext_feats["synonym_tested_freq"] = float(syn_tested_count)
            
            # C. Inject into features vector
            # Order in FEATURE_NAMES (from features.py):
            # ... phase 9 additions ...
            # "survival_hazard", "synonym_tested_freq", "level_difficulty_match"
            # Indices: -3, -2, -1
            
            raw_features[-3] = ext_feats["survival_hazard"]
            raw_features[-2] = ext_feats["synonym_tested_freq"]
            
            features = raw_features
            
            processed += 1
            label = extractor.get_target_label(word_data, year, target_mode)
            
            year_X.append(features)
            year_y.append(label)
            
        if year_X:
            console.print(f"  Year {year}: Processed {processed}, Skipped {skipped}, Positives: {sum(year_y)}")
            X_list.append(np.array(year_X))
            y_list.append(np.array(year_y))
            groups_list.append(len(year_X))
            
    if not X_list:
        console.print("[red]No training data collected![/]")
        return np.array([[]]), np.array([]), np.array([])
        
    X = np.vstack(X_list)
    y = np.concatenate(y_list)
    groups = np.array(groups_list)
    
    console.print(f"[bold]Total Training Dataset:[/] X={X.shape}, Positives={int(sum(y))}")
    return X, y, groups





def train_ranker_model(
    entries: list[dict],
    distractor_groups: list[dict],
    essay_topics: list[dict],
    target_year: int,
    lookback_years: int = 20,
    target_mode: str = "tested",
    gsat_only: bool = False,
) -> tuple[VocabRanker, dict]:
    """
    Train the final ranking model.

    Uses data from [target_year - 5... target_year - 1] to train
    a model that predicts target_year.
    Wait, if we want to predict target_year (future), we should train on
    all available past data.
    
    Strategy:
    - Train on years: [target_year-lookback ... target_year-1]
    - Predict for: target_year
    """
    training_years = list(range(max(105, target_year - 10), target_year))
    console.print(f"Training data years: {training_years}")
    
    X, y, groups = prepare_ranking_dataset(
        entries, [], [],
        training_years, target_mode, gsat_only
    )
    
    feature_names = get_feature_names()
    console.print(f"Training samples: {len(X)}, Groups: {len(groups)}")
    
    ranker = VocabRanker(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
    )
    
    metrics = ranker.train(X, y, groups, feature_names=feature_names)
    
    # Get feature importance
    importance = ranker.get_feature_importance("gain")
    top_features = sorted(
        [{"name": k, "importance": v} for k, v in importance.items()],
        key=lambda x: x["importance"],
        reverse=True,
    )[:20]
    
    training_info = {
        "target_year": target_year,
        "target_mode": target_mode,
        "training_years": training_years,
        "metrics": {
            "ndcg@50": metrics.ndcg_at_50,
            "ndcg@100": metrics.ndcg_at_100,
            "cv_ndcg_mean": metrics.cv_ndcg_mean,
        },
        "top_features": top_features,
    }
    
    return ranker, training_info


def temporal_validation(
    entries: list[dict],
    distractor_groups: list[dict],
    essay_topics: list[dict],
    test_years: list[int],
    target_mode: str = "tested",
    gsat_only: bool = False,
) -> dict:
    results = {
        "year": [],
        "ndcg@100": [],
        "cv_ndcg": [],
        "precision@100": [],
        "recall@100": [],
        "samples": [],
        "positive": [],
        "positive_rate": [],
    }

    feature_names = get_feature_names()

    for target_year in test_years:
        console.print(f"  [dim]Validating year {target_year}...[/]")

        # 1. Prepare Training Data (Past years)
        training_years = list(range(max(105, target_year - 5), target_year))
        X_train, y_train, groups_train = prepare_ranking_dataset(
            entries, [], [], 
            training_years, target_mode, gsat_only, feature_names
        )

        # 2. Prepare Validation Data (Target year)
        X_val, y_val, groups_val = prepare_ranking_dataset(
            entries, [], [], 
            [target_year], target_mode, gsat_only, feature_names
        )

        if len(X_val) < 100 or sum(y_val) < 5:
            console.print(f"    [yellow]Skipping {target_year}: insufficient samples[/]")
            continue

        # 3. Train Ranker
        ranker = VocabRanker(n_estimators=100)
        metrics = ranker.train(X_train, y_train, groups_train, feature_names=feature_names)

        # 4. Evaluate on Validation Set
        y_pred = ranker.predict(X_val)
        val_metrics = compute_metrics(y_val, y_pred, k_list=[50, 100, 200])

        results["year"].append(target_year)
        results["ndcg@100"].append(val_metrics.ndcg_100)
        results["cv_ndcg"].append(metrics.cv_ndcg_mean)
        results["precision@100"].append(val_metrics.precision_100)
        results["recall@100"].append(val_metrics.recall_100)
        results["samples"].append(len(X_val))
        results["positive"].append(sum(y_val))
        results["positive_rate"].append(sum(y_val) / len(y_val))

    return results


def compare_target_modes(
    entries: list[dict],
    distractor_groups: list[dict],
    essay_topics: list[dict],
    test_years: list[int],
    gsat_only: bool = False,
) -> dict[str, dict]:
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
            avg_ndcg = np.mean(results["ndcg@100"])
            avg_cv_ndcg = np.mean(results["cv_ndcg"])
            all_results[mode] = {
                "avg_ndcg@100": avg_ndcg,
                "avg_cv_ndcg": avg_cv_ndcg,
                "yearly_results": results,
            }
            console.print(f"  NDCG@100: {avg_ndcg:.4f}, CV NDCG: {avg_cv_ndcg:.4f}")

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Train GSAT vocabulary importance prediction model (LambdaRank)"
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/output/vocab.json"),
        help="Path to vocab.json (with WSD-assigned senses)",
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
        default=None,
        help="Target year for prediction (default: max_year in data)",
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
    # Compare modes might take very long with ranking, maybe disable by default or warn
    parser.add_argument(
        "--compare-modes",
        action="store_true",
        help="Compare all target modes (slow)",
    )
    parser.add_argument(
        "--gsat-only",
        action="store_true",
        help="Filter out AST data, train on GSAT only",
    )
    args = parser.parse_args()

    if not args.data.exists():
        console.print(f"[red]Error: Data file not found: {args.data}[/]")
        sys.exit(1)

    # Load vocab.json (with WSD-assigned senses)
    data = load_vocab_data(args.data)

    analysis = analyze_data(data)
    max_year = analysis["year_range"][1]

    # Dynamic target year: Use provided year or default to max_year in data
    target_year = args.target_year or max_year

    table = Table(title="Data Summary", show_header=False)
    table.add_column(style="dim")
    table.add_column(style="bold")
    table.add_row("Total entries", str(analysis["total_entries"]))
    table.add_row("Year range", f"{analysis['year_range'][0]} - {analysis['year_range'][1]}")
    table.add_row("Curriculum cutoff", f"Year {CURRICULUM_CUTOFF_YEAR}")
    table.add_row("Trial years", ", ".join(str(y) for y in sorted(TRIAL_YEARS)))
    table.add_row("Target Year", str(target_year))
    console.print(table)
    console.print()

    if args.gsat_only:
        console.print("[yellow]GSAT-only mode enabled: filtering out AST data[/]")
        console.print()

    entries = data.get("entries", [])

    # Validation years: Validate on the latest 4 years prior to target (starting from 111)
    test_years = [y for y in range(target_year - 4, target_year) if y >= 111]

    if args.compare_modes:
        console.print("[cyan]Comparing all target modes...[/]")
        compare_target_modes(
            entries, [], [], test_years, gsat_only=args.gsat_only
        )

    if not args.skip_validation:
        console.print(f"[cyan]Running temporal validation (mode: {args.target_mode})...[/]")

        val_results = temporal_validation(
            entries,
            [],  # distractor_groups removed
            [],  # essay_topics removed
            test_years,
            target_mode=args.target_mode,
            gsat_only=args.gsat_only,
        )

        if val_results["year"]:
            val_table = Table(title=f"Temporal Validation (mode: {args.target_mode})")
            val_table.add_column("Year", style="cyan")
            val_table.add_column("NDCG@100", style="green")
            val_table.add_column("CV NDCG", style="dim")
            val_table.add_column("P@100", style="yellow")
            val_table.add_column("R@100", style="yellow")
            val_table.add_column("Samples", style="dim")

            for i, year in enumerate(val_results["year"]):
                val_table.add_row(
                    str(year),
                    f"{val_results['ndcg@100'][i]:.4f}",
                    f"{val_results['cv_ndcg'][i]:.4f}",
                    f"{val_results['precision@100'][i]:.4f}",
                    f"{val_results['recall@100'][i]:.4f}",
                    str(val_results["samples"][i]),
                )

            avg_ndcg = np.mean(val_results["ndcg@100"])
            val_table.add_row(
                "Average", f"[bold]{avg_ndcg:.4f}[/]", "", "", "", ""
            )
            console.print(val_table)
            console.print()

    # Train Final Model
    console.print(
        f"[cyan]Training final model (target: year {args.target_year})...[/]"
    )

    ranker, training_info = train_ranker_model(
        entries=entries,
        distractor_groups=[],
        essay_topics=[],
        target_year=args.target_year,
        lookback_years=20,
        target_mode=args.target_mode,
        gsat_only=args.gsat_only,
    )

    # Save Model
    ranker.save(args.output)
    console.print(f"[green]✓[/] Model saved to {args.output}")

    # Save Info
    output_info_path = args.output_info or args.output.with_suffix(".json").with_name(
        "model_info.json"
    )
    training_info["generated_at"] = datetime.now(UTC).isoformat()
    training_info["model_path"] = str(args.output)
    training_info["feature_count"] = len(get_feature_names())

    with open(output_info_path, "w", encoding="utf-8") as f:
        json.dump(training_info, f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/] Training info saved to {output_info_path}")

    # --- SHOW PREDICTIONS FOR TARGET YEAR ---
    # We want to see the 115 distribution
    console.print(f"\n[bold cyan]Top Predictions for Year {target_year}:[/]")
    
    extractor = FeatureExtractor(current_year=target_year)
    all_scores = []
    
    # Pre-compute survival hazard if possible
    surv_model = _train_survival_model(entries, target_year)
    
    # Pre-build synonym testing history
    lemma_history = {}
    for entry in entries:
        wd = extractor.extract_word_data(entry)
        lemma_history[wd.lemma.lower()] = wd.years_tested

    for entry in entries:
        wd = extractor.extract_word_data(entry)
        feats = extractor.extract_feature_vector(wd, target_year=target_year)
        if feats:
            # External features (simplified for quick report)
            ext = {"survival_hazard": 0.5, "synonym_tested_freq": 0.0}
            if surv_model and surv_model.model:
                try:
                    h = surv_model.predict_hazard(np.array([feats]))
                    ext["survival_hazard"] = float(h[0])
                except: pass
            
            # Simple synonym freq from history
            syn_cnt = 0
            for s in entry.get("synonyms", []):
                sl = s.lower()
                if sl in lemma_history:
                    syn_cnt += sum(1 for y in lemma_history[sl] if target_year - 5 <= y < target_year)
            ext["synonym_tested_freq"] = float(syn_cnt)
            
            feats[-3] = ext["survival_hazard"]
            feats[-2] = ext["synonym_tested_freq"]
            
            score = ranker.predict(np.array([feats]))[0]
            all_scores.append((wd.lemma, wd.level, score))
    
    all_scores.sort(key=lambda x: x[2], reverse=True)
    
    pred_table = Table(title=f"Top 50 Predictions for {target_year}")
    pred_table.add_column("Rank", justify="right")
    pred_table.add_column("Lemma", style="magenta")
    pred_table.add_column("Level", justify="center")
    pred_table.add_column("ML Score", style="green")
    
    for i, (lemma, lvl, score) in enumerate(all_scores[:50]):
        pred_table.add_row(str(i+1), lemma, str(lvl), f"{score:.4f}")
    
    console.print(pred_table)




if __name__ == "__main__":
    main()


def run_ml_pipeline(
    cleaned_data: CleanedVocabData,
    final_entries: list[VocabEntry],
    target_year: int = 115,
    use_modern: bool = False,
) -> list[VocabEntry]:
    """
    Run the full ML pipeline: Train -> Predict -> Inject Scores.
    Called by CLI pipeline (Stage 6 -> 7).

    Args:
        cleaned_data: Cleaned vocabulary data
        final_entries: Final entry objects to update
        target_year: Target year for prediction
        use_modern: If True, use the modern ensemble pipeline
    """
    if use_modern:
        return _run_modern_pipeline(cleaned_data, final_entries, target_year)

    return _run_legacy_pipeline(cleaned_data, final_entries, target_year)


def _run_modern_pipeline(cleaned_data, final_entries: list, target_year: int) -> list:
    """Run the modern ML pipeline with all advanced features."""
    from .pipeline import ModernVocabPipeline, PipelineConfig

    console.print(f"\n[bold cyan]=== Stage 6.5: Modern ML Pipeline (Target: {target_year}) ===[/]")

    config = PipelineConfig(
        target_year=target_year,
        target_mode="tested",
        use_embeddings=True,
        use_graph=True,
        use_sense_survival=True,
        use_value_estimation=True,
    )

    pipeline = ModernVocabPipeline(config)

    # Convert cleaned data to dicts
    cleaned_dicts = [w.model_dump() for w in cleaned_data.words]
    cleaned_dicts.extend([p.model_dump() for p in cleaned_data.phrases])

    # Enrich with senses from final entries
    final_map = {e.lemma: e for e in final_entries if hasattr(e, "lemma")}
    for d in cleaned_dicts:
        lemma = d.get("lemma") or d.get("word")
        if lemma and lemma in final_map:
            f_entry = final_map[lemma]
            if hasattr(f_entry, "senses") and f_entry.senses:
                d["senses"] = [s.model_dump() for s in f_entry.senses]
            if hasattr(f_entry, "synonyms") and f_entry.synonyms:
                d["synonyms"] = f_entry.synonyms
            if hasattr(f_entry, "antonyms") and f_entry.antonyms:
                d["antonyms"] = f_entry.antonyms

    # Train
    pipeline.train(cleaned_dicts, validate=False)

    # Predict
    predictions = pipeline.predict(cleaned_dicts)

    # Build score map
    score_map = {p["lemma"]: p["score"] for p in predictions}

    # Inject scores into final entries
    updated_count = 0
    for entry in final_entries:
        if hasattr(entry, "lemma") and entry.lemma in score_map:
            if entry.frequency:
                entry.frequency.ml_score = score_map[entry.lemma]
                updated_count += 1

    # Print top predictions
    from rich.table import Table
    top_n = predictions[:50]
    table = Table(title=f"Top 50 Predicted Words for Year {target_year} (Modern Pipeline)")
    table.add_column("Rank", justify="right", style="cyan")
    table.add_column("Lemma", style="magenta")
    table.add_column("Level", justify="center")
    table.add_column("Score", justify="right", style="green")

    for i, pred in enumerate(top_n):
        table.add_row(str(i + 1), pred["lemma"], str(pred["level"] or "?"), f"{pred['score']:.4f}")

    console.print(table)
    console.print(f"[green]✓[/] ML Scores assigned to {updated_count} entries.")

    return final_entries


def _run_legacy_pipeline(
    cleaned_data: CleanedVocabData,
    final_entries: list[VocabEntry],
    target_year: int,
) -> list[VocabEntry]:
    """
    Run the full ML pipeline: Train -> Predict -> Inject Scores.
    Called by CLI pipeline (Stage 6 -> 7).
    """
    console.print(f"\n[bold cyan]=== Stage 6.5: ML Training & Scoring (Target: {target_year}) ===[/]")

    # 1. Prepare Data (Convert to dicts for compatibility)
    cleaned_dicts = [w.model_dump() for w in cleaned_data.words]
    cleaned_dicts.extend([p.model_dump() for p in cleaned_data.phrases])
    
    # 2. Train Survival Model
    surv_model = _train_survival_model(cleaned_dicts, target_year)
    
    # History for synonym features
    extractor = FeatureExtractor(current_year=200)
    lemma_history = {}
    for d in cleaned_dicts:
        wd = extractor.extract_word_data(d)
        lemma_history[wd.lemma.lower()] = wd.years_tested

    # 2b. Enrich Cleaned Data with WSD History (for Training)
    # We inject 'senses' from final_entries into cleaned_dicts so the ranker can see WSD features.
    final_map: dict[str, WordEntry | PhraseEntry] = {
        e.lemma: e for e in final_entries if isinstance(e, (WordEntry, PhraseEntry))
    }
    enriched_count = 0
    for d in cleaned_dicts:
        lemma = d.get("lemma") or d.get("word")
        if lemma and lemma in final_map:
            f_entry = final_map[lemma]
            if f_entry.senses:
                d["senses"] = [s.model_dump() for s in f_entry.senses]
                enriched_count += 1

    console.print(f"[cyan]Enriched {enriched_count} training entries with WSD history.[/]")


    # 3. Train Ranker Model
    # We train on valid data (dictionaries)
    ranker, _ = train_ranker_model(
        entries=cleaned_dicts,
        distractor_groups=[], # Not available in current CLI flow
        essay_topics=[],      # Not available
        target_year=target_year,
        lookback_years=20,
        target_mode="tested",
        gsat_only=False
    )
    
    # 4. Predict & Inject
    pred_extractor = FeatureExtractor(current_year=target_year)
    cleaned_map = {d["lemma"]: d for d in cleaned_dicts}

    updated_count = 0
    for entry in final_entries:
        # Only process WordEntry and PhraseEntry (PatternEntry doesn't have lemma in same sense)
        if not isinstance(entry, (WordEntry, PhraseEntry)):
            continue

        # Strategy: Use Final Entry as Primary Source (High Quality)
        # But we need raw historical context (exam roles, prompt types) from Cleaned Data
        c_entry = cleaned_map.get(entry.lemma)

        # 1. Start with Cleaned Data for RAW History (Contexts)
        if c_entry:
            wd = pred_extractor.extract_word_data(c_entry)
        else:
            # Fallback if no history (e.g. new word in refined list?)
            wd = pred_extractor.extract_word_data(entry)

        # 2. OVERWRITE/ENRICH with High Quality Data from Final Entry
        # WSD Senses (The refined meaning distribution)
        wd.wsd_year_sense_map.clear()
        for s_idx, sense in enumerate(entry.senses):
            for ex in sense.examples:
                if ex.source and ex.source.year > 0:
                    wd.wsd_year_sense_map[ex.source.year][s_idx] += 1

        # 3. Use Refined Properties (Level, Official Status) from Final Entry
        # Only WordEntry has level/in_official_list; PhraseEntry doesn't
        if isinstance(entry, WordEntry):
            if entry.level:
                wd.level = entry.level
            if entry.in_official_list is not None:
                wd.in_official = entry.in_official_list
        
        feats = pred_extractor.extract_feature_vector(wd, target_year=target_year, external_features=None)
        
        if feats:
            # Calc External Features
            ext = {}
            if surv_model and surv_model.model:
                try:
                    h = surv_model.predict_hazard(np.array([feats]))
                    ext["survival_hazard"] = float(h[0])
                except:
                    ext["survival_hazard"] = 0.5
            else:
                ext["survival_hazard"] = 0.5
                
            syn_cnt = 0
            # Use Final Entry Synonyms (Refined Relations)
            for s in (entry.synonyms or []):
                 sl = s.lower()
                 if sl in lemma_history:
                     cnt = sum(1 for y in lemma_history[sl] if target_year - 5 <= y < target_year)
                     syn_cnt += cnt
            ext["synonym_tested_freq"] = float(syn_cnt)
            
            feats[-3] = ext["survival_hazard"]
            feats[-2] = ext["synonym_tested_freq"]
            
            score = ranker.predict(np.array([feats]))[0]
            
            # Inject score
            if entry.frequency:
                 entry.frequency.ml_score = float(score)
            updated_count += 1
            
    # 5. Report Top Predictions
    scorable_entries = [e for e in final_entries if isinstance(e, (WordEntry, PhraseEntry))]
    top_n = sorted(
        scorable_entries, key=lambda x: x.frequency.ml_score if x.frequency else 0, reverse=True
    )[:50]

    table = Table(title=f"Top 50 Predicted Words for Year {target_year}")
    table.add_column("Rank", justify="right", style="cyan")
    table.add_column("Lemma", style="magenta")
    table.add_column("Level", justify="center")
    table.add_column("Score", justify="right", style="green")

    for i, entry in enumerate(top_n):
        level = entry.level if isinstance(entry, WordEntry) else 0
        score = entry.frequency.ml_score if entry.frequency else 0.0
        table.add_row(str(i + 1), entry.lemma, str(level or 0), f"{score:.4f}")
    
    console.print(table)
    
    console.print(f"[green]✓[/] ML Scores assigned to {updated_count} entries.")
    return final_entries
