# GSAT Vocab Website Design System

A comprehensive design specification based on Heptabase/Notion-inspired aesthetics. This document serves as the single source of truth for UI consistency across all components.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Color System](#color-system)
3. [Typography](#typography)
4. [Spacing](#spacing)
5. [Border & Radius](#border--radius)
6. [Shadows](#shadows)
7. [Components](#components)
8. [Form Controls](#form-controls)
9. [States & Interactions](#states--interactions)
10. [Layout Patterns](#layout-patterns)

---

## Design Principles

### 1. Light Borders Over Heavy Shadows
Use subtle borders (`border border-border`) instead of heavy box shadows. Shadows should only be used for floating elements like dropdowns or modals.

### 2. Subtle Interactions
Hover states should be barely perceptible but still provide feedback. Use `bg-surface-hover` (rgba(0,0,0,0.04)) for ghost interactions.

### 3. Content-First Hierarchy
Typography and spacing should guide the user's eye. Use font weight and color contrast rather than decorative elements to establish hierarchy.

### 4. Consistent Density
Maintain consistent padding and gap values. Use 4px increments (0.25rem) for spacing.

### 5. Accessible by Default
Ensure sufficient color contrast, visible focus states, and keyboard navigability.

---

## Color System

All colors are defined as CSS custom properties in `app.css`.

### Surface Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-surface-page` | `#f7f7f7` | Page background |
| `--color-surface-primary` | `#ffffff` | Cards, panels, inputs |
| `--color-surface-secondary` | `#fafafa` | Secondary containers, skeleton base |
| `--color-surface-hover` | `rgba(0,0,0,0.04)` | Hover state for ghost elements |

### Content Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-content-primary` | `#2e2e2e` | Headings, primary text, primary buttons |
| `--color-content-secondary` | `#6a6972` | Body text, labels |
| `--color-content-tertiary` | `#908f89` | Hints, placeholders, disabled text |

### Border Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-border` | `rgba(0,0,0,0.08)` | Default borders |
| `--color-border-hover` | `rgba(0,0,0,0.13)` | Hover state borders |

### Accent Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-accent` | `#207dff` | Links, active states, primary actions |
| `--color-accent-soft` | `rgba(32,125,255,0.1)` | Active backgrounds, focus rings |
| `--color-accent-hover` | `#1a6ae0` | Accent button hover |

### SRS Status Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-srs-again` | `#e57373` | Failed/incorrect states |
| `--color-srs-hard` | `#ffb74d` | Needs review states |
| `--color-srs-good` | `#81c784` | Success/correct states |
| `--color-srs-easy` | `#64b5f6` | Easy/new states |

### Tailwind Class Mapping

```css
/* Use these Tailwind classes */
bg-surface-page        /* Page background */
bg-surface-primary     /* Cards, panels */
bg-surface-secondary   /* Secondary containers */
bg-surface-hover       /* Hover states */

text-content-primary   /* Main headings, important text */
text-content-secondary /* Body text, labels */
text-content-tertiary  /* Hints, placeholders */

border-border          /* Default borders */
border-border-hover    /* Hover borders */

bg-accent              /* Primary action buttons */
bg-accent-soft         /* Active chip backgrounds */
text-accent            /* Links, active text */

bg-srs-again           /* Error/fail button */
bg-srs-hard            /* Warning button */
bg-srs-good            /* Success button */
bg-srs-easy            /* Info button */
```

---

## Typography

### Font Families

```css
--font-sans: "Inter", "Noto Sans TC", system-ui, -apple-system, sans-serif;
--font-heading: "Manrope", "Inter", system-ui, sans-serif;
```

### Font Sizes & Weights

| Element | Size | Weight | Tracking | Class |
|---------|------|--------|----------|-------|
| Page Title | `text-2xl` / `text-3xl` | `font-semibold` (600) | `tracking-tight` | `.text-2xl.font-semibold.tracking-tight` |
| Section Header | `text-xl` / `text-lg` | `font-semibold` (600) | `tracking-tight` | `.text-lg.font-semibold.tracking-tight` |
| Card Title | `text-base` | `font-semibold` (600) | - | `.text-base.font-semibold` |
| Body Text | `text-sm` / `text-base` | `font-normal` (400) | - | `.text-sm` |
| Label | `text-sm` | `font-medium` (500) | - | `.text-sm.font-medium` |
| Small/Caption | `text-xs` | `font-medium` (500) | `tracking-wide` | `.text-xs.font-medium` |

### Section Headers Pattern

```html
<h3 class="text-sm font-medium text-content-secondary mb-3 uppercase tracking-wide">
  Section Title
</h3>
```

---

## Spacing

Use 4px (0.25rem) increments consistently.

### Common Patterns

| Usage | Value | Tailwind |
|-------|-------|----------|
| Card padding | 24px | `p-6` |
| Card padding (large) | 28px-32px | `p-7` / `p-8` |
| Section gap | 20px | `gap-5` / `space-y-5` |
| Element gap | 8px-12px | `gap-2` / `gap-3` |
| Button padding | 10px 20px | `py-2.5 px-5` |
| Small button padding | 8px 16px | `py-2 px-4` |
| Input padding | 10px 14px | `py-2.5 px-3.5` |
| Chip padding | 6px 12px | `py-1.5 px-3` |

---

## Border & Radius

### Border Width

Always use `1px` borders (Tailwind default `border`).

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `4px` | Chips, tags, small elements |
| `--radius-md` | `6px` | Buttons, inputs, chips |
| `--radius-lg` | `8px` | Cards, panels |

```html
<!-- Examples -->
<div class="rounded-md">Button/Input</div>
<div class="rounded-lg">Card/Panel</div>
```

---

## Shadows

### Design Philosophy

Prefer borders over shadows. Use shadows sparingly.

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-card` | `0 0 0 1px hsla(0,0%,6%,0.05), 0 2px 4px hsla(0,0%,6%,0.1)` | Elevated cards (rarely used) |
| `--shadow-float` | `0 10px 30px rgba(0,0,0,0.06)` | Dropdowns, modals |

### Preferred Pattern

```html
<!-- DO: Use border for cards -->
<div class="bg-surface-primary rounded-lg border border-border">...</div>

<!-- DON'T: Use heavy shadows -->
<div class="bg-white rounded-xl shadow-lg">...</div>
```

---

## Components

### Cards

```html
<div class="bg-surface-primary rounded-lg border border-border p-6">
  <h3 class="text-lg font-semibold tracking-tight text-content-primary mb-4">
    Card Title
  </h3>
  <p class="text-content-secondary">Card content...</p>
</div>
```

### Buttons

#### Primary Button (Dark)
```html
<button class="px-5 py-2.5 bg-content-primary text-white font-medium rounded-md hover:opacity-90 transition-opacity">
  Primary Action
</button>
```

#### Accent Button (Blue)
```html
<button class="px-5 py-2.5 bg-accent text-white font-medium rounded-md hover:opacity-90 transition-opacity">
  Accent Action
</button>
```

#### Secondary Button
```html
<button class="px-5 py-2.5 bg-surface-page text-content-primary font-medium rounded-md border border-border hover:bg-surface-hover transition-colors">
  Secondary Action
</button>
```

#### Ghost Button
```html
<button class="p-2.5 rounded-md hover:bg-surface-hover transition-colors text-content-tertiary hover:text-content-secondary">
  <svg class="w-5 h-5">...</svg>
</button>
```

#### Status Buttons
```html
<!-- Success -->
<button class="px-5 py-2.5 bg-srs-good text-white font-medium rounded-md hover:opacity-90">
  Correct
</button>

<!-- Warning -->
<button class="px-5 py-2.5 bg-srs-hard text-white font-medium rounded-md hover:opacity-90">
  Needs Review
</button>

<!-- Error -->
<button class="px-5 py-2.5 bg-srs-again text-white font-medium rounded-md hover:opacity-90">
  Incorrect
</button>
```

### Chips / Tags

#### Default Chip
```html
<button class="px-3 py-1.5 bg-surface-page text-content-secondary text-sm font-medium rounded-md border border-transparent hover:bg-surface-hover hover:border-border transition-all">
  Chip Label
</button>
```

#### Active Chip
```html
<button class="px-3 py-1.5 bg-accent-soft text-accent text-sm font-medium rounded-md border border-transparent transition-all">
  Active Chip
</button>
```

#### POS Tag (Part of Speech)
```html
<span class="text-xs font-medium px-2 py-0.5 bg-accent-soft text-accent rounded">
  NOUN
</span>
```

### List Items

```html
<button class="flex justify-between items-center w-full p-4 bg-surface-primary border-b border-border hover:bg-surface-hover transition-colors text-left">
  <div class="flex-1 min-w-0">
    <div class="flex items-center gap-2">
      <span class="font-semibold text-content-primary">Word</span>
      <span class="text-xs font-medium text-content-tertiary">POS</span>
    </div>
    <p class="text-xs text-content-secondary mt-1 truncate">Description...</p>
  </div>
  <span class="text-xs font-mono bg-surface-page text-content-secondary px-2 py-0.5 rounded-full">
    123
  </span>
</button>
```

#### Active List Item
Add `bg-accent-soft` to indicate selection:
```html
<button class="... bg-accent-soft">...</button>
```

### Empty States

```html
<div class="flex flex-col items-center justify-center h-full px-4 py-12 text-center">
  <div class="w-12 h-12 rounded-full bg-surface-secondary flex items-center justify-center mb-4">
    <svg class="w-6 h-6 text-content-tertiary">...</svg>
  </div>
  <h3 class="text-base font-semibold text-content-primary mb-2">
    No Results Found
  </h3>
  <p class="text-sm text-content-secondary max-w-xs">
    Try adjusting your filters or search terms.
  </p>
</div>
```

### Skeleton Loading

```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--color-surface-secondary) 25%,
    var(--color-surface-page) 50%,
    var(--color-surface-secondary) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 2.5s infinite;
  border-radius: 4px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## Form Controls

All form controls have global styles defined in `app.css`.

### Text Input

```html
<input
  type="text"
  class="w-full px-3.5 py-2.5 text-sm bg-surface-primary border border-border rounded-md focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent-soft transition-colors"
  placeholder="Placeholder text..."
/>
```

### Checkbox

Custom styled via CSS (no Tailwind classes needed):
```html
<label class="flex items-center gap-2.5 cursor-pointer group">
  <input type="checkbox" />
  <span class="text-sm text-content-secondary group-hover:text-content-primary transition-colors">
    Checkbox label
  </span>
</label>
```

### Radio Button

```html
<label class="inline-flex items-center gap-2.5 cursor-pointer">
  <input type="radio" name="group" value="option1" />
  <span class="text-sm text-content-primary">Option 1</span>
</label>
```

### Range Slider

Custom styled via CSS with accent color thumb.

### Number Input

Spinners are hidden by default for cleaner appearance.

---

## States & Interactions

### Hover States

| Element | Hover Effect |
|---------|--------------|
| Ghost buttons | `bg-surface-hover` |
| Cards/List items | `bg-surface-hover` or `border-border-hover` |
| Links | `text-accent` (if not already) |
| Accent buttons | `opacity-90` |

### Focus States

All interactive elements use:
```css
focus:outline-none focus:ring-2 focus:ring-accent-soft
```

Or via the global CSS:
```css
box-shadow: 0 0 0 2px var(--color-accent-soft);
```

### Active/Selected States

| Element | Active Style |
|---------|--------------|
| Chips | `bg-accent-soft text-accent` |
| List items | `bg-accent-soft` |
| Navigation items | `bg-accent-soft text-accent` |

### Disabled States

```css
disabled:opacity-50 disabled:cursor-not-allowed
```

### Loading States

- Use skeleton loaders for content
- Use spinner for buttons (add `animate-spin` class to SVG)
- Show loading state after 150ms delay to avoid flash

---

## Layout Patterns

### Page Container

```html
<div class="h-full overflow-y-auto bg-surface-page p-5 sm:p-8">
  <div class="max-w-4xl mx-auto">
    <!-- Content -->
  </div>
</div>
```

### Two-Column Layout (Browse View)

```html
<div class="flex h-full">
  <!-- Sidebar: 240px fixed -->
  <aside class="w-60 flex-shrink-0 bg-surface-primary border-r border-border">
    ...
  </aside>
  
  <!-- Main content -->
  <div class="flex flex-1">
    <!-- List: 320px fixed -->
    <div class="w-80 flex-shrink-0 border-r border-border">
      ...
    </div>
    
    <!-- Detail: flex-1 -->
    <div class="flex-1 bg-surface-page">
      ...
    </div>
  </div>
</div>
```

### Card Grid

```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  <div class="bg-surface-primary rounded-lg border border-border p-5">
    ...
  </div>
</div>
```

### Stats Row

```html
<div class="grid grid-cols-3 gap-3">
  <div class="text-center py-4 px-3 rounded-md bg-surface-page/60">
    <div class="text-2xl font-semibold text-content-primary tracking-tight">
      123
    </div>
    <div class="text-sm text-content-secondary mt-1.5">
      Label
    </div>
  </div>
  ...
</div>
```

---

## Scrollbar Styling

Apply to scrollable containers:

```css
.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-hover) transparent;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: var(--color-border-hover);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: var(--color-content-tertiary);
}
```

---

## Text Highlighting

For highlighting words in sentences:

```css
.highlight {
  background: linear-gradient(
    to top,
    rgba(32, 125, 255, 0.15) 0%,
    rgba(32, 125, 255, 0.15) 45%,
    transparent 45%
  );
  padding: 0 2px;
  margin: 0 -2px;
  border-radius: 2px;
  font-weight: 500;
}
```

---

## Checklist for New Components

When creating new components, verify:

- [ ] Uses `bg-surface-primary` for cards/panels (not `bg-white`)
- [ ] Uses `border border-border` (not `shadow-lg`)
- [ ] Uses `rounded-lg` for cards, `rounded-md` for buttons/inputs
- [ ] Text colors use `text-content-*` tokens
- [ ] Interactive elements have hover/focus states
- [ ] Buttons follow the established patterns
- [ ] Spacing uses consistent values (p-6, gap-3, etc.)
- [ ] Loading states use skeleton or spinner patterns
- [ ] Empty states are handled gracefully
