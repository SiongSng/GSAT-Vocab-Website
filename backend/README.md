# GSAT Vocabulary Website - Backend

This directory contains all backend-related code including API services and data processing scripts.

## Directory Structure

```
backend/
├── api/                          # Cloudflare Workers API
│   ├── worker-api.js            # API worker code
│   └── wrangler.toml            # Cloudflare Workers configuration
├── scripts/                      # Data processing scripts
│   ├── ceec_scraper.py          # PDF scraper from CEEC website
│   ├── extract_words.py         # Extract words and generate AI definitions
│   ├── filter_sentences.py      # Filter and clean sentences
│   ├── generate_polysemy.py     # Generate polysemy analysis
│   ├── generate_tts_audio.py    # Generate word pronunciation audio
│   ├── generate_featured_sentence_audio.py  # Generate sentence audio
│   ├── split_vocab_details.py   # Split data into chunks
│   ├── upload_vocab_details.py  # Upload data to R2
│   ├── r2_up.py                 # Upload audio files to R2
│   └── temp_upload_sentences.py # Temporary upload script
└── requirements.txt              # Python dependencies
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (for Wrangler CLI)
- OpenAI API Key
- Cloudflare account

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or venv\Scripts\activate  # Windows

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Install Wrangler CLI
npm install -g wrangler
```

### Environment Variables

Create `.env` file in project root:

```bash
OPENAI_API_KEY=sk-proj-your-key-here
R2_ACCOUNT_ID=your-r2-account-id
R2_ACCESS_KEY_ID=your-r2-access-key
R2_SECRET_ACCESS_KEY=your-r2-secret-key
```

## Data Processing Pipeline

### 1. Scrape PDF Files

```bash
cd backend/scripts
python ceec_scraper.py
```

Downloads CEEC English exam PDFs to `ceec_english_papers/`.

### 2. Extract Words and Generate Definitions

```bash
python extract_words.py
```

- Extracts text from PDFs
- Performs NLP analysis with spaCy
- Generates AI definitions using OpenAI API
- Outputs: `data/output/vocab_data.json`

### 3. Generate Audio

```bash
# Generate word pronunciation
python generate_tts_audio.py

# Generate sentence audio
python generate_featured_sentence_audio.py
```

Outputs: `data/output/tts_audio/*.mp3`

### 4. Split Data

```bash
python split_vocab_details.py
```

Splits large JSON into:
- `vocab_index.json` - Lightweight index
- `search_index.json` - Search index
- `vocab_details/*.json` - Individual word details

### 5. Upload to R2

```bash
# Upload audio files
python r2_up.py

# Upload data files
python upload_vocab_details.py
```

## API Deployment

### Configure Wrangler

Edit `api/wrangler.toml` with your settings.

### Create KV Namespace

```bash
wrangler kv:namespace create "VOCAB_CACHE"
```

Update the namespace ID in `wrangler.toml`.

### Deploy Worker

```bash
cd api
wrangler deploy
```

## API Endpoints

- `GET /api/vocab/index` - Get vocabulary index
- `GET /api/vocab/detail/:lemma` - Get word details
- `GET /api/vocab/search?q=word` - Search words
- `GET /api/vocab/random` - Get random word
- `GET /api/quiz/generate` - Generate quiz questions
- `GET /api/search-index` - Get search index
- `GET /audio/:filename` - Get audio file

## Technology Stack

### Data Processing
- **Python 3.10+**
- **pdfplumber** - PDF text extraction
- **spaCy** - NLP processing
- **OpenAI API** - AI definitions and TTS
- **boto3** - R2 upload

### API
- **Cloudflare Workers** - Serverless API
- **Cloudflare R2** - Object storage
- **Cloudflare KV** - Caching layer

## Notes

- All scripts should be run from the `backend/scripts` directory
- Data output goes to `data/output/`
- Audio files are uploaded incrementally
- API uses caching to improve performance