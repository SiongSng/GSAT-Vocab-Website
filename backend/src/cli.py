import asyncio
import gzip
import json
import logging
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from .models import load_official_wordlist
from .stages import (
    build_database,
    clean_and_classify,
    compute_relations,
    generate_all_entries,
    process_all_markdowns,
    process_all_pdfs,
    write_output,
)

app = typer.Typer(help="GSAT Vocabulary Pipeline")
console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, show_time=False, show_path=False)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)


def get_data_dir() -> Path:
    return Path(__file__).parent.parent / "data"


def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        expand=False,
        refresh_per_second=4,
    )


@app.command()
def run(
    pdf_dir: Path = typer.Option(None, help="PDF directory"),
    wordlist: Path = typer.Option(None, help="Official wordlist JSON"),
    output: Path = typer.Option(None, help="Output vocab.json path"),
    skip_llm: bool = typer.Option(False, help="Skip LLM stages (use cached)"),
    use_legacy_weights: bool = typer.Option(False, help="Use legacy weights instead of ML"),
    debug_first_batch: bool = typer.Option(False, help="Only generate first batch for debugging"),
):
    data_dir = get_data_dir()

    if pdf_dir is None:
        pdf_dir = data_dir / "pdf"
    if wordlist is None:
        wordlist = data_dir / "official_wordlist.json"
    if output is None:
        output = data_dir / "output" / "vocab.json"

    asyncio.run(
        _run_pipeline(pdf_dir, wordlist, output, skip_llm, use_legacy_weights, debug_first_batch)
    )


async def _run_pipeline(
    pdf_dir: Path,
    wordlist_path: Path,
    output_path: Path,
    skip_llm: bool,
    use_legacy_weights: bool,
    debug_first_batch: bool = False,
):
    intermediate_dir = pdf_dir.parent / "intermediate"
    intermediate_dir.mkdir(exist_ok=True)

    stats = {
        "pdfs": 0,
        "exams": 0,
        "cleaned": 0,
        "generated": 0,
        "errors": 0,
        "ml_cv_auc": 0.0,
        "scoring_mode": "legacy" if use_legacy_weights else "ml",
    }

    with create_progress() as progress:
        stage0 = progress.add_task("[cyan]Stage 0: PDF → Markdown", total=None)
        md_dir = pdf_dir.parent / "markdown"

        def on_stage0_progress(completed, total):
            progress.update(stage0, completed=completed, total=total)

        markdown_files = await process_all_pdfs(
            pdf_dir, md_dir, progress_callback=on_stage0_progress
        )
        stats["pdfs"] = len(markdown_files)
        if not markdown_files:
            progress.update(stage0, completed=1, total=1)

        stage1 = progress.add_task(
            "[cyan]Stage 1: Structurize exams", total=len(markdown_files) or 1
        )
        exams_dir = intermediate_dir / "exams"

        def on_stage1_progress(completed, total):
            progress.update(stage1, completed=completed, total=total)

        exams = await process_all_markdowns(
            markdown_files, cache_dir=exams_dir, progress_callback=on_stage1_progress
        )
        stats["exams"] = len(exams)
        progress.update(stage1, completed=len(markdown_files) or 1)

        stage2 = progress.add_task("[cyan]Stage 2: Clean & classify", total=1)
        official_wordlist = load_official_wordlist(wordlist_path)
        cleaned_cache = intermediate_dir / "cleaned.json"
        if exams:
            cleaned = clean_and_classify(exams, official_wordlist)
            stats["cleaned"] = len(cleaned.entries)
        elif cleaned_cache.exists():
            from .models import CleanedVocabData

            with open(cleaned_cache, encoding="utf-8") as f:
                cleaned = CleanedVocabData.model_validate(json.load(f))
            stats["cleaned"] = len(cleaned.entries)
        else:
            cleaned = None
        progress.update(stage2, completed=1)

        model_path = output_path.parent / "importance_model.pkl"
        model_info_path = output_path.parent / "model_info.json"

        if not use_legacy_weights and cleaned and cleaned.entries:
            stage_ml = progress.add_task("[cyan]Stage 2.5: Train ML model", total=2)

            from .ml.model import ImportanceScorer, train_model

            years = [f[1] for f in markdown_files if f[1] > 0]
            target_year = max(years) if years else 114

            entries_dict = [e.model_dump(mode="json", exclude_none=True) for e in cleaned.entries]
            distractor_dict = [
                dg.model_dump(mode="json", exclude_none=True) for dg in cleaned.distractor_groups
            ]
            essay_dict = [
                et.model_dump(mode="json", exclude_none=True) for et in cleaned.essay_topics
            ]

            model, training_info = train_model(
                entries=entries_dict,
                distractor_groups=distractor_dict,
                essay_topics=essay_dict,
                target_year=target_year,
                lookback_years=20,
                target_mode="tested",
                gsat_only=True,
            )

            model.save(model_path)
            stats["ml_cv_auc"] = training_info["metrics"]["cv_auc_mean"]

            progress.update(stage_ml, completed=1, description="[cyan]Stage 2.5: Computing scores")

            scorer = ImportanceScorer(
                model=model,
                distractor_groups=distractor_dict,
                essay_topics=essay_dict,
                current_year=target_year,
            )

            ml_scores = scorer.score_entries(entries_dict)

            for entry in cleaned.entries:
                score = ml_scores.get(entry.lemma)
                if score is not None:
                    entry.frequency.ml_score = round(score, 4)

            cleaned.entries.sort(
                key=lambda e: (e.frequency.ml_score or 0, e.frequency.weighted_score),
                reverse=True,
            )

            progress.update(stage_ml, completed=2)

            from datetime import UTC, datetime

            training_info["generated_at"] = datetime.now(UTC).isoformat()
            training_info["model_path"] = str(model_path)
            training_info["scored_entries"] = len(ml_scores)

            with open(model_info_path, "w", encoding="utf-8") as f:
                json.dump(training_info, f, ensure_ascii=False, indent=2)
        else:
            if cleaned:
                cleaned.entries.sort(key=lambda e: e.frequency.weighted_score, reverse=True)

        if cleaned:
            with open(cleaned_cache, "w", encoding="utf-8") as f:
                json.dump(
                    cleaned.model_dump(mode="json", exclude_none=True),
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

        stage3 = progress.add_task("[cyan]Stage 3: Generate entries", total=100)
        if not skip_llm and cleaned and cleaned.entries:

            def on_progress(
                completed_batches,
                total_batches,
                tier,
                generated_count,
                processed_count,
                total_items,
            ):
                progress.update(
                    stage3,
                    completed=processed_count,
                    total=total_items,
                    description=f"[cyan]Stage 3: {tier} ({generated_count} generated)",
                )

            entries = await generate_all_entries(
                cleaned,
                debug_first_batch=debug_first_batch,
                progress_callback=on_progress,
            )
            stats["generated"] = len(entries)
        else:
            entries = []
        progress.update(stage3, completed=100)

        stage4 = progress.add_task("[cyan]Stage 4: Compute relations", total=100)
        if entries and not debug_first_batch:

            def on_relations_progress(completed, total, count):
                progress.update(
                    stage4,
                    completed=completed,
                    total=total,
                    description=f"[cyan]Stage 4: WordNet ({count} words)",
                )

            entries = compute_relations(entries, progress_callback=on_relations_progress)
        progress.update(stage4, completed=100)

        stage5 = progress.add_task("[cyan]Stage 5: Write output", total=1)
        years = [f[1] for f in markdown_files if f[1] > 0]
        min_year = min(years) if years else 0
        max_year = max(years) if years else 0

        distractor_groups = cleaned.distractor_groups if cleaned else []
        database = build_database(entries, distractor_groups, min_year, max_year)
        errors_path = output_path.parent / "errors.json"
        count, errors = write_output(database, output_path, errors_path)
        stats["errors"] = len(errors)
        progress.update(stage5, completed=1)

    console.print()
    table = Table(title="Pipeline Complete", show_header=False, box=None)
    table.add_column(style="dim")
    table.add_column(style="bold")
    table.add_row("Output", str(output_path))
    table.add_row("PDFs processed", str(stats["pdfs"]))
    table.add_row("Exams structured", str(stats["exams"]))
    table.add_row("Entries cleaned", str(stats["cleaned"]))
    table.add_row("Entries generated", str(stats["generated"]))
    table.add_row("Scoring mode", stats["scoring_mode"])
    if stats["ml_cv_auc"] > 0:
        table.add_row("ML model CV AUC", f"{stats['ml_cv_auc']:.4f}")
    if stats["errors"]:
        table.add_row("[yellow]Warnings[/]", f"[yellow]{stats['errors']}[/]")
    console.print(Panel(table, border_style="green"))


@app.command()
def train_ml(
    data: Path = typer.Option(None, help="Path to cleaned.json"),
    output: Path = typer.Option(None, help="Output model path"),
    target_year: int = typer.Option(114, help="Target year for prediction"),
    target_mode: str = typer.Option(
        "tested", help="Target mode: appeared/tested/active_tested/answer_only"
    ),
    gsat_only: bool = typer.Option(True, help="Train on GSAT data only"),
    compare_modes: bool = typer.Option(False, help="Compare all target modes"),
):
    """Train ML importance prediction model separately."""
    import subprocess
    import sys

    data_dir = get_data_dir()

    if data is None:
        data = data_dir / "intermediate" / "cleaned.json"
    if output is None:
        output = data_dir / "output" / "importance_model.pkl"

    cmd = [
        sys.executable,
        "-m",
        "src.ml.train",
        "--data",
        str(data),
        "--output",
        str(output),
        "--target-year",
        str(target_year),
        "--target-mode",
        target_mode,
    ]

    if gsat_only:
        cmd.append("--gsat-only")
    if compare_modes:
        cmd.append("--compare-modes")

    subprocess.run(cmd, cwd=data_dir.parent)


@app.command()
def scrape(
    output_dir: Path = typer.Option(None, help="Output directory for PDFs"),
):
    from .utils.scraper import scrape_ceec_papers

    if output_dir is None:
        output_dir = get_data_dir() / "pdf"

    console.print(f"Scraping CEEC papers to {output_dir}...")
    count = scrape_ceec_papers(output_dir)
    console.print(f"[green]✓[/] Downloaded {count} papers")


@app.command()
def export(
    input_path: Path = typer.Option(None, help="Input vocab.json path"),
    output_dir: Path = typer.Option(None, help="Output directory in frontend"),
):
    """Compress vocab.json to gzip and copy to frontend for lazy loading."""
    data_dir = get_data_dir()

    if input_path is None:
        input_path = data_dir / "output" / "vocab.json"
    if output_dir is None:
        output_dir = data_dir.parent.parent / "frontend" / "public" / "data"

    if not input_path.exists():
        console.print(f"[red]✗[/] Input file not found: {input_path}")
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "vocab.json.gz"

    with (
        open(input_path, "rb") as f_in,
        gzip.open(output_path, "wb", compresslevel=9) as f_out,
    ):
        shutil.copyfileobj(f_in, f_out)

    original_size = input_path.stat().st_size
    compressed_size = output_path.stat().st_size
    ratio = (1 - compressed_size / original_size) * 100

    table = Table(title="Export Complete", show_header=False, box=None)
    table.add_column(style="dim")
    table.add_column(style="bold")
    table.add_row("Source", str(input_path))
    table.add_row("Output", str(output_path))
    table.add_row("Original size", f"{original_size / 1024 / 1024:.2f} MB")
    table.add_row("Compressed size", f"{compressed_size / 1024 / 1024:.2f} MB")
    table.add_row("Compression ratio", f"{ratio:.1f}%")
    console.print(Panel(table, border_style="green"))


if __name__ == "__main__":
    app()
