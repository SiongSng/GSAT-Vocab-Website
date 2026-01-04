import asyncio
import gzip
import hashlib
import json
import logging
import shutil
from datetime import datetime, timezone
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

from .models import CleanedVocabData, ExamType, load_official_wordlist
from .registry import Registry
from .stages import (
    assign_all_senses,
    build_database,
    clean_and_classify,
    compute_relations,
    generate_all_entries,
    perform_wsd,
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
    skip_ml: bool = typer.Option(False, help="Skip ML training"),
    legacy_ml: bool = typer.Option(False, help="Use legacy ML pipeline instead of modern"),
    exam_only: bool = typer.Option(False, help="Only include words that appear in exams"),
):
    data_dir = get_data_dir()

    if pdf_dir is None:
        pdf_dir = data_dir / "pdf"
    if wordlist is None:
        wordlist = data_dir / "official_wordlist.json"
    if output is None:
        output = data_dir / "output" / "vocab.json"

    try:
        asyncio.run(
            _run_pipeline(
                pdf_dir,
                wordlist,
                output,
                skip_ml,
                legacy_ml,
                exam_only,
            )
        )
    except Exception:
        import traceback

        console.print("\n[red]Error occurred:[/]\n")
        traceback.print_exc()
        raise typer.Exit(1)


async def _run_pipeline(
    pdf_dir: Path,
    wordlist_path: Path,
    output_path: Path,
    skip_ml: bool,
    legacy_ml: bool,
    exam_only: bool = False,
):
    intermediate_dir = pdf_dir.parent / "intermediate"
    intermediate_dir.mkdir(exist_ok=True)

    stats = {
        "pdfs": 0,
        "exams": 0,
        "extracted": 0,
        "generated": 0,
    }

    with create_progress() as progress:
        stage0 = progress.add_task("[cyan]Stage 0: PDF → Markdown", total=None)
        md_dir = pdf_dir.parent / "markdown"

        def on_stage0_progress(completed: int, total: int) -> None:
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

        def on_stage1_progress(completed: int, total: int) -> None:
            progress.update(stage1, completed=completed, total=total)

        exams = await process_all_markdowns(
            markdown_files, cache_dir=exams_dir, progress_callback=on_stage1_progress
        )
        stats["exams"] = len(exams)
        progress.update(stage1, completed=len(markdown_files) or 1)

        stage2 = progress.add_task("[cyan]Stage 2: Extract vocabulary", total=100)
        official_wordlist = load_official_wordlist(wordlist_path)
        extracted_cache = intermediate_dir / "extracted.json"

        cleaned: CleanedVocabData | None = None
        if exams:

            def on_stage2_progress(completed: int, total: int, step: str) -> None:
                progress.update(
                    stage2,
                    completed=completed,
                    total=total,
                    description=f"[cyan]Stage 2: Extract vocabulary ({step})",
                )

            cleaned = clean_and_classify(
                exams, official_wordlist, exam_only=exam_only, progress_callback=on_stage2_progress
            )
        elif extracted_cache.exists():
            with open(extracted_cache, encoding="utf-8") as f:
                cleaned = CleanedVocabData.model_validate(json.load(f))

        if cleaned is not None:
            stats["extracted"] = len(cleaned.words) + len(cleaned.phrases) + len(cleaned.patterns)
            with open(extracted_cache, "w", encoding="utf-8") as f:
                json.dump(
                    cleaned.model_dump(mode="json", exclude_none=True),
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

        progress.update(stage2, completed=100)

        cleaned_total = (
            len(cleaned.words) + len(cleaned.phrases) + len(cleaned.patterns) if cleaned else 0
        )
        if cleaned is not None and cleaned_total > 0:
            stage3 = progress.add_task("[cyan]Stage 3: Build sense inventory", total=cleaned_total)
            registry = Registry()

            def on_sense_progress(completed: int, total: int, item_type: str) -> None:
                progress.update(
                    stage3,
                    completed=completed,
                    total=total,
                    description=f"[cyan]Stage 3: Build sense inventory ({item_type})",
                )

            sense_assigned = await assign_all_senses(
                cleaned,
                registry,
                progress_callback=on_sense_progress,
            )
            progress.update(stage3, completed=cleaned_total)
        else:
            sense_assigned = None
            registry = Registry()

        generation_total = (
            len(sense_assigned.words) + len(sense_assigned.phrases) if sense_assigned else 0
        )
        stage4 = progress.add_task("[cyan]Stage 4: Generate content", total=generation_total or 1)
        entries: list = []

        if sense_assigned is not None:
            registry_for_generation = registry if "registry" in locals() else Registry()

            def on_gen_progress(
                completed_batches: int,
                total_batches: int,
                tier: str,
                generated_count: int,
                processed_count: int,
                total_items: int,
            ) -> None:
                progress.update(
                    stage4,
                    completed=processed_count,
                    total=total_items,
                    description=f"[cyan]Stage 4: Generate ({tier}, {generated_count} senses)",
                )

            entries = await generate_all_entries(
                sense_assigned,
                registry=registry_for_generation,
                progress_callback=on_gen_progress,
            )
            stats["generated"] = len(entries)

        progress.update(stage4, completed=generation_total or 1)

        # Count entries for WSD progress
        wsd_entry_count = len([e for e in entries if hasattr(e, "senses")]) if entries else 0
        stage5 = progress.add_task("[cyan]Stage 5: WSD assignment", total=wsd_entry_count or 1)

        if entries and sense_assigned:
            # Import here to show loading status
            from .stages.stage5_wsd import load_wsd_model

            # Show model loading status (first run will download model)
            progress.update(stage5, description="[cyan]Stage 5: Loading graded-wsd...")
            load_wsd_model()  # Pre-load model

            def on_wsd_progress(completed: int, total: int, lemma: str) -> None:
                progress.update(
                    stage5,
                    completed=completed,
                    total=total,
                    description=f"[cyan]Stage 5: WSD ({lemma})",
                )

            entries = await perform_wsd(sense_assigned, entries, progress_callback=on_wsd_progress)

        progress.update(stage5, completed=wsd_entry_count or 1)

        stage6 = progress.add_task("[cyan]Stage 6: Compute relations", total=100)
        if entries:

            def on_relations_progress(completed: int, total: int, count: int) -> None:
                progress.update(
                    stage6,
                    completed=completed,
                    total=total,
                    description=f"[cyan]Stage 6: WordNet ({count} words)",
                )

            entries = compute_relations(entries, progress_callback=on_relations_progress)

        progress.update(stage6, completed=100)

        # === Stage 6.5: ML Scoring ===
        if not skip_ml and entries and cleaned:
            from .ml.train import run_ml_pipeline

            # Only count actual exams (exclude GSAT_REF and GSAT_TRIAL) for target year
            actual_exam_types = {
                ExamType.GSAT,
                ExamType.GSAT_MAKEUP,
                ExamType.AST,
                ExamType.AST_MAKEUP,
            }
            actual_exam_years = [
                f[1] for f in markdown_files if f[1] > 0 and f[2] in actual_exam_types
            ]
            max_actual_year = max(actual_exam_years) if actual_exam_years else 114
            target_year = max_actual_year + 1

            # This updates entries in-place with ml_score
            # Default: modern pipeline; use --legacy-ml for old pipeline
            entries = run_ml_pipeline(
                cleaned, entries, target_year=target_year, use_modern=not legacy_ml
            )

        stage7 = progress.add_task("[cyan]Stage 7: Write output", total=1)
        # For output metadata, include all years (including ref/trial)
        all_years = [f[1] for f in markdown_files if f[1] > 0]
        min_year = min(all_years) if all_years else 0
        max_year = max(all_years) if all_years else 0

        database = build_database(entries, min_year, max_year)
        write_output(database, output_path)
        progress.update(stage7, completed=1)

    console.print()
    table = Table(title="Pipeline Complete", show_header=False, box=None)
    table.add_column(style="dim")
    table.add_column(style="bold")
    table.add_row("Output", str(output_path))
    table.add_row("PDFs processed", str(stats["pdfs"]))
    table.add_row("Exams structured", str(stats["exams"]))
    table.add_row("Entries extracted", str(stats["extracted"]))
    table.add_row("Entries generated", str(stats["generated"]))
    console.print(Panel(table, border_style="green"))


@app.command()
def train_ml(
    data: Path = typer.Option(None, help="Path to extracted.json"),
    output: Path = typer.Option(None, help="Output model path"),
    target_year: int = typer.Option(
        None, help="Target year for prediction (default: max_year in data)"
    ),
    target_mode: str = typer.Option(
        "tested", help="Target mode: appeared/tested/active_tested/answer_only"
    ),
    gsat_only: bool = typer.Option(False, help="Train on GSAT data only"),
    compare_modes: bool = typer.Option(False, help="Compare all target modes"),
):
    import subprocess
    import sys

    data_dir = get_data_dir()

    if data is None:
        data = data_dir / "intermediate" / "extracted.json"
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
        "--target-mode",
        target_mode,
    ]

    if target_year is not None:
        cmd.extend(["--target-year", str(target_year)])
    if gsat_only:
        cmd.append("--gsat-only")
    if compare_modes:
        cmd.append("--compare-modes")

    subprocess.run(cmd, cwd=data_dir.parent)


@app.command()
def train_modern(
    data: Path = typer.Option(None, help="Path to extracted.json"),
    vocab: Path = typer.Option(None, help="Path to vocab.json (for semantic data)"),
    output: Path = typer.Option(None, help="Output directory"),
    target_year: int = typer.Option(116, help="Target year for prediction"),
    target_mode: str = typer.Option("tested", help="Target mode: tested/active_tested/answer_only"),
    skip_validation: bool = typer.Option(False, help="Skip temporal validation"),
    no_embeddings: bool = typer.Option(False, help="Disable embedding features"),
    no_graph: bool = typer.Option(False, help="Disable graph features"),
):
    """
    Train the modern ML pipeline with all advanced features.

    Uses TOPSIS/EVL value estimation, embeddings, graph features,
    sense-level survival analysis, and two-stage ensemble ranking.
    """
    from .ml.pipeline import ModernVocabPipeline, PipelineConfig

    data_dir = get_data_dir()

    if data is None:
        data = data_dir / "intermediate" / "extracted.json"
    if vocab is None:
        vocab = data_dir / "output" / "vocab.json"
    if output is None:
        output = data_dir / "output"

    config = PipelineConfig(
        target_year=target_year,
        target_mode=target_mode,
        output_dir=output,
        use_embeddings=not no_embeddings,
        use_graph=not no_graph,
    )

    pipeline = ModernVocabPipeline(config)

    entries = pipeline.load_data(data, vocab)

    pipeline.train(entries, validate=not skip_validation)

    predictions = pipeline.predict(entries)
    pipeline.print_predictions(predictions)

    pipeline.save()


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
    skip_version: bool = typer.Option(False, help="Skip version.json generation"),
):
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

    vocab_content = input_path.read_bytes()
    vocab_hash = hashlib.sha256(vocab_content).hexdigest()

    vocab_data = json.loads(vocab_content)
    entry_count = (
        len(vocab_data.get("words", []))
        + len(vocab_data.get("phrases", []))
        + len(vocab_data.get("patterns", []))
    )

    with gzip.open(output_path, "wb", compresslevel=9) as f_out:
        f_out.write(vocab_content)

    original_size = input_path.stat().st_size
    compressed_size = output_path.stat().st_size
    ratio = (1 - compressed_size / original_size) * 100

    version_info: dict[str, str | int] | None = None
    if not skip_version:
        now = datetime.now(timezone.utc)
        version_info = {
            "version": now.strftime("%Y.%m.%d"),
            "vocab_hash": vocab_hash,
            "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "entry_count": entry_count,
        }
        version_path = output_dir / "version.json"
        with open(version_path, "w", encoding="utf-8") as f:
            json.dump(version_info, f, indent=2)

    table = Table(title="Export Complete", show_header=False, box=None)
    table.add_column(style="dim")
    table.add_column(style="bold")
    table.add_row("Source", str(input_path))
    table.add_row("Output", str(output_path))
    table.add_row("Original size", f"{original_size / 1024 / 1024:.2f} MB")
    table.add_row("Compressed size", f"{compressed_size / 1024 / 1024:.2f} MB")
    table.add_row("Compression ratio", f"{ratio:.1f}%")
    if version_info:
        table.add_row("Version", version_info["version"])
        table.add_row("Entry count", str(version_info["entry_count"]))
        table.add_row("Hash", vocab_hash[:16] + "...")
    console.print(Panel(table, border_style="green"))


if __name__ == "__main__":
    app()
