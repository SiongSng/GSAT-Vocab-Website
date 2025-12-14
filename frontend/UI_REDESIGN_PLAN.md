# GSAT Vocab Website UI/UX Redesign Plan

> Leveraging the new comprehensive vocabulary data structure for enhanced learning experience

---

## 🎯 Design Vision & Requirements

> **IMPORTANT**: This section defines the core design philosophy. All implementations MUST adhere to these principles.

### Product Owner's Vision

The new vocabulary data structure enables a complete UI/UX overhaul with the following capabilities:

#### Data-Driven Features

1. **Rich Filtering & Sorting**: CEEC vocabulary levels, phrase/pattern types, POS filters, ML-predicted importance scores, and legacy weighted scores for more meaningful sorting than simple occurrence counts.

2. **Multi-Sense Word Details**: Present different meanings via tabs or similar patterns, with dedicated examples and real exam cases for each sense. Include:
   - Tag labels for various attributes
   - Real exam sentences with source citations
   - LLM-generated learning sentences
   - Extensive statistics visualization
   - Root analysis and memory strategies
   - Confusion notes with distractor explanations
   - Synonyms, antonyms, and derived forms

3. **Global Word Lookup**: Any word anywhere in the app should be clickable to open a detail view:
   - **Desktop**: Heptabase-style sidebar panel
   - **Mobile**: Bottom sheet modal

4. **Sense-Aware SRS**: Flashcards keyed by `lemma + sense_id` for effective multi-meaning learning:
   - Primary meaning shown first
   - Forgetting curves tracked per sense, not just per word
   - Smart presentation of relevant meanings with random real examples + LLM sentences
   - All words in examples are clickable for extended learning
   - Reserve space for future learning history charts (line/bar graphs)

5. **ML-Powered Recommendations**: Use trained ML model scores to intelligently order flashcards, eliminating the need for users to manually set frequency ranges.

6. **Adaptive Quiz System**: Different quiz types based on forgetting curve state:
   - Recognition (multiple choice)
   - Reverse recognition (Chinese → English)
   - Fill-in-blank using real exam sentences
   - Spelling tests
   - Quiz results update SRS forgetting curve data

### Design Principles

1. **Heptabase/Notion Aesthetic**: Clean, minimal, content-focused design consistent with the existing design system (`DESIGN_SYSTEM.md`)

2. **No Emojis**: Use proper SVG icons (Heroicons) instead of emojis in production UI

3. **Clean Tag Labels**: Follow mainstream patterns (Linear, Notion, Raycast) - inline tags with middle dot separators, minimal visual weight

4. **Filter Explanations**: Each filter option should include brief descriptions explaining what the data means

5. **Responsive First**: Optimize layouts for mobile, tablet (iPad), and desktop with device-appropriate patterns

6. **Learning-Centered**: Every UI decision should support effective vocabulary acquisition and exam preparation

### Technical Requirements

#### URL-Based Routing (Critical)

The current implementation lacks URL path state management, which severely impacts user experience. **This must be implemented**:

```
/                       → Browse view (word list)
/word/:lemma            → Word detail view
/word/:lemma/:senseId   → Specific sense view
/flashcard              → SRS flashcard dashboard
/flashcard/session      → Active study session
/quiz                   → Quiz setup
/quiz/session           → Active quiz session
/stats                  → Learning statistics (future)
```

**Benefits of URL routing:**
- Browser back/forward navigation works correctly
- Shareable links to specific words
- Bookmarkable views
- Better mobile experience (system back gesture)
- SEO potential for public word pages

**Implementation approach:**
- Use a lightweight client-side router (e.g., `svelte-spa-router` or custom hash-based routing)
- Sync URL state with app stores
- Handle deep links on initial load
- Preserve scroll position on navigation

---

## Table of Contents

0. [Design Vision & Requirements](#-design-vision--requirements)
1. [Data Architecture](#1-data-architecture)
2. [Data Loading & Caching](#2-data-loading--caching)
3. [Browse View Redesign](#3-browse-view-redesign)
4. [Word Detail Panel](#4-word-detail-panel)
5. [Global Word Lookup](#5-global-word-lookup)
6. [SRS Flashcard System](#6-srs-flashcard-system)
7. [Quiz/Practice System](#7-quizpractice-system)
8. [Responsive Design Strategy](#8-responsive-design-strategy)
9. [URL Routing](#9-url-routing)
10. [Implementation Phases](#10-implementation-phases)

---

## 1. Data Architecture

### 1.1 New Data Models (Frontend)

Based on the backend `VocabEntry` and related models, create TypeScript interfaces:

```typescript
// types/vocab-v2.ts

interface VocabEntry {
  lemma: string;
  type: "word" | "phrase" | "pattern";
  pos: string[];
  level: number | null; // CEEC official level 1-6
  tier: VocabTier;
  in_official_list: boolean;
  senses: VocabSense[];
  frequency: FrequencyData;
  confusion_notes: ConfusionNote[];
  root_info: RootInfo | null;
  pattern_info: PatternInfo | null;
  synonyms: string[] | null;
  antonyms: string[] | null;
  derived_forms: string[] | null;
}

type VocabTier = "tested" | "translation" | "phrase" | "pattern" | "basic";

interface VocabSense {
  sense_id: string;
  pos: string;
  zh_def: string;
  en_def: string;
  tested_in_exam: boolean;
  examples: ExamExample[];
  generated_example: string;
}

interface ExamExample {
  text: string;
  source: SourceInfo;
}

interface SourceInfo {
  year: number;
  exam_type: string;
  section: string;
  question_number?: number;
}

interface FrequencyData {
  total_occurrences: number;
  tested_count: number;
  year_spread: number;
  weighted_score: float;
  ml_score: float | null;
}

interface ConfusionNote {
  confused_with: string;
  distinction: string;
  memory_tip: string;
}

interface RootInfo {
  root_breakdown: string | null;
  memory_strategy: string;
}

interface PatternInfo {
  pattern_type: "collocation" | "phrasal_verb" | "idiom" | "grammar";
  display_name: string | null;
  structure: string;
}
```

### 1.2 Index Structure for Fast Lookup

Create a lightweight index for the word list (separate from full data):

```typescript
interface VocabIndexItem {
  lemma: string;
  type: "word" | "phrase" | "pattern";
  pos: string[];
  level: number | null;
  tier: VocabTier;
  in_official_list: boolean;
  sense_count: number;
  zh_preview: string; // First sense zh_def truncated
  importance_score: number; // Computed: ml_score ?? (weighted_score / 30)
  tested_count: number;
  year_spread: number;
}
```

---

## 2. Data Loading & Caching

### 2.1 Version Management

Create `public/data/version.json`:

```json
{
  "version": "2024.01.15",
  "vocab_hash": "abc123...",
  "generated_at": "2024-01-15T10:30:00Z",
  "entry_count": 5234
}
```

### 2.2 IndexedDB Schema

```typescript
// Database: gsat-vocab-v2
// Version: 1

interface VocabDB {
  // Object Stores:
  entries: VocabEntry;        // keyPath: "lemma"
  metadata: { key: string; value: unknown };
  srs_cards: SRSCardV2;       // keyPath: ["lemma", "sense_id"]
  review_logs: SRSReviewLog;  // keyPath: ["lemma", "sense_id", "review"]
}

// Indexes on entries:
// - by_level: level
// - by_tier: tier
// - by_type: type
// - by_importance: importance_score (computed)
```

### 2.3 Loading Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        App Initialization                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Check localStorage for cached version                        │
│     └─ Key: "gsat_vocab_version"                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Fetch /data/version.json (small, always fresh)              │
└─────────────────────────────────────────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
              ▼                                   ▼
┌─────────────────────────┐         ┌─────────────────────────────┐
│ Version matches:        │         │ Version differs:            │
│ Load from IndexedDB     │         │ Show loading UI             │
│ App ready immediately   │         │ Stream vocab.json.gz        │
└─────────────────────────┘         │ Decompress with pako        │
                                    │ Batch insert to IndexedDB   │
                                    │ Update version in storage   │
                                    └─────────────────────────────┘
```

### 2.4 Loading Progress UI

Design a full-screen loading overlay (only on first load or update):

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                         [GSAT Logo]                             │
│                                                                 │
│                    正在載入詞彙資料庫...                          │
│                                                                 │
│     ┌─────────────────────────────────────────────────────┐    │
│     │████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│    │
│     └─────────────────────────────────────────────────────┘    │
│                         45% (2,345 / 5,234)                     │
│                                                                 │
│              首次載入需要約 10-15 秒，之後將即時啟動              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Component styling follows design system:
- Background: `bg-surface-page`
- Progress bar track: `bg-surface-secondary`
- Progress bar fill: `bg-accent` with subtle gradient
- Text: `text-content-secondary` for labels, `text-content-tertiary` for hints

---

## 3. Browse View Redesign

### 3.1 Enhanced Filter Sidebar

Each filter includes a brief explanation to help users understand the data:

```
┌──────────────────────────────────────────┐
│  篩選條件                         [重設]  │
├──────────────────────────────────────────┤
│                                          │
│  搜尋單字                                 │
│  ┌────────────────────────────────────┐  │
│  │ Search...                    [icon] │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ─────────────────────────────────────── │
│                                          │
│  詞彙等級                           [?]   │
│  大考中心官方難度分級，1-2 基礎、           │
│  3-4 中級、5-6 進階                       │
│                                          │
│  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐   │
│  │ 1 │ │ 2 │ │ 3 │ │ 4 │ │ 5 │ │ 6 │   │
│  └───┘ └───┘ └───┘ └───┘ └───┘ └───┘   │
│                                          │
│  ─────────────────────────────────────── │
│                                          │
│  詞彙類型                                 │
│  ┌────────┐ ┌────────┐ ┌────────┐       │
│  │  單字  │ │  片語  │ │  句型  │        │
│  └────────┘ └────────┘ └────────┘       │
│                                          │
│  ─────────────────────────────────────── │
│                                          │
│  詞性                                     │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │ 名詞 │ │ 動詞 │ │ 形容詞│ │ 副詞 │   │
│  └──────┘ └──────┘ └──────┘ └──────┘   │
│                                          │
│  ─────────────────────────────────────── │
│                                          │
│  考試重要性                         [?]   │
│  ML 模型預測未來一年考試出現機率，          │
│  綜合歷年出題頻率與語言學特徵              │
│                                          │
│  [●─────────────────────────────────○]   │
│  低                                  高   │
│                                          │
│  ─────────────────────────────────────── │
│                                          │
│  進階篩選                          [展開]  │
│                                          │
│  ☐ 僅顯示大考中心詞彙表                    │
│     官方公布的 7000 單字範圍               │
│                                          │
│  ☐ 僅顯示曾出現在考題的詞彙                │
│     作為答案、選項或翻譯關鍵字             │
│                                          │
│  ☐ 排除專有名詞                           │
│                                          │
└──────────────────────────────────────────┘
```

**Filter Data Explanations:**

| Filter | Data Source | Description |
|--------|-------------|-------------|
| 詞彙等級 | `level` (1-6) | CEEC official difficulty level. `null` for words not in official list. |
| 詞彙類型 | `type` | `word` (single word), `phrase` (multi-word), `pattern` (grammar structure) |
| 考試重要性 | `frequency.ml_score` | ML-predicted probability (0-1) of appearing in future exams. Falls back to `weighted_score / 30` when null. |
| 大考詞彙表 | `in_official_list` | Whether included in CEEC's official vocabulary list |
| 曾出考題 | `tier === 'tested'` | Appeared as answer, distractor, or translation keyword |

### 3.2 Sort Options

Add dropdown in results header:

```
┌────────────────────────────────────────────────────────────┐
│  找到 1,234 個符合條件的單詞          排序: [▼ 重要性優先]  │
├────────────────────────────────────────────────────────────┤
│                                       ┌─────────────────┐  │
│                                       │ ● 重要性優先    │  │
│                                       │   出現次數      │  │
│                                       │   年份分布      │  │
│                                       │   字母順序 A-Z  │  │
│                                       │   字母順序 Z-A  │  │
│                                       │   等級 (低→高)  │  │
│                                       │   等級 (高→低)  │  │
│                                       └─────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### 3.3 Word List Item (Clean Tag Label Design)

Following mainstream design patterns (Linear, Notion, Raycast), the word list item uses compact inline tags:

**Default State:**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  abandon                                                        │
│  v. ・ L3 ・ 官方                                                │
│  放棄；拋棄                                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Hover/Active State (show more context):**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  abandon                                              92% [bar] │
│  v. ・ L3 ・ 官方                                                │
│  放棄；拋棄                                                      │
│  23次 ・ 8年 ・ 5題                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Design Principles:**

1. **Primary info always visible**: lemma, POS, level, zh_preview
2. **Secondary info on interaction**: importance score, frequency stats
3. **Inline separator**: Use `・` (middle dot) for tag separation
4. **Minimal visual weight**: No borders on tags, rely on typography hierarchy

**Tag Styling:**

| Tag | Style | Example |
|-----|-------|---------|
| POS | `text-xs text-content-tertiary` | `v.` `n.` `adj.` |
| Level | `text-xs text-content-tertiary` | `L1` - `L6` |
| Official | `text-xs text-accent` (only if true) | `官方` |
| Importance | Tiny progress bar, `bg-accent` fill | `[████░░] 92%` |
| Stats | `text-xs text-content-tertiary` | `23次 ・ 8年 ・ 5題` |

**Stats abbreviation:**
- `23次` = total_occurrences (總出現次數)
- `8年` = year_spread (跨越年份數)
- `5題` = tested_count (出現在考題次數)

---

## 4. Word Detail Panel

### 4.1 Multi-Sense Tab Interface

```
┌─────────────────────────────────────────────────────────────────┐
│  ← 返回                                               [speaker] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  run                                                            │
│  L2 ・ 官方 ・ 重要 95%                                          │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 涵義1 (v.) │ 涵義2 (v.) │ 涵義3 (n.) │ 涵義4 (n.) │ +3   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  定義                                                   │   │
│  │                                                         │   │
│  │  跑步；奔跑                                              │   │
│  │  To move swiftly on foot                                │   │
│  │                                                         │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │                                                         │   │
│  │  真實考題例句                              [考題來源▼]   │   │
│  │                                                         │   │
│  │  "He **runs** every morning to stay healthy."           │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ 111學測 ・ 閱讀測驗 ・ 第15題          [speaker] │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  │  "She decided to **run** for class president."          │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ 108指考 ・ 克漏字 ・ 第23題            [speaker] │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │                                                         │   │
│  │  學習例句 (AI 生成)                                     │   │
│  │                                                         │   │
│  │  "The children **run** happily in the park every        │   │
│  │   afternoon after school."                              │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Note: `[speaker]` represents the volume/audio SVG icon from the design system.

### 4.2 Expandable Sections

Below the sense tabs, collapsible sections:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  統計數據                                           [chevron ▼] │
│  ├─────────────────────────────────────────────────────────────┤
│  │                                                             │
│  │  總出現次數: 156 次                                         │
│  │  ├── 考題答案: 12 次                                        │
│  │  ├── 考題選項: 23 次                                        │
│  │  └── 文章段落: 121 次                                       │
│  │                                                             │
│  │  年份分布 (2015-2024)                                       │
│  │  ┌──────────────────────────────────────────────────────┐  │
│  │  │  █     █  ██  █  ███ ██  █  ██  █                    │  │
│  │  │ '15  '16 '17 '18 '19 '20 '21 '22 '23 '24             │  │
│  │  └──────────────────────────────────────────────────────┘  │
│  │                                                             │
│  │  詞性分布                                                   │
│  │  VERB  ████████████████████░░░░░░  78%                     │
│  │  NOUN  ██████░░░░░░░░░░░░░░░░░░░░  22%                     │
│  │                                                             │
│  └─────────────────────────────────────────────────────────────┘
│                                                                 │
│  字根分析                                           [chevron ▼] │
│  ├─────────────────────────────────────────────────────────────┤
│  │                                                             │
│  │  run (古英語 rinnan)                                        │
│  │                                                             │
│  │  記憶策略                                                   │
│  │  想像一個人在「潤」滑的跑道上快速奔跑，                      │
│  │  「run」發音接近「潤」，跑步時身體會出汗變潤。               │
│  │                                                             │
│  └─────────────────────────────────────────────────────────────┘
│                                                                 │
│  易混淆詞彙                                         [chevron ▼] │
│  ├─────────────────────────────────────────────────────────────┤
│  │                                                             │
│  │  run vs. ran vs. running                                    │
│  │  ┌─────────────────────────────────────────────────────┐   │
│  │  │ run 是原形動詞，ran 是過去式，running 是現在分詞      │   │
│  │  └─────────────────────────────────────────────────────┘   │
│  │  記住：run-ran-run (過去分詞同原形)                         │
│  │                                                             │
│  │  run vs. jog                                                │
│  │  ┌─────────────────────────────────────────────────────┐   │
│  │  │ run 泛指跑步，jog 特指慢跑健身                        │   │
│  │  └─────────────────────────────────────────────────────┘   │
│  │                                                             │
│  └─────────────────────────────────────────────────────────────┘
│                                                                 │
│  相關詞彙                                           [chevron ▼] │
│  ├─────────────────────────────────────────────────────────────┤
│  │                                                             │
│  │  同義詞                                                     │
│  │  ┌──────┐ ┌──────┐ ┌───────┐ ┌────────┐                   │
│  │  │ dash │ │ race │ │ sprint│ │ hurry  │                   │
│  │  └──────┘ └──────┘ └───────┘ └────────┘                   │
│  │                                                             │
│  │  反義詞                                                     │
│  │  ┌──────┐ ┌──────┐ ┌───────┐                              │
│  │  │ walk │ │ stop │ │ stand │                              │
│  │  └──────┘ └──────┘ └───────┘                              │
│  │                                                             │
│  │  衍生詞                                                     │
│  │  ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐          │
│  │  │ runner │ │ runway │ │ running │ │ runaway  │          │
│  │  └────────┘ └────────┘ └─────────┘ └──────────┘          │
│  │                                                             │
│  └─────────────────────────────────────────────────────────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Section Header Icons** (use Heroicons or similar):
- 統計數據: `chart-bar` icon
- 字根分析: `puzzle-piece` icon  
- 易混淆詞彙: `exclamation-triangle` icon
- 相關詞彙: `link` icon

### 4.3 Component Tokens

Following design system:

| Element | Style |
|---------|-------|
| Sense tabs | `bg-surface-secondary` inactive, `bg-accent-soft text-accent` active |
| Section headers | `text-sm font-semibold text-section-header` |
| Source citations | `bg-surface-page rounded-md border border-border` |
| Related word chips | `bg-surface-page text-content-secondary hover:bg-surface-hover cursor-pointer` |
| Exam marker | `bg-srs-good/10 text-srs-good` when tested in exam |

---

## 5. Global Word Lookup

### 5.1 Click-to-Lookup Feature

Any word in the app (in examples, definitions, etc.) can be clicked to open a quick lookup.

**Desktop**: Heptabase-style side panel
```
┌─────────────────────────────────────────┬───────────────────────┐
│                                         │                       │
│                                         │  Quick Lookup         │
│        Main Content Area                │                       │
│                                         │  abandon              │
│                                         │  v. ・ L3             │
│   "He decided to **abandon** his..."    │                       │
│              ↑                          │  放棄；拋棄            │
│         (clicked)                       │                       │
│                                         │  [查看完整資訊 →]      │
│                                         │                       │
└─────────────────────────────────────────┴───────────────────────┘
```

**Mobile/Tablet**: Bottom sheet modal
```
┌─────────────────────────────────────────┐
│                                         │
│        Main Content Area                │
│                                         │
│   "He decided to **abandon** his..."    │
│              ↑                          │
│         (clicked)                       │
│                                         │
├─────────────────────────────────────────┤
│  ━━━━━━━━━━━━━  (drag handle)           │
│                                         │
│  abandon                      [speaker] │
│  v. ・ L3                               │
│                                         │
│  放棄；拋棄                               │
│  To give up completely                  │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │      查看完整資訊                │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

The Quick Lookup panel uses the same inline tag style (`v. ・ L3`) as the Word List items for visual consistency.

### 5.2 Implementation Strategy

```typescript
// Component: ClickableWord.svelte
// Wraps text and makes vocabulary words clickable

interface Props {
  text: string;
  onWordClick: (lemma: string) => void;
}

// Use a trie or set of all lemmas to identify clickable words
// Render spans with hover effect for recognized words
```

### 5.3 Word Lookup Store

```typescript
// stores/word-lookup.svelte.ts

interface WordLookupState {
  isOpen: boolean;
  lemma: string | null;
  position: "sidebar" | "bottom-sheet";
  entry: VocabEntry | null;
  isLoading: boolean;
}

// Functions:
// - openLookup(lemma: string)
// - closeLookup()
// - navigateToFullDetail() // switches to browse view with word selected
```

---

## 6. SRS Flashcard System

### 6.1 Sense-Aware Card Model

```typescript
// types/srs-v2.ts

interface SRSCardV2 {
  lemma: string;
  sense_id: string; // e.g., "run_v_1" for first verb sense
  
  // FSRS fields
  due: Date;
  stability: number;
  difficulty: number;
  elapsed_days: number;
  scheduled_days: number;
  reps: number;
  lapses: number;
  state: State;
  last_review?: Date;
}

// One lemma can have multiple cards (one per sense)
// Primary sense card is created first, others unlocked progressively
```

### 6.2 Smart Card Selection Algorithm

The algorithm balances **learning efficiency** and **exam relevance**:

```
┌─────────────────────────────────────────────────────────────────┐
│              Card Selection Algorithm (Priority Order)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PHASE 1: Urgent Reviews (Memory Decay Prevention)              │
│  ──────────────────────────────────────────────────             │
│  1. Relearning cards (failed recently, high priority)           │
│  2. Overdue review cards (sorted by days overdue)               │
│  3. Learning cards due now                                      │
│                                                                 │
│  PHASE 2: New Card Introduction                                 │
│  ──────────────────────────────────────────────────             │
│  New cards sorted by composite score:                           │
│                                                                 │
│    score = (ml_score × 0.6) + (recency_boost × 0.25)            │
│          + (level_match × 0.15)                                 │
│                                                                 │
│  Where:                                                         │
│  • ml_score: ML-predicted exam probability (0-1)                │
│  • recency_boost: Higher for words tested in recent 3 years     │
│  • level_match: Matches user's target level preference          │
│                                                                 │
│  PHASE 3: Interleaving Strategy                                 │
│  ──────────────────────────────────────────────────             │
│  • Pattern: 2 review → 1 new → 2 review → 1 new...              │
│  • Spacing: Synonyms/antonyms/confusables separated by 5+ cards │
│  • Variety: Mix different POS and levels within session         │
│                                                                 │
│  PHASE 4: Multi-Sense Progression                               │
│  ──────────────────────────────────────────────────             │
│  • Primary sense (most common/tested) introduced first          │
│  • Secondary senses unlock when:                                │
│    - Primary sense stability > 10 days, OR                      │
│    - User explicitly enables "all senses" mode                  │
│  • tested_in_exam senses prioritized over non-tested            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Learning Psychology Principles Applied:**

| Principle | Implementation |
|-----------|----------------|
| Spaced Repetition | FSRS algorithm with optimized intervals |
| Interleaving | Mix different word types and difficulty levels |
| Desirable Difficulty | Gradually introduce harder words as mastery grows |
| Context Variation | Show different example sentences each review |
| Active Recall | Flashcard format forces retrieval before reveal |
| Elaborative Encoding | Confusion notes and root analysis deepen memory |

**Exam-Focused Optimizations:**

1. **High-yield words first**: ML model trained on historical exam patterns
2. **Recent trends weighted**: Words from last 3 years get 25% boost
3. **Distractor awareness**: Words that appeared as wrong answers are flagged
4. **Section coverage**: Ensure exposure to vocab from all exam sections

### 6.3 Enhanced Flashcard UI

**Front of Card**:
```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────┐                                        [speaker]   │
│  │Learning │                                                    │
│  └─────────┘                                                    │
│                                                                 │
│                                                                 │
│                                                                 │
│                         abandon                                 │
│                           verb                                  │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
│                      點擊翻牌查看定義                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Note: `[speaker]` represents an SVG icon from the design system, not an emoji.

**Back of Card** (Enhanced):
```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────┐                                        [speaker]   │
│  │Learning │                                                    │
│  └─────────┘                                                    │
│                                                                 │
│                         abandon                                 │
│                        ┌─────┐                                  │
│                        │ v.  │ 涵義 1/3                         │
│                        └─────┘                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  放棄；拋棄                                                      │
│  To give up completely or leave behind                          │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  真實考題                                                       │
│  "Many people **abandon** their New Year's resolutions          │
│   within the first month."                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 112學測・詞彙題・第5題                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  學習例句                                                       │
│  "The sailor had to **abandon** ship when it started            │
│   to sink rapidly."                                             │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌──────────┬──────────┬──────────┬──────────┐                 │
│  │  重來    │   困難   │   良好   │   簡單   │                 │
│  │  <1m    │   <10m   │   1d     │   4d     │                 │
│  └──────────┴──────────┴──────────┴──────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.4 Clickable Words in Examples

All words in example sentences are interactive:
- Highlight on hover
- Click opens quick lookup (see Section 5)
- Prevents confusion when reading examples

### 6.5 Study Dashboard Redesign

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  今日學習                                                       │
│                                                                 │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐     │
│  │    12      │     8       │     45      │     3       │     │
│  │   待複習    │   學習中    │   新卡片    │   重新學習   │     │
│  │    [●]     │     [●]     │     [●]     │     [●]     │     │
│  │  srs-again │  srs-hard   │  srs-easy   │  srs-hard   │     │
│  └─────────────┴─────────────┴─────────────┴─────────────┘     │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  學習進度                                                       │
│                                                                 │
│  本週學習                                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  50 │     █                                              │  │
│  │  40 │  █  █     █                                        │  │
│  │  30 │  █  █  █  █  █                                     │  │
│  │  20 │  █  █  █  █  █  █                                  │  │
│  │  10 │  █  █  █  █  █  █  █                               │  │
│  │   0 ├──────────────────────────                          │  │
│  │      Mon Tue Wed Thu Fri Sat Sun                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │                     開始學習                             │   │
│  │                   約 65 張卡片                           │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  學習設定                                                [展開] │
│                                                                 │
│  智慧推薦模式                                            [開啟] │
│     根據 ML 模型自動安排最佳學習順序                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Color indicators** use design system SRS tokens (not emojis):
- 待複習: `bg-srs-again` (red dot)
- 學習中: `bg-srs-hard` (orange dot)  
- 新卡片: `bg-srs-easy` (blue dot)
- 重新學習: `bg-srs-hard` (orange dot)

### 6.6 Session Complete Screen

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                      [checkmark icon]                           │
│                         今日完成！                              │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│               學習時間: 12 分鐘                                 │
│               完成卡片: 45 張                                   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                                                        │    │
│  │   正確率分布                                           │    │
│  │                                                        │    │
│  │   簡單  ████████████████░░░░░░░░  42%  (19張)          │    │
│  │   良好  ██████████████████████░░  58%  (26張)          │    │
│  │   困難  ████░░░░░░░░░░░░░░░░░░░░  12%  (5張)           │    │
│  │   重來  ██░░░░░░░░░░░░░░░░░░░░░░   7%  (3張)           │    │
│  │                                                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  需要加強的單字                                                 │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                       │
│  │ abandon  │ │ acquire  │ │ adequate │                       │
│  └──────────┘ └──────────┘ └──────────┘                       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    返回首頁                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  繼續學習更多                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Progress bar colors** follow SRS tokens:
- 簡單: `bg-srs-easy` (blue)
- 良好: `bg-srs-good` (green)
- 困難: `bg-srs-hard` (orange)
- 重來: `bg-srs-again` (red)

---

## 7. Quiz/Practice System

### 7.1 Adaptive Quiz Types

Quiz types are selected based on **SRS state** and **mastery level**, using real example sentences from the data:

| SRS State | Mastery | Quiz Type | Description | Data Source |
|-----------|---------|-----------|-------------|-------------|
| New/Learning | Low | Recognition | 英文單字 → 選中文定義 | `sense.zh_def` as correct, other senses as distractors |
| Learning | Low | Reverse | 中文定義 → 選英文單字 | Use `confusion_notes.confused_with` as distractors |
| Review (1-7d) | Medium | Fill-blank | 例句克漏字填空 | `sense.examples[].text` with lemma blanked |
| Review (7-30d) | Medium-High | Spelling | 聽音拼寫 / 看定義拼寫 | TTS audio + `sense.zh_def` as prompt |
| Review (30d+) | High | Context | 選擇正確例句用法 | Mix `generated_example` with modified wrong versions |
| Any (flagged) | Weak | Distinction | 區分易混淆詞 | `confusion_notes` for word pairs |

**Fill-in-Blank Example Generation:**

```
Original: "Many people abandon their New Year's resolutions within the first month."
Quiz:     "Many people _______ their New Year's resolutions within the first month."
Hint:     (v.) 放棄；拋棄
Options:  [abandon] [absorb] [abolish] [abstract]  ← from confusion_notes or similar tier
```

**Spelling Quiz Variants:**

1. **Audio → Spell**: Play TTS, user types the word
2. **Definition → Spell**: Show zh_def + en_def, user types the word
3. **Sentence → Spell**: Show sentence with blank, user types missing word

### 7.2 Quiz Generation from Real Data

```typescript
interface QuizQuestionV2 {
  type: "recognition" | "reverse" | "fill_blank" | "spelling" | "context" | "distinction";
  lemma: string;
  sense_id: string;
  
  // Question content
  prompt: string;
  prompt_audio?: string;  // For listening questions
  sentence_context?: string;  // For fill-blank, shows the sentence
  hint?: string;  // Optional hint (POS, partial definition)
  
  // For choice questions
  options?: {
    label: string;
    value: string;
    is_distractor_from_exam?: boolean;
  }[];
  
  // For spelling/fill-blank
  correct: string;
  accept_variants?: string[];  // e.g., ["abandoned", "abandoning"] for fill-blank
  
  // Source info
  exam_context?: {
    sentence: string;
    source: SourceInfo;
  };
  
  // Post-answer content
  explanation?: {
    confusion_note?: ConfusionNote;
    memory_tip?: string;
    correct_usage: string;
  };
}
```

### 7.3 Quiz Difficulty Progression

The quiz system adapts difficulty based on cumulative performance:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Difficulty Ladder                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Level 1: Recognition (Passive Recall)                          │
│  ├─ See English word → Pick Chinese definition                  │
│  └─ 4 options, distractors from different meanings              │
│                                                                 │
│  Level 2: Reverse Recognition                                   │
│  ├─ See Chinese definition → Pick English word                  │
│  └─ 4 options, distractors from confusion_notes                 │
│                                                                 │
│  Level 3: Contextual Fill-in-Blank                              │
│  ├─ Real exam sentence with word blanked                        │
│  ├─ 4 options OR free-form typing                               │
│  └─ Accept inflected forms (run/ran/running)                    │
│                                                                 │
│  Level 4: Spelling (Active Production)                          │
│  ├─ Hear audio OR see definition → Type the word                │
│  ├─ Partial credit for close spellings                          │
│  └─ Show correct after 2 attempts                               │
│                                                                 │
│  Level 5: Sentence Completion                                   │
│  ├─ Complete sentence using correct word form                   │
│  ├─ Must choose correct tense/form                              │
│  └─ Uses generated_example sentences                            │
│                                                                 │
│  Level 6: Usage Distinction                                     │
│  ├─ "Which sentence uses 'abandon' correctly?"                  │
│  ├─ Tests nuanced understanding                                 │
│  └─ Uses confusion_notes.distinction for feedback               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Automatic Level Assignment:**

```typescript
function getQuizLevel(card: SRSCardV2): number {
  const { stability, reps, lapses } = card;
  
  // High lapse count = need more basic practice
  if (lapses >= 3) return 1;
  
  // New or unstable = recognition first
  if (stability < 1) return 1;
  if (stability < 3) return 2;
  if (stability < 7) return 3;
  if (stability < 21) return 4;
  if (stability < 60) return 5;
  
  return 6; // Mastered - test nuanced usage
}
```

### 7.3 Quiz UI (Recognition Example)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  練習模式                                    第 5 題 / 共 10 題  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  請選出 "abandon" 的正確中文定義：                               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  A. 吸收；接受                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  B. 放棄；拋棄                              [check icon] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  C. 承認；認可                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  D. 實現；完成                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**After answering (correct):**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    [check icon] 正確！                          │
│                    text-srs-good                                │
│                                                                 │
│  abandon                                                        │
│  放棄；拋棄                                                      │
│                                                                 │
│  這個單字曾出現在 112學測 詞彙題                                 │
│                                                                 │
│  "Many people **abandon** their New Year's resolutions..."      │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      下一題 →                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**After answering (incorrect):**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    [x icon] 再想想                              │
│                    text-srs-again                               │
│                                                                 │
│  你選了: 吸收；接受 (absorb)                                     │
│  正確答案: 放棄；拋棄 (abandon)                                  │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  區分技巧                                                       │
│                                                                 │
│  abandon vs. absorb                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ abandon 有「放棄」的意思，開頭 ab- 可聯想成「away」       │   │
│  │ absorb 是「吸收」，開頭 ab- + sorb 像是「吸附」          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      下一題 →                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.4 Quiz UI Examples

**Fill-in-Blank (using real exam sentence):**

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  練習模式                                    第 5 題 / 共 10 題  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  填入適當的單字：                                                │
│                                                                 │
│  "Many people _______ their New Year's resolutions              │
│   within the first month."                                      │
│                                                                 │
│  提示: (v.) 放棄；拋棄                                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  A. abandon                                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  B. absorb                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  C. abolish                                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  D. abstract                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  112學測・詞彙題                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Spelling Quiz:**

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  拼寫測驗                                    第 3 題 / 共 10 題  │
│  ━━━━━━━━━━━━━━━━░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  請拼出這個單字：                                                │
│                                                                 │
│                        [speaker icon]                           │
│                       點擊播放發音                               │
│                                                                 │
│  (v.) 放棄；拋棄                                                 │
│  To give up completely or leave behind                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  a b a n _ _ _                                          │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      確認答案                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.5 Quiz Settings

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  練習設定                                                       │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  題目來源                                                       │
│                                                                 │
│  ● 智慧推薦                                                     │
│    根據遺忘曲線自動選擇需要複習的單字                            │
│                                                                 │
│  ○ 今日學習                                                     │
│    複習今天在 Flashcard 學過的單字                               │
│                                                                 │
│  ○ 困難單字                                                     │
│    按錯次數較多或標記為困難的單字                                │
│                                                                 │
│  ○ 自訂範圍                                                     │
│    手動選擇等級、詞性或特定單字                                  │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  題型 (智慧推薦會自動調整)                                       │
│                                                                 │
│  ☑ 選擇題 (英→中)       適合初學                                │
│  ☑ 選擇題 (中→英)       適合初學                                │
│  ☑ 克漏字填空           使用真實考題例句                         │
│  ☐ 拼寫測驗             需要更高熟悉度                           │
│  ☐ 用法區分             測試易混淆詞                             │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  題數                                                           │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                          │
│  │  10  │ │  20  │ │  30  │ │  50  │                          │
│  └──────┘ └──────┘ └──────┘ └──────┘                          │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     開始練習                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.6 Quiz Result Integration with SRS

Quiz results directly update SRS card states:

| Quiz Result | SRS Impact |
|-------------|------------|
| Correct (fast, <3s) | Equivalent to "Easy" rating |
| Correct (normal) | Equivalent to "Good" rating |
| Correct (slow, >10s or with hint) | Equivalent to "Hard" rating |
| Incorrect | Equivalent to "Again" rating, card re-enters learning queue |

This creates a unified learning loop where both Flashcard and Quiz modes contribute to the same spaced repetition schedule.

---

## 8. Responsive Design Strategy

### 8.1 Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | < 640px | Single column, bottom sheet modals |
| Tablet | 640px - 1023px | Two column (list + detail), collapsible sidebar |
| Desktop | ≥ 1024px | Three column (sidebar + list + detail) |

### 8.2 Mobile-Specific Patterns

**Navigation**: Bottom tab bar
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                        [Content Area]                           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│    📚         📝         🎴         📊                          │
│   瀏覽       練習       學習       統計                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Word Detail**: Full-screen overlay with swipe-to-dismiss
**Flashcard**: Full-screen immersive mode
**Filters**: Bottom sheet with gesture controls

### 8.3 Tablet-Specific Patterns

**iPad Split View**: Support for multitasking
**Landscape**: Side-by-side list and detail
**Portrait**: Collapsible detail panel

### 8.4 Desktop-Specific Patterns

**Keyboard shortcuts**:
- `Space`: Flip flashcard / Submit answer
- `1-4`: Rate card (Again/Hard/Good/Easy)
- `←/→`: Navigate cards
- `/`: Focus search
- `Esc`: Close modals

**Hover states**: Rich tooltips, preview on hover

---

## 9. URL Routing

### 9.1 Route Structure

```typescript
// routes.ts
const routes = {
  '/': BrowseView,
  '/word/:lemma': WordDetailView,
  '/word/:lemma/:senseId': WordSenseView,
  '/flashcard': FlashcardDashboard,
  '/flashcard/session': FlashcardSession,
  '/quiz': QuizSetup,
  '/quiz/session': QuizSession,
  '/stats': StatsView,  // Future
};
```

### 9.2 Navigation Behavior

| Action | URL Change | Behavior |
|--------|------------|----------|
| Click word in list | `/word/{lemma}` | Push to history, show detail |
| Click sense tab | `/word/{lemma}/{senseId}` | Replace current URL |
| Click "開始學習" | `/flashcard/session` | Push to history |
| Complete session | `/flashcard` | Replace (prevent back to session) |
| Browser back | Previous URL | Restore previous view state |
| Direct URL access | Any valid route | Load correct view with data |

### 9.3 State Synchronization

```typescript
// URL ↔ Store sync pattern
$effect(() => {
  // When URL changes, update store
  const params = parseRoute(currentPath);
  if (params.lemma) {
    selectWord(params.lemma);
  }
});

// When store changes from UI, update URL
function handleWordSelect(lemma: string) {
  selectWord(lemma);
  navigate(`/word/${lemma}`);
}
```

### 9.4 Mobile Considerations

- Support system back gesture (iOS swipe, Android back button)
- Bottom sheet dismiss should update URL
- Preserve scroll position in word list when returning

---

## 10. Implementation Phases

### Phase 0: URL Routing Foundation (Week 1)

- [x] Choose and integrate router library (or implement hash-based routing)
- [x] Define route structure and type-safe route params
- [ ] Implement URL ↔ store synchronization
- [ ] Handle deep linking and initial load
- [ ] Test browser navigation (back/forward)
- [ ] Mobile gesture support verification

### Phase 1: Data Infrastructure (Week 1-2)

- [x] Create TypeScript types for new data model
- [x] Implement IndexedDB wrapper (`stores/vocab-db.ts`)
- [x] Create version checking and update mechanism
- [x] Build loading progress UI component
- [x] Migrate from API fetching to local IndexedDB queries

### Phase 2: Browse View Enhancement (Week 2-3)

- [x] Redesign filter sidebar with new filter options
- [x] Implement sort options dropdown
- [x] Update `WordList` item design with new data fields
- [x] Add level/tier/importance indicators

### Phase 3: Word Detail Overhaul (Week 3-4)

- [x] Implement multi-sense tab interface
- [x] Create collapsible section components
- [x] Add statistics visualization (year distribution chart)
- [x] Implement confusion notes display
- [x] Add related words (synonyms/antonyms/derived) section

### Phase 4: Global Word Lookup (Week 4-5)

- [ ] Create `ClickableWord` component
- [ ] Build word lookup store and state management
- [ ] Implement desktop sidebar lookup panel
- [ ] Implement mobile bottom sheet lookup
- [ ] Integrate with all text display components

### Phase 5: SRS System Upgrade (Week 5-7)

- [ ] Migrate SRS schema to sense-aware model
- [ ] Implement smart card selection algorithm
- [ ] Redesign flashcard component with new data
- [ ] Add clickable words in flashcard examples
- [ ] Build learning progress charts
- [ ] Update study dashboard

### Phase 6: Quiz System (Week 7-8)

- [ ] Create adaptive quiz type selector
- [ ] Build quiz question generator using real exam data
- [ ] Implement quiz UI with explanations
- [ ] Integrate quiz results with SRS state updates
- [ ] Add quiz history and statistics

### Phase 7: Polish & Testing (Week 8-9)

- [ ] Responsive design refinements
- [ ] Performance optimization (virtual scrolling, lazy loading)
- [ ] Accessibility audit and fixes
- [ ] Cross-browser testing
- [ ] User testing and feedback integration

---

## Appendix: Component Checklist

### New Components to Create

| Component | Location | Priority |
|-----------|----------|----------|
| `DataLoader.svelte` | `components/` | P0 |
| `LoadingOverlay.svelte` | `components/` | P0 |
| `LevelChip.svelte` | `components/ui/` | P1 |
| `ImportanceBadge.svelte` | `components/ui/` | P1 |
| `SenseTabs.svelte` | `components/word/` | P1 |
| `CollapsibleSection.svelte` | `components/ui/` | P1 |
| `YearDistributionChart.svelte` | `components/charts/` | P2 |
| `ConfusionNotes.svelte` | `components/word/` | P2 |
| `RelatedWords.svelte` | `components/word/` | P2 |
| `ClickableWord.svelte` | `components/ui/` | P1 |
| `QuickLookupSidebar.svelte` | `components/lookup/` | P1 |
| `QuickLookupSheet.svelte` | `components/lookup/` | P1 |
| `FlashcardV2.svelte` | `components/srs/` | P1 |
| `LearningChart.svelte` | `components/charts/` | P2 |
| `QuizQuestion.svelte` | `components/quiz/` | P2 |
| `QuizExplanation.svelte` | `components/quiz/` | P2 |
| `BottomSheet.svelte` | `components/ui/` | P1 |
| `Router.svelte` | `components/` | P0 |

### Stores to Create/Modify

| Store | Status | Description |
|-------|--------|-------------|
| `vocab-db.ts` | New | IndexedDB operations |
| `vocab.svelte.ts` | Modify | Use local DB instead of API |
| `srs-storage.ts` | Modify | Sense-aware card schema |
| `srs.svelte.ts` | Modify | Smart card selection |
| `word-lookup.svelte.ts` | New | Global word lookup state |
| `quiz.svelte.ts` | Modify | Adaptive quiz generation |
| `router.svelte.ts` | New | URL routing state management |

---

## Appendix: Icon Guidelines

All icons should come from **Heroicons** (https://heroicons.com) or a similar consistent icon library. Never use emojis in the production UI.

### Recommended Icon Mappings

| Usage | Heroicon Name | Style |
|-------|---------------|-------|
| Audio/Speaker | `speaker-wave` | outline |
| Back/Return | `arrow-left` | outline |
| Expand/Collapse | `chevron-down` / `chevron-up` | outline |
| Search | `magnifying-glass` | outline |
| Filter | `adjustments-horizontal` | outline |
| Statistics | `chart-bar` | outline |
| Root Analysis | `puzzle-piece` | outline |
| Confusion/Warning | `exclamation-triangle` | outline |
| Related/Link | `link` | outline |
| Check/Correct | `check` | solid |
| X/Incorrect | `x-mark` | solid |
| Info/Help | `question-mark-circle` | outline |
| Settings | `cog-6-tooth` | outline |
| Play | `play` | solid |
| Complete/Success | `check-circle` | solid |

### Icon Sizing

| Context | Size | Tailwind Class |
|---------|------|----------------|
| Inline with text | 16px | `w-4 h-4` |
| Button icon | 20px | `w-5 h-5` |
| Section header | 20px | `w-5 h-5` |
| Hero/Empty state | 48px | `w-12 h-12` |

### Icon Colors

- Default: `text-content-tertiary`
- Hover: `text-content-secondary`
- Active: `text-accent`
- Success: `text-srs-good`
- Error: `text-srs-again`
- Warning: `text-srs-hard`

---

*This document should be updated as implementation progresses and requirements evolve.*
