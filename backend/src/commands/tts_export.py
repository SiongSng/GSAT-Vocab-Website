import concurrent.futures
import contextlib
import json
import logging
import os
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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

from ..utils.tts_hash import normalize_tts_text, tts_text_hash

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, show_time=False, show_path=False)],
)


def get_data_dir() -> Path:
    return Path(__file__).parent.parent.parent / "data"


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


_TOKEN_SPLIT_RE = re.compile(r"\s+")
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")


TTSKind = Literal["lemma", "sentence"]
TTSEngine = Literal["kokoro", "supertonic"]


@dataclass(frozen=True)
class TTSItem:
    text: str
    kind: TTSKind


@dataclass(frozen=True)
class TTSJob:
    h: str
    text: str
    engine: TTSEngine
    out_path: Path


def _iter_vocab_texts(vocab: dict) -> list[str]:
    return [i.text for i in _iter_vocab_items(vocab)]


def _iter_vocab_items(vocab: dict) -> list[TTSItem]:
    items: list[TTSItem] = []

    for entry in vocab.get("words", []):
        if isinstance(entry, dict) and isinstance(entry.get("lemma"), str):
            items.append(TTSItem(text=entry["lemma"], kind="lemma"))
        for sense in entry.get("senses", []) if isinstance(entry, dict) else []:
            if isinstance(sense, dict) and isinstance(sense.get("generated_example"), str):
                items.append(TTSItem(text=sense["generated_example"], kind="sentence"))
            for ex in sense.get("examples", []) if isinstance(sense, dict) else []:
                if isinstance(ex, dict) and isinstance(ex.get("text"), str):
                    items.append(TTSItem(text=ex["text"], kind="sentence"))

    for entry in vocab.get("phrases", []):
        if isinstance(entry, dict) and isinstance(entry.get("lemma"), str):
            items.append(TTSItem(text=entry["lemma"], kind="lemma"))
        for sense in entry.get("senses", []) if isinstance(entry, dict) else []:
            if isinstance(sense, dict) and isinstance(sense.get("generated_example"), str):
                items.append(TTSItem(text=sense["generated_example"], kind="sentence"))
            for ex in sense.get("examples", []) if isinstance(sense, dict) else []:
                if isinstance(ex, dict) and isinstance(ex.get("text"), str):
                    items.append(TTSItem(text=ex["text"], kind="sentence"))

    for entry in vocab.get("patterns", []):
        for subtype in entry.get("subtypes", []) if isinstance(entry, dict) else []:
            if isinstance(subtype, dict) and isinstance(subtype.get("generated_example"), str):
                items.append(TTSItem(text=subtype["generated_example"], kind="sentence"))
            for ex in subtype.get("examples", []) if isinstance(subtype, dict) else []:
                if isinstance(ex, dict) and isinstance(ex.get("text"), str):
                    items.append(TTSItem(text=ex["text"], kind="sentence"))

    return items


def _kokoro_stabilize_short_text(text: str) -> str:
    trimmed = text.strip()
    if not trimmed:
        return trimmed
    token_count = len(_TOKEN_SPLIT_RE.split(trimmed))
    if token_count <= 2 and not re.search(r"[.!?]$", trimmed):
        return f"{trimmed}."
    return trimmed


def _should_skip_tts_text(text: str, *, skip_non_english: bool) -> bool:
    return bool(skip_non_english and _CJK_RE.search(text))


def _resolve_torch_device(device: str) -> str:
    if device != "auto":
        return device

    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        return "cpu"

    return "cpu"


def _assert_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise typer.BadParameter(
            "ffmpeg not found in PATH (required to encode to MP3); install ffmpeg first."
        )


_KOKORO_VOICE = "af_heart"
_KOKORO_LANG_CODE = "a"
_KOKORO_SPEED = 1.0
_SUPERTONIC_VOICE = "M1"
_SUPERTONIC_TOTAL_STEPS = 3
_SUPERTONIC_SPEED = 1.0
_SUPERTONIC_BATCH_SIZE = 25
_MP3_BITRATE = "64k"
_ENCODE_WORKERS = 4
_MAX_PENDING_ENCODES = 16


def tts_export(
    input_path: Path = typer.Option(None, help="Input vocab.json path"),
    output_dir: Path = typer.Option(None, help="Output directory for audio files"),
    dataset_repo: str = typer.Option(
        "TCabbage/gsat-vocab-sentences-tts",
        help="Hugging Face dataset repo id",
    ),
    upload: bool = typer.Option(False, help="Upload output_dir to Hugging Face dataset"),
    commit_message: str = typer.Option("Add TTS audio", help="Hugging Face commit message"),
    device: str = typer.Option("auto", help="Torch device: auto/cpu/mps/cuda"),
    overwrite: bool = typer.Option(False, help="Overwrite existing audio files"),
):
    data_dir = get_data_dir()
    if input_path is None:
        input_path = data_dir / "output" / "vocab.json"
    if output_dir is None:
        output_dir = data_dir / "output" / "tts"

    if not input_path.exists():
        console.print(f"[red]✗[/] Input file not found: {input_path}")
        raise typer.Exit(1)

    hf_cache_dir = data_dir / "cache" / "hf"
    supertonic_model_dir = data_dir / "cache" / "supertonic"
    hf_cache_dir.mkdir(parents=True, exist_ok=True)
    supertonic_model_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", str(hf_cache_dir))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(hf_cache_dir / "hub"))
    os.environ.setdefault("HF_HUB_CACHE", str(hf_cache_dir / "hub"))

    _assert_ffmpeg_available()

    try:
        import numpy as np
        import soundfile as sf
    except Exception as e:
        console.print("[red]✗[/] Missing TTS dependencies. Install with: uv sync --dev --extra tts")
        raise typer.Exit(1) from e

    resolved_device = device

    console.print(
        "TTS export: "
        f"input={input_path} output={output_dir} "
        f"kokoro_voice={_KOKORO_VOICE} supertonic_voice={_SUPERTONIC_VOICE} device={device}"
    )

    vocab = json.loads(input_path.read_text(encoding="utf-8"))
    all_items = _iter_vocab_items(vocab)

    def engine_priority(engine: TTSEngine) -> int:
        return 1 if engine == "kokoro" else 0

    hash_to_item: dict[str, tuple[str, TTSEngine]] = {}
    skipped_by_filter = 0
    for item in all_items:
        normalized = normalize_tts_text(item.text)
        if not normalized:
            continue
        if _should_skip_tts_text(normalized, skip_non_english=True):
            skipped_by_filter += 1
            continue
        h = tts_text_hash(normalized)
        engine: TTSEngine = "kokoro" if item.kind == "lemma" else "supertonic"
        existing = hash_to_item.get(h)
        if existing is None or engine_priority(engine) > engine_priority(existing[1]):
            hash_to_item[h] = (normalized, engine)

    hashes = sorted(hash_to_item.keys())

    audio_root = output_dir / "audio"
    audio_root.mkdir(parents=True, exist_ok=True)

    skipped = 0
    failed = 0
    generated_kokoro = 0
    generated_supertonic = 0

    jobs: list[TTSJob] = []
    for h in hashes:
        text, engine = hash_to_item[h]
        out_path = audio_root / h[:2] / f"{h}.mp3"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists() and not overwrite:
            skipped += 1
            continue
        jobs.append(TTSJob(h=h, text=text, engine=engine, out_path=out_path))

    kokoro_jobs = [j for j in jobs if j.engine == "kokoro"]
    supertonic_jobs = [j for j in jobs if j.engine == "supertonic"]

    torch_mod = None
    kokoro_pipeline = None
    kokoro_g2p = None
    if kokoro_jobs:
        try:
            import torch
            from kokoro import KPipeline
            from misaki import en as misaki_en
        except Exception as e:
            console.print(
                "[red]✗[/] Missing Kokoro/Misaki dependencies. Install with: uv sync --dev --extra tts"
            )
            raise typer.Exit(1) from e

        torch_mod = torch
        resolved_device = _resolve_torch_device(device)
        if resolved_device == "mps":
            os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        try:
            kokoro_pipeline = KPipeline(
                lang_code=_KOKORO_LANG_CODE,
                repo_id="hexgrad/Kokoro-82M",
                device=resolved_device,
            )
        except TypeError:
            kokoro_pipeline = KPipeline(lang_code=_KOKORO_LANG_CODE, device=resolved_device)

        fallback = None
        with contextlib.suppress(Exception):
            from misaki import espeak as misaki_espeak

            fallback = misaki_espeak.EspeakFallback(british=False)

        kokoro_g2p = misaki_en.G2P(trf=False, british=False, fallback=fallback)

    supertonic_cls = None
    if supertonic_jobs:
        try:
            from supertonic import TTS as SupertoneTTS
        except Exception as e:
            console.print(
                "[red]✗[/] Missing Supertonic dependencies. Install with: uv sync --dev --extra tts"
            )
            raise typer.Exit(1) from e

        supertonic_cls = SupertoneTTS

    supertonic_local = threading.local()

    def get_supertonic():
        tts = getattr(supertonic_local, "tts", None)
        style = getattr(supertonic_local, "style", None)
        if tts is not None and style is not None:
            return tts, style

        assert supertonic_cls is not None
        tts = supertonic_cls(
            model_dir=supertonic_model_dir,
            auto_download=True,
        )
        style = tts.get_voice_style(voice_name=_SUPERTONIC_VOICE)
        supertonic_local.tts = tts
        supertonic_local.style = style
        return tts, style

    if supertonic_jobs:
        tts, style = get_supertonic()
        del tts, style

    def supertonic_repeat_style(style, bsz: int):
        from supertonic.core import Style

        ttl = np.repeat(style.ttl, bsz, axis=0)
        dp = np.repeat(style.dp, bsz, axis=0)
        return Style(ttl, dp)

    def encode_wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
        cmd = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-vn",
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ac",
            "1",
            "-ar",
            "24000",
            "-b:a",
            _MP3_BITRATE,
            str(mp3_path),
        ]
        subprocess.run(cmd, check=True)
        wav_path.unlink(missing_ok=True)

    def to_numpy_audio(x: object):
        if torch_mod is not None and isinstance(x, torch_mod.Tensor):
            return x.detach().cpu().numpy()
        return np.asarray(x)

    def kokoro_ipa_markup(text: str) -> str:
        if kokoro_g2p is None:
            return text

        try:
            phonemes, _ = kokoro_g2p(text)
        except Exception:
            return text

        ipa = re.sub(r"\s+", " ", str(phonemes)).strip().rstrip(".!? ")
        if not ipa:
            return text

        visible = text.replace("[", "(").replace("]", ")")
        return f"[{visible}](/{ipa}/)"

    def synthesize_kokoro_to_wav(text: str, wav_path: Path) -> None:
        assert kokoro_pipeline is not None
        assert torch_mod is not None
        processed = _kokoro_stabilize_short_text(kokoro_ipa_markup(text))
        chunks: list[object] = []
        with torch_mod.inference_mode():
            generator = kokoro_pipeline(processed, voice=_KOKORO_VOICE, speed=_KOKORO_SPEED)
            for _, _, audio in generator:
                chunks.append(audio)
        if not chunks:
            raise RuntimeError("Empty audio")
        audio_arr = np.concatenate([to_numpy_audio(c) for c in chunks])
        sf.write(wav_path, audio_arr, 24000)

    with create_progress() as progress:
        task = progress.add_task("[cyan]Generating TTS audio", total=len(jobs) or 1)
        completed = 0

        def advance() -> None:
            nonlocal completed
            completed += 1
            progress.update(task, completed=completed)

        max_workers = _ENCODE_WORKERS
        max_queue = _MAX_PENDING_ENCODES

        if kokoro_jobs:
            if max_workers <= 1:
                for job in kokoro_jobs:
                    wav_tmp = job.out_path.with_suffix(".wav")
                    try:
                        synthesize_kokoro_to_wav(job.text, wav_tmp)
                        encode_wav_to_mp3(wav_tmp, job.out_path)
                        generated_kokoro += 1
                    except Exception as e:
                        failed += 1
                        console.print(f"[red]✗[/] {job.h[:8]}... failed: {e}")
                        with contextlib.suppress(Exception):
                            wav_tmp.unlink(missing_ok=True)
                    advance()
            else:
                pending: dict[concurrent.futures.Future[None], TTSJob] = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    for job in kokoro_jobs:
                        wav_tmp = job.out_path.with_suffix(".wav")
                        try:
                            synthesize_kokoro_to_wav(job.text, wav_tmp)
                            fut = executor.submit(encode_wav_to_mp3, wav_tmp, job.out_path)
                            pending[fut] = job
                        except Exception as e:
                            failed += 1
                            console.print(f"[red]✗[/] {job.h[:8]}... failed: {e}")
                            with contextlib.suppress(Exception):
                                wav_tmp.unlink(missing_ok=True)
                            advance()
                            continue

                        if len(pending) >= max_queue:
                            done, _ = concurrent.futures.wait(
                                pending, return_when=concurrent.futures.FIRST_COMPLETED
                            )
                            for d in done:
                                job = pending.pop(d)
                                try:
                                    d.result()
                                    generated_kokoro += 1
                                except Exception as e:
                                    failed += 1
                                    console.print(f"[red]✗[/] {job.h[:8]}... encode failed: {e}")
                                advance()

                    while pending:
                        done, _ = concurrent.futures.wait(
                            pending, return_when=concurrent.futures.FIRST_COMPLETED
                        )
                        for d in done:
                            job = pending.pop(d)
                            try:
                                d.result()
                                generated_kokoro += 1
                            except Exception as e:
                                failed += 1
                                console.print(f"[red]✗[/] {job.h[:8]}... encode failed: {e}")
                            advance()

        if kokoro_jobs:
            console.print("[dim]Releasing Kokoro model memory...[/]")
            del kokoro_pipeline, kokoro_g2p
            kokoro_pipeline = None
            kokoro_g2p = None
            if torch_mod is not None:
                import gc

                gc.collect()
                if torch_mod.cuda.is_available():
                    torch_mod.cuda.empty_cache()
                elif hasattr(torch_mod.backends, "mps") and torch_mod.backends.mps.is_available():
                    torch_mod.mps.empty_cache()

        if supertonic_jobs:
            tts, base_style = get_supertonic()
            batch_size = _SUPERTONIC_BATCH_SIZE

            short_jobs = [j for j in supertonic_jobs if len(j.text) <= 300]
            long_jobs = [j for j in supertonic_jobs if len(j.text) > 300]

            def write_trimmed_and_encode(job: TTSJob, wav_1d, sample_rate: int) -> None:
                wav_tmp = job.out_path.with_suffix(".wav")
                try:
                    sf.write(wav_tmp, wav_1d, sample_rate)
                    encode_wav_to_mp3(wav_tmp, job.out_path)
                finally:
                    with contextlib.suppress(Exception):
                        wav_tmp.unlink(missing_ok=True)

            for start in range(0, len(short_jobs), batch_size):
                batch = short_jobs[start : start + batch_size]
                texts = [j.text for j in batch]
                style = supertonic_repeat_style(base_style, len(batch))
                try:
                    wav, dur = tts.model(texts, style, _SUPERTONIC_TOTAL_STEPS, _SUPERTONIC_SPEED)
                except Exception as e:
                    console.print(f"[yellow]![/] Supertonic batch failed, falling back: {e}")
                    for job in batch:
                        try:
                            w, _ = tts.synthesize(
                                job.text,
                                voice_style=base_style,
                                total_steps=_SUPERTONIC_TOTAL_STEPS,
                                speed=_SUPERTONIC_SPEED,
                                verbose=False,
                            )
                            write_trimmed_and_encode(job, w.squeeze(), tts.sample_rate)
                            generated_supertonic += 1
                        except Exception as e2:
                            failed += 1
                            console.print(f"[red]✗[/] {job.h[:8]}... failed: {e2}")
                        advance()
                    continue

                for i, job in enumerate(batch):
                    try:
                        samples = int(tts.sample_rate * float(dur[i]))
                        w = wav[i, :samples]
                        write_trimmed_and_encode(job, w, tts.sample_rate)
                        generated_supertonic += 1
                    except Exception as e:
                        failed += 1
                        console.print(f"[red]✗[/] {job.h[:8]}... failed: {e}")
                    advance()

            for job in long_jobs:
                try:
                    w, _ = tts.synthesize(
                        job.text,
                        voice_style=base_style,
                        total_steps=_SUPERTONIC_TOTAL_STEPS,
                        speed=_SUPERTONIC_SPEED,
                        verbose=False,
                    )
                    write_trimmed_and_encode(job, w.squeeze(), tts.sample_rate)
                    generated_supertonic += 1
                except Exception as e:
                    failed += 1
                    console.print(f"[red]✗[/] {job.h[:8]}... failed: {e}")
                advance()

    index_path = output_dir / "index.jsonl"
    with open(index_path, "w", encoding="utf-8") as f:
        for h in hashes:
            text, engine = hash_to_item[h]
            audio_path = f"audio/{h[:2]}/{h}.mp3"
            f.write(
                json.dumps(
                    {"hash": h, "text": text, "engine": engine, "audio": audio_path},
                    ensure_ascii=False,
                )
                + "\n"
            )

    table = Table(title="TTS Export Complete", show_header=False, box=None)
    table.add_column(style="dim")
    table.add_column(style="bold")
    table.add_row("Unique texts", str(len(hashes)))
    table.add_row("Skipped non-English", str(skipped_by_filter))
    table.add_row("Generated", str(generated_kokoro + generated_supertonic))
    table.add_row("Generated (Kokoro)", str(generated_kokoro))
    table.add_row("Generated (Supertonic)", str(generated_supertonic))
    table.add_row("Skipped", str(skipped))
    table.add_row("Failed", str(failed))
    table.add_row("Output", str(output_dir))
    console.print(Panel(table, border_style="green" if failed == 0 else "yellow"))

    if upload:
        try:
            from huggingface_hub import HfApi
        except Exception as e:
            console.print(
                "[red]✗[/] Missing Hugging Face dependency. Install with: uv sync --dev --extra tts"
            )
            raise typer.Exit(1) from e

        from huggingface_hub import get_token

        token = get_token()
        if not token:
            console.print(
                "[red]✗[/] HF token not found. Set HF_TOKEN env var or run: huggingface-cli login"
            )
            raise typer.Exit(1)

        readme_path = output_dir / "README.md"
        if not readme_path.exists():
            readme_content = """---
license: cc-by-4.0
task_categories:
  - text-to-speech
language:
  - en
tags:
  - tts
  - vocabulary
  - gsat
---

# GSAT Vocabulary TTS Audio

Text-to-speech audio files for GSAT (General Scholastic Ability Test) English vocabulary.

## Structure

- `audio/` - MP3 audio files organized by hash prefix (e.g., `audio/ab/abcd1234....mp3`)
- `index.jsonl` - Index file with columns: `hash`, `text`, `engine`, `audio` (path to mp3)

## Engines

- **Kokoro** (`af_heart` voice) - Used for lemmas (single words/phrases)
- **Supertonic** (`M1` voice) - Used for example sentences

## Audio Format

- Format: MP3
- Sample rate: 24kHz
- Channels: Mono
- Bitrate: 48kbps
- Normalization: loudnorm (I=-16, TP=-1.5, LRA=11)
"""
            readme_path.write_text(readme_content, encoding="utf-8")
            console.print("[dim]Generated README.md[/]")

        console.print(f"Uploading to hf://datasets/{dataset_repo} ...")
        api = HfApi(token=token)
        api.upload_large_folder(
            repo_id=dataset_repo,
            repo_type="dataset",
            folder_path=str(output_dir),
            ignore_patterns=[".DS_Store", "*.pyc", "__pycache__", ".cache"],
        )
        console.print("[green]✓[/] Upload complete")
