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

#### State Management (`/frontend/src/lib/stores`)

- `vocab.svelte.ts` - Vocabulary index, word selection, filtering
- `app.svelte.ts` - App-level state (current view, mobile detection)
- `flashcard.svelte.ts` - Flashcard session state
- `quiz.svelte.ts` - Quiz session state

#### API Layer (`/frontend/src/lib/api.ts`)

- Communicates with Cloudflare Workers backend
- Implements client-side caching with 5-minute TTL
- Transforms API responses to match TypeScript interfaces

### Backend

- **Platform**: Cloudflare Workers
- **API Base**: `https://gsat-vocab-api.vic0407lu.workers.dev`

## Development Commands

```bash
cd frontend
bun install        # Install dependencies
bun run dev        # Start dev server
bun run build      # Production build
bun run preview    # Preview production build
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
4. **Use built-in diagnostics** - Prefer IDE diagnostics over `cargo check` or similar CLI tools

## CSS Notes

- When manipulating classes via JavaScript (`classList.add/remove`), use `:global(.class-name)` in scoped styles
- Tailwind classes for utility styling, scoped `<style>` for component-specific styles

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/vocab/index` | Full vocabulary index |
| `GET /api/vocab/detail/:lemma` | Word detail with meanings and sentences |
| `GET /api/vocab/random` | Random word (supports filters) |
| `GET /api/search-index` | Search index by POS |
| `GET /api/quiz/generate` | Generate quiz questions |
| `GET /api/audio/:lemma` | Word pronunciation audio |
| `GET /api/vocab/:lemma/sentences` | Paginated sentences |