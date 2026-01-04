import asyncio
import re
from collections.abc import Callable
from pathlib import Path

import pdfplumber
from pydantic import BaseModel

from ..llm import STAGE0_SYSTEM, ModelTier, get_llm_client
from ..models import ExamType


class FormattedMarkdown(BaseModel):
    content: str


def extract_text_from_pdf(pdf_path: Path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if text:
                pages.append(text)
        return "\n\n".join(pages)


def parse_exam_info(filename: str) -> tuple[int, ExamType]:
    # 1. Try standardized tokens first (deterministic)
    if "_AST_MAKEUP_" in filename:
        exam_type = ExamType.AST_MAKEUP
    elif "_GSAT_MAKEUP_" in filename:
        exam_type = ExamType.GSAT_MAKEUP
    elif "_GSAT_TRIAL_" in filename:
        exam_type = ExamType.GSAT_TRIAL
    elif "_GSAT_REF_" in filename:
        exam_type = ExamType.GSAT_REF
    elif "_AST_" in filename:
        exam_type = ExamType.AST
    elif "_GSAT_" in filename:
        exam_type = ExamType.GSAT
    else:
        # 2. Fallback heuristic for legacy/manual files
        is_ast = any(k in filename for k in ["指考", "指定科目"])
        is_makeup = "補考" in filename
        is_trial = "試辦" in filename
        is_ref = "參考" in filename

        if is_trial:
            exam_type = ExamType.GSAT_TRIAL
        elif is_ref:
            exam_type = ExamType.GSAT_REF
        elif is_ast:
            exam_type = ExamType.AST_MAKEUP if is_makeup else ExamType.AST
        else:
            exam_type = ExamType.GSAT_MAKEUP if is_makeup else ExamType.GSAT

    # Year extraction
    match = re.search(r"(\d{4})_(\d{2,3})_", filename)
    if match:
        year_roc = int(match.group(2))
        return year_roc, exam_type

    # Fallback year extraction
    match = re.search(r"(\d{2,3})學年", filename)
    if match:
        year_roc = int(match.group(1))
        return year_roc, exam_type

    return 0, exam_type


async def pdf_to_markdown(pdf_path: Path) -> tuple[str, int, ExamType]:
    raw_text = extract_text_from_pdf(pdf_path)
    year, exam_type = parse_exam_info(pdf_path.name)

    client = get_llm_client()
    prompt = f"""<exam_metadata>
Year: {year} (民國)
Type: {exam_type.value}
</exam_metadata>

<raw_pdf_text>
{raw_text}
</raw_pdf_text>

Convert this exam to clean Markdown. Preserve all questions, options, and passage structure."""

    result = await client.complete(
        prompt=prompt,
        system=STAGE0_SYSTEM,
        response_model=FormattedMarkdown,
        temperature=0.1,
        tier=ModelTier.FAST,
    )
    return result.content, year, exam_type


async def process_all_pdfs(
    pdf_dir: Path,
    output_dir: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[tuple[Path, int, ExamType]]:
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        return []

    total_files = len(pdf_files)
    completed_count = 0

    async def _process_single(pdf_path: Path) -> tuple[Path, int, ExamType]:
        nonlocal completed_count

        # Use clean standardized filename: YYYY_TWY_TYPE.md
        year, exam_type = parse_exam_info(pdf_path.name)
        full_year = 1911 + year
        clean_stem = f"{full_year}_{year}_{exam_type.value}"
        output_path = output_dir / f"{clean_stem}.md"

        if output_path.exists():
            result = (output_path, year, exam_type)
        else:
            markdown, year, exam_type = await pdf_to_markdown(pdf_path)
            output_path.write_text(markdown, encoding="utf-8")
            result = (output_path, year, exam_type)

        completed_count += 1
        if progress_callback:
            progress_callback(completed_count, total_files)
        return result

    return await asyncio.gather(*[_process_single(p) for p in pdf_files])
