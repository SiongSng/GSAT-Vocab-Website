# SRS Flashcard UI Redesign Plan

## Overview

將現有的 Flashcard 功能升級為基於遺忘曲線的 SRS（間隔重複系統），並採用 Heptabase 風格重新設計 UI。

---

## Part 1: Design System (Heptabase Style)

### 色彩系統

從 Heptabase 官網提取的關鍵設計 token：

```css
/* 背景色 */
--bg-page: #f7f7f7;           /* 頁面背景 */
--bg-section: #ffffff;         /* 卡片/面板背景 */
--bg-hover: rgba(0,0,0,0.04);  /* hover 狀態背景 - 更明顯 */

/* 文字色 */
--text-primary: #2e2e2e;       /* 主要文字 */
--text-secondary: #6a6972;     /* 次要文字 */
--text-tertiary: #908f89;      /* 提示文字 */

/* 邊框 */
--border-light: rgba(0,0,0,0.08);
--border-light-middle: rgba(0,0,0,0.13);

/* 強調色 */
--accent: #207dff;             /* 藍色強調 */
--danger: #e14646;             /* 紅色警告 */
--success: #75c33a;            /* 綠色成功 */

/* SRS 語意色（降低飽和度）*/
--srs-again: #e57373;          /* 忘記 */
--srs-hard: #ffb74d;           /* 困難 */
--srs-good: #81c784;           /* 正常 */
--srs-easy: #64b5f6;           /* 簡單 */

/* 陰影 */
--shadow-card: 0 0 0 1px hsla(0,0%,6%,.05), 0 2px 4px hsla(0,0%,6%,.1);
--shadow-float: 0 10px 30px rgba(0,0,0,.06);
```

### 字體系統

- **Primary Font**: Inter (400, 500, 600)
- **Heading Font**: Manrope (600) - 用於大標題
- **Letter Spacing**: 負值追蹤 (-0.36px ~ -1.6px) 用於標題

### 設計特點

1. **極淡邊框** — `border: 1px solid rgba(0,0,0,0.08)` 取代陰影
2. **低飽和度** — 灰階為主，彩色只用於語意指示
3. **小圓角** — `rounded-md` (6px) 或 `rounded-lg` (8px)
4. **Ghost 按鈕** — hover 使用 `rgba(0,0,0,0.04)` 背景，足夠明顯但不刺眼
5. **充足留白** — 寬鬆的 padding 和 gap
6. **輕量字重** — 最重只用 `font-semibold` (600)
7. **Pill 按鈕** — CTA 使用 `rounded-full`
8. **定義分隔** — 多個定義間使用 `space-y-4`，不使用分隔線，靠間距區分
9. **層次高度** — 使用 `shadow-card` 建立視覺層次，重要元素浮起

---

## Part 2: Tailwind v4 Setup

### 安裝步驟

```bash
cd frontend
bun add -D tailwindcss @tailwindcss/vite
```

### vite.config.ts 更新

```ts
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [tailwindcss(), svelte()],
});
```

### 建立 src/app.css

```css
@import "tailwindcss";

@theme {
  /* Typography */
  --font-sans: 'Inter', system-ui, sans-serif;
  
  /* Colors - Surfaces */
  --color-surface-page: #f7f7f7;
  --color-surface-primary: #ffffff;
  --color-surface-secondary: #fafafa;
  
  /* Colors - Content */
  --color-content-primary: #2e2e2e;
  --color-content-secondary: #6a6972;
  --color-content-tertiary: #908f89;
  
  /* Colors - Border */
  --color-border: rgba(0,0,0,0.08);
  --color-border-hover: rgba(0,0,0,0.13);
  
  /* Colors - Accent */
  --color-accent: #207dff;
  --color-accent-soft: rgba(32,125,255,0.1);
  
  /* Colors - SRS */
  --color-srs-again: #e57373;
  --color-srs-hard: #ffb74d;
  --color-srs-good: #81c784;
  --color-srs-easy: #64b5f6;
  
  /* Shadows */
  --shadow-card: 0 0 0 1px hsla(0,0%,6%,.05), 0 2px 4px hsla(0,0%,6%,.1);
  --shadow-float: 0 10px 30px rgba(0,0,0,.06);
  
  /* Border Radius */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-full: 9999px;
}
```

### index.html 更新

移除 CDN，改為 import：

```html
<!-- 移除這行 -->
<script src="https://cdn.tailwindcss.com"></script>
```

在 main.ts 中：

```ts
import './app.css';
```

---

## Part 3: SRS Core Implementation

### 資料模型

```ts
// src/lib/types/srs.ts

export type CardState = 'new' | 'learning' | 'review' | 'relearning';
export type Rating = 'again' | 'hard' | 'good' | 'easy';

export interface Card {
  lemma: string;
  due: Date;
  stability: number;      // 記憶穩定度（天數）
  difficulty: number;     // 難度 (1-10)
  elapsedDays: number;    // 距上次複習天數
  scheduledDays: number;  // 預定間隔天數
  reps: number;           // 複習次數
  lapses: number;         // 遺忘次數
  state: CardState;
  lastReview: Date | null;
}

export interface ReviewLog {
  lemma: string;
  rating: Rating;
  state: CardState;
  due: Date;
  stability: number;
  difficulty: number;
  elapsedDays: number;
  scheduledDays: number;
  review: Date;
}
```

### 儲存策略

使用 IndexedDB + Memory Cache：

```ts
// src/lib/stores/srs-storage.ts

import { openDB, type IDBPDatabase } from 'idb';

interface SRSDatabase {
  cards: Card;
  logs: ReviewLog;
  meta: { key: string; value: unknown };
}

// 啟動時一次載入到記憶體
// 操作時純 Memory 讀寫
// 儲存時批次寫入 IndexedDB (debounced)
```

### FSRS 演算法

選項：
1. 使用 `ts-fsrs` 套件 (推薦)
2. 自行實作核心演算法

```bash
bun add ts-fsrs
```

---

## Part 4: UI Components

### 畫面結構

```
FlashcardView.svelte
├── DashboardPanel.svelte      # 今日學習儀表板
│   ├── StatsCards             # Review/Learning/New 統計
│   ├── StartButton            # 開始學習按鈕
│   ├── CustomStudyPanel       # 自訂學習（可展開）
│   └── ProgressStats          # 學習統計
│
├── StudySession.svelte        # 學習 session
│   ├── Flashcard.svelte       # 卡片本體
│   │   ├── CardBadge          # 狀態
徽章
│   │   ├── AudioButton        # 發音按鈕
│   │   ├── WordDisplay        # 單字顯示
│   │   └── DefinitionList     # 釋義列表
│   ├── RatingButtons.svelte   # Again/Hard/Good/Easy
│   └── ProgressBar.svelte     # 進度指示器
│
└── SessionComplete.svelte     # 學習完成畫面
    ├── SessionStats           # 本次統計
    ├── TomorrowForecast       # 明日預測
    └── ActionButtons          # 繼續/返回
```

### 關鍵元件樣式

#### 主要按鈕 (CTA)

```html
<button class="

  px-6 py-3 
  bg-content
-primary text-white 
  rounded-full 
  text-sm font-medium 
  hover:opacity-90 
  transition-all duration-200
  shadow-card
">
  Start Learning
</button>
```

#### 次要按鈕

```html
<button class="
  px-4 py-2 
  bg-surface-secondary text-content-secondary 
  rounded-md 
  text-sm font-medium 
  border border-border
  hover:bg-surface-page hover:border-border-hover 
  transition-all duration-200
">
  Cancel
</button>
```

#### Ghost 按鈕

```html
<button class="
  px-3 py-2 
  text-content-secondary 
  rounded-lg 
  text-sm font-normal 
  hover:bg-surface-secondary 
  transition-all duration-200
">
  Custom Study
</button>
```

#### 評分按鈕

```html
<button class="
  flex flex-col items-center 
  py-3.5 px-4 
  rounded-lg 
  border border-transparent
  hover:border-srs-good/30 
  hover:bg-srs-good/8
  transition-all 
  group
">
  <span class="text-[14px] font-medium text-content-secondary group-hover:text-srs-good transition-colors">
    Good
  </span>
  <span class="text-[11px] text-content-tertiary mt-1">1d</span>
</button>
```

Note: 評分按鈕 hover 使用邊框 + 淡背景組合，而非單純背景色變化，更精緻。

#### 卡片容器

```html
<div class="
  bg-surface-primary 
  rounded-lg 
  border border-border 
  p-6
  shadow-card
">
  <!-- content -->
</div>
```

#### 狀態徽章

```html
<span class="px-2 py-0.5 text-xs font-medium rounded bg-srs-easy/10 text-srs-easy">
  New
</span>
<span class="px-2 py-0.5 text-xs font-medium rounded bg-srs-hard/10 text-srs-hard">
  Learning
</span>
<span class="px-2 py-0.5 text-xs font-medium rounded bg-srs-good/10 text-srs-good">
  Review
</span>
<span class="px-2 py-0.5 text-xs font-medium rounded bg-srs-again/10 text-srs-again">
  Relearning
</span>
```

---

## Part 5: Implementation Steps

### Phase 1: Setup (1-2 hours)

1. [ ] 安裝 Tailwind v4 + @tailwindcss/vite
2. [ ] 建立 app.css 與 theme 配置
3. [ ] 更新 vite.config.ts
4. [ ] 移除 index.html 中的 CDN
5. [ ] 驗證 build 正常

### Phase 2: Design System (2-3 hours)

1. [ ] 建立共用 CSS classes
2. [ ] 更新 Header.svelte 樣式
3. [ ] 更新 Sidebar.svelte 樣式
4. [ ] 確保現有功能不受影響

### Phase 3: SRS Core (3-4 hours)

1. [ ] 安裝 ts-fsrs 和 idb
2. [ ] 建立 srs types
3. [ ] 實作 IndexedDB storage
4. [ ] 實作 FSRS 排程邏輯
5. [ ] 建立 srs.svelte.ts store

### Phase 4: Flashcard UI (4-5 hours)

1. [ ] 重構 FlashcardView.svelte 結構
2. [ ] 實作 DashboardPanel
3. [ ] 實作 StudySession
4. [ ] 實作 RatingButtons
5. [ ] 實作 SessionComplete
6. [ ] 加入鍵盤快捷鍵 (1/2/3/4)

### Phase 5: Testing & Polish (2-3 hours)

1. [ ] 測試 SRS 排程邏輯
2. [ ] 測試 IndexedDB 持久化
3. [ ] 響應式測試 (mobile/desktop)
4. [ ] 動畫微調
5. [ ] 刪除 prototype.html

---

## Dependencies to Add

```bash
bun add -D tailwindcss @tailwindcss/vite
bun add ts-fsrs idb
```

---

## Files to Create/Modify

### New Files

- `src/app.css` - Tailwind 入口與 theme
- `src/lib/types/srs.ts` - SRS 型別定義
- `src/lib/stores/srs.svelte.ts` - SRS 狀態管理
- `src/lib/stores/srs-storage.ts` - IndexedDB 儲存層
- `src/lib/components/DashboardPanel.svelte`
- `src/lib/components/StudySession.svelte`
- `src/lib/components/RatingButtons.svelte`
- `src/lib/components/SessionComplete.svelte`

### Modified Files

- `vite.config.ts` - 加入 Tailwind plugin
- `src/main.ts` - import app.css
- `index.html` - 移除 CDN
- `src/lib/components/FlashcardView.svelte` - 重構
- `src/lib/stores/flashcard.svelte.ts` - 整合 SRS
- `src/lib/components/Header.svelte` - 樣式更新
- `src/lib/components/Sidebar.svelte` - 樣式更新

### Delete Files

- `prototype.html` - 完成後刪除

---

## UI 細節注意事項

### 層次與高度 (Elevation)

建立視覺層次感，讓重要元素「浮」起來：

| 層級 | 用途 | 樣式 |
|-----|------|------|
| Level 0 | 頁面背景 | `bg-surface-page` (#f7f7f7) |
| Level 1 | 卡片/面板 | `bg-surface-primary shadow-card` |
| Level 2 | 浮動元素、Modal | `bg-surface-primary shadow-float` |
| Level 3 | Tooltip、Dropdown | `bg-surface-primary shadow-image` |

```css
--shadow-card: 0 0 0 1px rgba(15,15,15,0.03), 0 2px 4px rgba(15,15,15,0.06);
--shadow-float: 0 10px 30px rgba(0,0,0,0.06);
--shadow-image: 0 8px 24px rgba(0,0,0,0.12);
```

- 主要卡片（Dashboard、Flashcard）使用 `shadow-card`
- 統計區塊使用 `bg-surface-page/60` 下沉，與卡片形成對比
- 按鈕不加陰影，靠背景色和邊框區分
- 評分按鈕 hover 時微微浮起感，用 `border` 實現而非 `shadow`

### Hover 狀態
- Ghost 按鈕: `hover:bg-[rgba(0,0,0,0.04)]` — 比 `surface-hover` 更明顯
- 評分按鈕: `hover:border-{color}/30 hover:bg-{color}/8` — 邊框 + 背景組合
- 連結/可點擊: 使用 `clickable-overlay` 偽元素實現平滑過渡

### 定義列表樣式
- 多個定義間使用 `space-y-4` 間距，不使用水平分隔線
- 每個定義區塊結構:
  ```html
  <div>
    <span class="inline-block px-2 py-0.5 text-[11px] font-medium rounded bg-surface-page text-content-tertiary mb-2">noun</span>
    <p class="text-[15px] text-content-primary leading-relaxed">中文定義</p>
    <p class="text-[13px] text-content-tertiary mt-1 leading-relaxed">英文定義</p>
  </div>
  ```
- 避免使用 `border-b` 分隔定義，視覺上太重且不自然

---

## Notes

- 不需要 dark mode
- 保留翻牌動畫但改為更現代的效果
- 優先使用 Heptabase 風格的極簡邊框而非陰影
- 評分按鈕使用 4 級制 (Again/Hard/Good/Easy)
- 鍵盤快捷鍵: 1=Again, 2=Hard, 3=Good, 4=Easy
