# GSAT Vocabulary Website - Frontend

A high-performance vocabulary learning platform for GSAT (General Scholastic Ability Test) preparation, built with modern web technologies.

## Tech Stack

- **Bun** - Fast JavaScript runtime and package manager
- **Svelte 5** - Reactive UI framework with runes
- **TypeScript** - Type-safe development
- **Vite** - Next-generation build tool
- **Tailwind CSS** - Utility-first CSS framework

## Features

### Browse Mode
- **Virtual Scrolling** - Efficiently renders 7000+ words without performance degradation
- Search and filter vocabulary by frequency and part of speech
- View word details with definitions and examples
- Listen to pronunciation audio
- Grid or list view options

### Flashcard Mode
- Interactive card flipping with smooth animations
- Mark words as mastered or needs review
- Auto-play pronunciation
- Progress tracking with localStorage persistence
- Export review list functionality

### Quiz Mode
- **Multiple Choice** - Definition to word / Word to definition
- **Spelling Test** - Listen and spell the word
- **Fill-in-the-Blank** - Context-based learning
- Retry incorrect answers feature

## Performance Improvements

The main performance optimization is **Virtual Scrolling**. The previous vanilla JS implementation rendered all 7000+ DOM nodes at once, causing:

- Slow initial render
- Laggy scrolling
- High memory usage
- Full re-renders on filter changes

With virtual scrolling, only ~20-30 visible items are rendered at any time, regardless of list size. Combined with Svelte 5's compiled reactivity, this eliminates the manual DOM manipulation overhead.

## Project Structure

```
frontend/
├── src/
│   ├── lib/
│   │   ├── components/
│   │   │   ├── Header.svelte
│   │   │   ├── Sidebar.svelte
│   │   │   ├── BrowseView.svelte
│   │   │   ├── WordList.svelte      # Virtual scrolling list
│   │   │   ├── WordDetail.svelte
│   │   │   ├── FlashcardView.svelte
│   │   │   └── QuizView.svelte
│   │   ├── stores/
│   │   │   ├── app.svelte.ts        # App state (mode, mobile, etc.)
│   │   │   ├── vocab.svelte.ts      # Vocabulary data & filters
│   │   │   ├── flashcard.svelte.ts
│   │   │   └── quiz.svelte.ts
│   │   ├── api.ts                   # API client with caching
│   │   └── types.ts                 # TypeScript definitions
│   ├── App.svelte
│   └── main.ts
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── svelte.config.js
```

## Development

### Prerequisites

- [Bun](https://bun.sh/) v1.0+

### Install Dependencies

```bash
bun install
```

### Start Development Server

```bash
bun run dev
```

The app will be available at `http://localhost:5173`.

### Type Checking

```bash
bun run check
```

### Build for Production

```bash
bun run build
```

The output will be in the `dist/` directory.

### Preview Production Build

```bash
bun run preview
```

## Configuration

### API Endpoint

The API base URL is configured in `src/lib/api.ts`:

```typescript
const API_BASE = "https://gsat-vocab-api.vic0407lu.workers.dev";
```

## Deployment

### Cloudflare Pages

```bash
# Build and deploy
bun run build
wrangler pages deploy dist --project-name=gsat-vocab
```

### Alternative Hosting

Since this builds to static files, you can deploy to:
- Netlify
- Vercel
- GitHub Pages
- AWS S3 + CloudFront
- Any static hosting service

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES2020+ features required
- LocalStorage support required

## Architecture Notes

### State Management

Uses Svelte 5 runes (`$state`, `$derived`, `$effect`) for reactive state:
- Global stores export getter functions to access reactive state
- State mutations through dedicated functions
- Derived values computed automatically

### Virtual Scrolling Implementation

The `WordList.svelte` component implements virtual scrolling:
1. Calculates visible range based on scroll position
2. Only renders items within the visible range + overscan
3. Uses absolute positioning within a spacer div
4. Handles both list and grid modes

### API Caching

The API client includes a simple in-memory cache with TTL to reduce redundant network requests.