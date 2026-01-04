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
│   │   ├── ranker.py           # LightGBM ranking model
│   │   ├── survival.py         # Survival analysis model
│   │   ├── evaluation.py       # Model evaluation utilities
│   │   ├── train.py            # Model training script
│   │   └── weights.py          # Legacy weight configuration
│   ├── models/                  # Pydantic data models
│   │   ├── cleaned.py          # Extracted vocab data models
│   │   ├── exam.py             # Exam structure models
│   │   ├── sense_assigned.py   # Sense-assigned data models
│   │   └── vocab.py            # Vocabulary entry models
│   ├── registry/                # Sense registry system
│   │   ├── models.py           # Registry data models
│   │   └── registry.py         # SQLite-based sense registry
│   ├── stages/                  # Pipeline stages
│   │   ├── stage0_pdf_to_md.py        # PDF → Markdown conversion
│   │   ├── stage1_structurize.py      # Exam structurization (LLM)
│   │   ├── stage2_extract.py          # Vocabulary extraction & NLP
│   │   ├── stage3_sense_inventory.py  # Build sense inventory (LLM)
│   │   ├── stage4_generate.py         # Content generation (LLM)
│   │   ├── stage5_wsd.py              # Word sense disambiguation
│   │   ├── stage6_relations.py        # WordNet relation computation
│   │   └── stage7_output.py           # Database building & output
│   └── utils/                   # Utility modules
│       ├── nlp.py              # NLP utilities (spaCy, lemmatization)
│       ├── patterns.py         # Regex pattern utilities
│       └── scraper.py          # CEEC paper scraper
├── data/                         # Data directory (gitignored)
│   ├── pdf/                     # Downloaded exam PDFs
│   ├── markdown/                # Converted markdown files
│   ├── registry/                # SQLite sense registry
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
uv run gsat-pipeline run --skip-ml      # Skip ML training stage
uv run gsat-pipeline run --exam-only    # Only include words that appear in exams

# Scrape exam papers from CEEC
uv run gsat-pipeline scrape

# Train ML model separately
uv run gsat-pipeline train-ml --compare-modes

# Export vocab.json as gzip to frontend
uv run gsat-pipeline export
```

### Pipeline Stages

| Stage | Description | Output |
|-------|-------------|--------|
| 0 | PDF → Markdown conversion | `data/markdown/*.md` |
| 1 | Exam structurization (LLM) | `data/intermediate/exams/*.json` |
| 2 | Extract vocabulary (NLP) | `data/intermediate/extracted.json` |
| 3 | Build sense inventory (LLM) | Registry database |
| 4 | Generate content (LLM) | Vocabulary entries |
| 5 | Word sense disambiguation | Sense-assigned entries |
| 6 | Compute WordNet relations | Enhanced entries |
| 6.5 | ML importance scoring | Scored entries (WIP) |
| 7 | Build database & write output | `data/output/vocab.json` |

### Export Command

The `export` command compresses `vocab.json` to gzip and copies it to the frontend for lazy loading into IndexedDB:

```bash
uv run gsat-pipeline export
```

Options:
- `--input-path`: Custom input vocab.json path (default: `data/output/vocab.json`)
- `--output-dir`: Custom output directory (default: `../frontend/public/data`)

Output: `frontend/public/data/vocab.json.gz` (~82% compression ratio)

## Technology Stack

- **Python 3.13+** with uv package manager
- **pdfplumber** - PDF text extraction
- **spaCy** (en_core_web_trf) - NLP processing with transformer model
- **OpenAI API** - LLM for structurization, sense inventory, and content generation
- **sentence-transformers** - Semantic embeddings for WSD
- **LightGBM** - ML ranking model for importance scoring
- **lifelines** - Survival analysis for prediction
- **scikit-learn** - ML utilities
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

# Type check
uvx ty check
```
