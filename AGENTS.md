# AGENTS.md

## Project Overview

GSAT-Vocab-Website is a vocabulary learning platform for Taiwan's GSAT (General Scholastic Ability Test) English exam. It provides word browsing, flashcard study, and quiz features based on vocabulary extracted from past exam papers.

## Architecture

### Frontend (`/frontend`)

- **Framework**: Svelte 5 with TypeScript
- **Build Tool**: Vite
- **Package Manager**: Bun
- **Styling**: Tailwind CSS + scoped component styles

#### Key Components

- `App.svelte` - Main app shell with view routing
- `BrowseView.svelte` - Word list browsing with filters
- `WordList.svelte` - Virtualized list (5000+ items) using `content-visibility: auto`
- `WordDetail.svelte` - Word detail panel with meanings, POS distribution, sentences
- `FlashcardView.svelte` - Flashcard study mode
- `QuizView.svelte` - Quiz generation and interaction

#### Design System (`/frontend/DESIGN_SYSTEM.md`)

The frontend uses a Heptabase/Notion-inspired design system with custom CSS tokens. Key aspects:

- **Color tokens**: `surface-*`, `content-*`, `border`, `accent`, `srs-*`
- **Philosophy**: Light borders over heavy shadows, subtle interactions
- **Components**: Cards, buttons, chips, form controls all follow consistent patterns

Refer to `frontend/DESIGN_SYSTEM.md` for complete specification including:
- Color system with Tailwind class mappings
- Typography scale and hierarchy
- Component patterns (buttons, cards, chips, list items)
- Form control styling
- State management (hover, focus, active, disabled)
- Migration guide from legacy Slate/Indigo colors

#### State Management (`/frontend/src/lib/stores`)

- `vocab.svelte.ts` - Vocabulary index, word selection, filtering
- `app.svelte.ts` - App-level state (current view, mobile detection)
- `flashcard.svelte.ts` - Flashcard session state
- `quiz.svelte.ts` - Quiz session state

#### API Layer (`/frontend/src/lib/api.ts`)

- Communicates with Cloudflare Workers backend
- Implements client-side caching with 5-minute TTL
- Transforms API responses to match TypeScript interfaces

### Backend (`/backend`)

The backend is a Python-based data processing pipeline that generates vocabulary data from CEEC exam papers.

- **Package Manager**: uv
- **Python Version**: 3.13+
- **CLI Framework**: typer + rich

#### Pipeline Stages (Refactored)

| Stage | Module | Description |
|-------|--------|-------------|
| 0 | `stage0_pdf_to_md.py` | PDF → Markdown conversion |
| 1 | `stage1_structurize.py` | LLM-based exam structurization |
| 2 | `stage2_extract.py` | Vocabulary extraction with NLP |
| 3 | `stage3_sense_inventory.py` | Build sense inventory via LLM |
| 4 | `stage4_generate.py` | LLM content generation |
| 5 | `stage5_wsd.py` | Word sense disambiguation |
| 6 | `stage6_relations.py` | WordNet relation computation |
| 6.5 | `ml/train.py` | ML importance scoring (WIP) |
| 7 | `stage7_output.py` | Database building & output |

#### Key Modules

- `src/cli.py` - CLI entry point with `run`, `scrape`, `train-ml`, `export` commands
- `src/config.py` - Pydantic settings for OpenAI configuration
- `src/llm/` - OpenAI client wrapper and prompt templates
- `src/ml/` - Machine learning importance scoring (LightGBM, survival analysis)
- `src/models/` - Pydantic data models for exams, vocabulary, sense assignment
- `src/registry/` - SQLite-based sense registry for vocabulary management
- `src/stages/` - Pipeline stage implementations
- `src/utils/` - NLP utilities, pattern matching, and scraper

#### Data Flow

```
PDF files → Markdown → Structured Exams → Extracted Vocab → Sense Inventory → Generated Content → WSD → Relations → vocab.json
```

## Development Commands

### Frontend

```bash
cd frontend
bun install        # Install dependencies
bun run build      # Production build
bun run preview    # Preview production build
```

### Backend

```bash
cd backend
uv sync            # Install dependencies
uv sync --dev      # Install with dev dependencies

# Pipeline commands
uv run gsat-pipeline run              # Run full pipeline
uv run gsat-pipeline run --skip-ml    # Skip ML training stage
uv run gsat-pipeline run --exam-only  # Only include exam words
uv run gsat-pipeline scrape           # Scrape CEEC papers
uv run gsat-pipeline train-ml         # Train ML model separately
uv run gsat-pipeline export           # Export vocab.json.gz to frontend

# Development
uv run pytest                         # Run tests
uv run ruff check src/                # Lint code
uv run ruff format src/               # Format code
uvx ty check                          # Type check (10-100x faster than mypy/Pyright)
```

## Performance Considerations

### Word List Optimization

The word list contains 5000+ items. Key optimizations:

1. **CSS `content-visibility: auto`** - Browser skips rendering offscreen items
2. **Manual active state management** - Uses `$effect` + `querySelector` instead of reactive class bindings to avoid 5000+ subscriptions
3. **`$state.raw`** - Used for large immutable data (vocab index, word details) to skip deep reactivity

### Loading States

- Skeleton loaders with shimmer animation (2.5s duration)
- `selectedLemma` updates immediately on click for instant UI feedback
- Word details fetched async with cache check to skip skeleton when cached

## Code Style Guidelines

1. **No unnecessary comments** - Code should be self-explanatory
2. **All comments in English** - When comments are needed
3. **TDD principles** - Write meaningful tests, not tests for coverage
4. **Type checking: `uvx ty check` FIRST** - Always use ty as the primary type checker for Python (10-100x faster than mypy/Pyright). Only fall back to mypy/Pyright if ty doesn't catch specific issues.
5. **Prefer IDE diagnostics** - For other languages, use built-in IDE diagnostics over CLI tools like `cargo check`

## CSS Notes

- When manipulating classes via JavaScript (`classList.add/remove`), use `:global(.class-name)` in scoped styles
- Tailwind classes for utility styling, scoped `<style>` for component-specific styles
