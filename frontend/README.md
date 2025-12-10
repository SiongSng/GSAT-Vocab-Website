# GSAT Vocabulary Website - Frontend

This directory contains the frontend application for the GSAT Vocabulary Learning Platform.

## Directory Structure

```
frontend/
├── index.html                    # Main HTML file
├── app.js                        # Application logic and state management
└── README.md                     # This file
```

## Features

### Browse Mode
- Search and filter vocabulary
- View word details with definitions and examples
- Listen to pronunciation audio
- Grid or list view options

### Flashcard Mode
- Interactive card flipping
- Mark words as mastered or needs review
- Audio playback for pronunciation practice
- Progress tracking with localStorage

### Quiz Mode

#### Multiple Choice
- Definition to word matching
- Word to definition matching

#### Spelling Test
- Listen to audio and spell the word
- See definition and spell the word

#### Fill-in-the-Blank
- Complete sentences with correct words
- Context-based learning

## Configuration

### API Endpoint

Edit `app.js` to configure the API base URL:

```javascript
const CONFIG = {
    API_BASE: 'https://your-worker-url.workers.dev',
    AUDIO_ENABLED: true,
    AUDIO_PREFETCH_COUNT: 2
};
```

## Development

### Local Development

Since this is a static site, you can serve it with any local server:

```bash
# Using Python
python -m http.server 8000

# Using Node.js http-server
npx http-server

# Using PHP
php -S localhost:8000
```

Then open `http://localhost:8000` in your browser.

### File Structure

```javascript
// app.js structure:
- CONFIG                  // Application configuration
- AppLocks                // Request locks to prevent duplicate calls
- AppState                // Global application state
  - currentMode           // browse | flashcard | quiz
  - vocabIndex           // Vocabulary index data
  - searchIndex          // Search index data
  - currentFilters       // Active filters
  - browseState          // Browse mode state
  - flashcardState       // Flashcard mode state
  - quizState            // Quiz mode state
- API functions           // Data fetching functions
- UI functions            // DOM manipulation functions
- Event handlers          // User interaction handlers
```

## Deployment

### Cloudflare Pages

```bash
# Build (from project root)
./deploy.sh pages

# Or manually
wrangler pages deploy frontend --project-name=gsat-vocab
```

### Alternative Hosting

Since this is a static site, you can deploy to:
- Netlify
- Vercel
- GitHub Pages
- AWS S3 + CloudFront
- Any static hosting service

Just deploy the contents of the `frontend/` directory.

## Technology Stack

- **Vanilla JavaScript** - No frameworks, pure JS
- **Tailwind CSS** - Utility-first CSS (via CDN)
- **HTML5 Audio API** - Audio playback
- **LocalStorage API** - Progress persistence
- **Fetch API** - API communication

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES6+ features required
- LocalStorage support required
- Audio API support required

## Features Implementation

### Data Loading

1. Initial load fetches vocabulary index
2. Search index loaded on demand
3. Word details loaded lazily on click
4. Audio files loaded on demand with prefetching

### State Management

All state stored in `AppState` object:
- No external state management library
- Direct DOM manipulation
- LocalStorage for persistence

### Performance Optimizations

- Lazy loading of word details
- Audio prefetching for smooth flashcard experience
- Debounced search input
- Cached API responses
- Incremental rendering for large lists

### Audio Handling

- Automatic prefetching in flashcard mode
- Play/pause controls
- Error handling for missing audio
- Fallback to text-to-speech (future)

## User Data

All user progress is stored locally using `localStorage`:

```javascript
// Flashcard progress
localStorage.getItem('flashcardProgress')

// Quiz results
localStorage.getItem('quizResults')

// User preferences
localStorage.getItem('userPreferences')
```

No server-side user data storage in current version.

## Future Enhancements

- User authentication
- Cloud sync for progress
- Offline support with Service Workers
- Progressive Web App (PWA)
- Mobile app version
- Advanced analytics
- Spaced repetition algorithm
- Social features (leaderboards, sharing)

## Notes

- All UI text is in Traditional Chinese
- API responses include both English and Chinese
- Audio files are served from Cloudflare R2
- No build process required (vanilla JS)
- Mobile-responsive design