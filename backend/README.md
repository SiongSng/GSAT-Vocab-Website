# GSAT Vocabulary Website - Backend

This directory contains the data processing pipeline that generates vocabulary data from CEEC exam papers.

## Directory Structure

```
backend/
├── src/                          # Pipeline source code
│   ├── cli.py                   # CLI entry point (typer)
│   ├── config.py                # Configuration settings
│   ├── llm/                     # LLM integration
│   │   ├── client.py           # OpenAI client wrapper
│   │   └── prompts.py          # Prompt templates
│   ├── ml/                      # Machine learning module
│   │   ├── features.py         # Feature extraction
│   │   ├── model.py            # ImportanceScorer model
│   │   ├── train.py            # Model training script
│   │   └── weights.py          # Legacy weight configuration
│   ├── models/                  # Pydantic data models
│   │   ├── analysis.py         # Analysis result models
│   │   ├── cleaned.py          # Cleaned vocab data models
│   │   ├── exam.py             # Exam structure models
│   │   └── vocab.py            # Vocabulary entry models
│   ├── stages/                  # Pipeline stages
│   │   ├── stage0_pdf_to_md.py # PDF → Markdown conversion
│   │   ├── stage1_structurize.py # Exam structurization
│   │   ├── stage2_clean.py     # Data cleaning & classification
│   │   ├── stage3_generate.py  # LLM entry generation
│   │   ├── stage4_output.py    # Database building & output
│   │   └── stage5_relations.py # WordNet relation computation
│   └── utils/                   # Utility modules
│       ├── scraper.py          # CEEC paper scraper
│       └── validation.py       # Data validation utilities
├── data/                         # Data directory (gitignored)
│   ├── pdf/                     # Downloaded exam PDFs
│   ├── markdown/                # Converted markdown files
│   ├── intermediate/            # Pipeline intermediate data
│   └── output/                  # Final output files
├── pyproject.toml               # Project configuration (uv)
└── uv.lock                      # Dependency lock file
```

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI API Key

### Installation

```bash
cd backend

# Install dependencies with uv
uv sync

# Or install development dependencies
uv sync --dev
```

### Environment Variables

Create `.env` file in the backend directory (see `.env.example`):

```bash
OPENAI_API_KEY=sk-proj-your-key-here
```

## Pipeline Usage

The pipeline is accessed via the `gsat-pipeline` CLI:

```bash
# Run the full pipeline
uv run gsat-pipeline run

# Run with options
uv run gsat-pipeline run --skip-llm           # Skip LLM stages (use cached)
uv run gsat-pipeline run --use-legacy-weights # Use legacy scoring instead of ML
uv run gsat-pipeline run --debug-first-batch  # Process only first batch for debugging

# Scrape exam papers from CEEC
uv run gsat-pipeline scrape

# Train ML model separately
uv run gsat-pipeline train-ml --target-year 114 --compare-modes
```

### Pipeline Stages

| Stage | Description | Output |
|-------|-------------|--------|
| 0 | PDF → Markdown conversion | `data/markdown/*.md` |
| 1 | Exam structurization (LLM) | `data/intermediate/exams/*.json` |
| 2 | Clean & classify vocabulary | `data/intermediate/cleaned.json` |
| 2.5 | Train ML importance model | `data/output/importance_model.pkl` |
| 3 | Generate vocabulary entries (LLM) | Vocabulary database |
| 4 | Compute WordNet relations | Enhanced entries |
| 5 | Build database & write output | `data/output/vocab.json` |

## Technology Stack

- **Python 3.13+** with uv package manager
- **pdfplumber** - PDF text extraction
- **spaCy** - NLP processing
- **OpenAI API** - LLM for structurization and generation
- **scikit-learn** - ML importance scoring
- **Pydantic** - Data validation
- **typer + rich** - CLI interface

## Data Sources

### Official Wordlist

The `data/official_wordlist.json` file is derived from the Taiwan high school 6K vocabulary list (108 curriculum edition), originally compiled by the community at:

https://github.com/EngTW/English-for-Programmers/tree/main/lists/Taiwan-high-school-6K-108-edition

### Exam Papers

Exam papers are scraped from the College Entrance Examination Center (CEEC, 大考中心) official website.

## Acknowledgments

- [EngTW/English-for-Programmers](https://github.com/EngTW/English-for-Programmers) for the vocabulary list compilation
- 大學入學考試中心 (CEEC) for providing past exam papers

## Development

```bash
# Run tests
uv run pytest

# Lint code
uv run ruff check src/

# Format code
uv run ruff format src/
```
