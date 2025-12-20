<script lang="ts">
    import { addWordsToSRS, getSRSStore } from "$lib/stores/srs.svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { getAppStore } from "$lib/stores/app.svelte";
    import {
        getNewCards,
        getAllCards,
        getLearningCards,
    } from "$lib/stores/srs-storage";
    import { State } from "ts-fsrs";
    import HelpTooltip from "$lib/components/ui/HelpTooltip.svelte";
    import BottomSheet from "$lib/components/ui/BottomSheet.svelte";
    import DeckEditor from "./DeckEditor.svelte";

    interface Props {
        onStart: (newCardPool: string[], excludeLemmas: Set<string>) => void;
    }

    let { onStart }: Props = $props();

    const srs = getSRSStore();
    const vocab = getVocabStore();
    const app = getAppStore();

    const STORAGE_KEY = "gsat_srs_study_settings";
    const CUSTOM_DECK_KEY = "gsat_srs_custom_decks";
    const LEGACY_DECK_KEY = "gsat_srs_custom_deck";

    type CustomDeck = {
        id: string;
        name: string;
        lemmas: string[];
        createdAt: number;
    };

    interface StudySettings {
        newCardLimit: number;
        autoSpeak: boolean;
        smartMode: boolean;
    }

    const defaultSettings: StudySettings = {
        newCardLimit: 20,
        autoSpeak: true,
        smartMode: true,
    };

    let newCardLimit = $state(defaultSettings.newCardLimit);
    let autoSpeak = $state(defaultSettings.autoSpeak);
    let smartMode = $state(defaultSettings.smartMode);
    let showSettings = $state(false);
    let isCustomDeckLoaded = $state(false);

    let customDecks: CustomDeck[] = $state([]);
    let selectedDeckId: string | null = $state(null);
    let isDeckModalOpen = $state(false);
    let editingDeckId: string | null = $state(null);

    function loadSettings(): void {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const settings: StudySettings = JSON.parse(saved);
                newCardLimit =
                    settings.newCardLimit ?? defaultSettings.newCardLimit;
                autoSpeak = settings.autoSpeak ?? defaultSettings.autoSpeak;
                smartMode = settings.smartMode ?? defaultSettings.smartMode;
            }
        } catch {
            // ignore
        }
    }

    function saveSettings(): void {
        try {
            const settings: StudySettings = {
                newCardLimit,
                autoSpeak,
                smartMode,
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
        } catch {
            // ignore
        }
    }

    loadSettings();

    $effect(() => {
        newCardLimit;
        autoSpeak;
        smartMode;
        saveSettings();
    });

    const vocabLemmaMap = $derived.by(() => {
        const map = new Map<string, string>();
        for (const item of vocab.index || []) {
            map.set(item.lemma.toLowerCase(), item.lemma);
        }
        return map;
    });

    function normalizeLemma(raw: string): string | null {
        const key = raw.trim().toLowerCase();
        if (!key) return null;
        return vocabLemmaMap.get(key) || null;
    }

    function normalizeLemmaList(list: string[]): string[] {
        const seen = new Set<string>();
        const result: string[] = [];
        for (const raw of list) {
            const normalized = normalizeLemma(raw);
            if (normalized && !seen.has(normalized)) {
                seen.add(normalized);
                result.push(normalized);
            }
        }
        return result;
    }

    function saveCustomDecks(decks: CustomDeck[]): void {
        try {
            localStorage.setItem(CUSTOM_DECK_KEY, JSON.stringify(decks));
        } catch (err) {
            console.warn("Failed to save custom decks", err);
        }
    }

    function migrateLegacyDeck(): CustomDeck[] {
        try {
            const saved = localStorage.getItem(LEGACY_DECK_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                if (Array.isArray(parsed)) {
                    const lemmas = normalizeLemmaList(parsed);
                    if (lemmas.length > 0) {
                        return [
                            {
                                id:
                                    crypto.randomUUID?.() ??
                                    `deck-${Date.now()}`,
                                name: "自訂卡組",
                                lemmas,
                                createdAt: Date.now(),
                            },
                        ];
                    }
                }
            }
        } catch (err) {
            console.warn("Failed to migrate legacy custom deck", err);
        }
        return [];
    }

    function loadCustomDecks(): void {
        try {
            const saved = localStorage.getItem(CUSTOM_DECK_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                if (Array.isArray(parsed)) {
                    const decks = parsed
                        .map((d) => ({
                            ...d,
                            lemmas: normalizeLemmaList(d.lemmas || []),
                        }))
                        .filter((d) => d.name && Array.isArray(d.lemmas));
                    customDecks = decks;
                }
            } else {
                const legacy = migrateLegacyDeck();
                if (legacy.length > 0) {
                    customDecks = legacy;
                    saveCustomDecks(legacy);
                }
            }
        } catch (err) {
            console.warn("Failed to load custom decks", err);
        } finally {
            isCustomDeckLoaded = true;
            if (!selectedDeckId && customDecks.length > 0) {
                selectedDeckId = customDecks[0].id;
            }
        }
    }

    $effect(() => {
        if (isCustomDeckLoaded) return;
        if (!vocab.index || vocab.index.length === 0) return;
        loadCustomDecks();
    });

    function handleDeckSave(name: string, lemmas: string[]): void {
        const decks = [...customDecks];
        const now = Date.now();
        let deckId = editingDeckId;

        if (editingDeckId) {
            const idx = decks.findIndex((d) => d.id === editingDeckId);
            if (idx >= 0) {
                decks[idx] = { ...decks[idx], name, lemmas };
            } else {
                deckId = null;
            }
        }

        if (!deckId) {
            deckId =
                crypto.randomUUID?.() ??
                `deck-${now}-${Math.random().toString(36).slice(2, 8)}`;
            decks.push({ id: deckId, name, lemmas, createdAt: now });
        }

        const newOnes = lemmas.filter((lemma) => !existingLemmaSet.has(lemma));
        if (newOnes.length > 0) {
            addWordsToSRS(newOnes);
        }

        customDecks = decks;
        selectedDeckId = deckId;
        saveCustomDecks(decks);
        isDeckModalOpen = false;
        editingDeckId = null;
    }

    function openCreateDeck(): void {
        editingDeckId = null;
        isDeckModalOpen = true;
    }

    function openEditDeck(deck: CustomDeck): void {
        editingDeckId = deck.id;
        isDeckModalOpen = true;
    }

    function handleDeleteDeck(deckId: string): void {
        customDecks = customDecks.filter((d) => d.id !== deckId);
        if (selectedDeckId === deckId) {
            selectedDeckId = customDecks[0]?.id ?? null;
        }
        saveCustomDecks(customDecks);
    }

    function handleModalClose(): void {
        isDeckModalOpen = false;
        editingDeckId = null;
    }

    const newCardLemmas = $derived.by(() => {
        return new Set(getNewCards().map((c) => c.lemma));
    });

    const dueLearningCount = $derived.by(() => {
        const now = new Date();
        return getLearningCards().filter((c) => new Date(c.due) <= now).length;
    });

    const existingLemmaSet = $derived.by(() => {
        return new Set(getAllCards().map((c) => c.lemma));
    });

    const customDeckMap = $derived.by(() => {
        const map = new Map<string, CustomDeck>();
        for (const deck of customDecks) {
            map.set(deck.id, deck);
        }
        return map;
    });

    const selectedDeck = $derived(customDeckMap.get(selectedDeckId ?? ""));
    const editingDeck = $derived(
        editingDeckId ? customDeckMap.get(editingDeckId) : null,
    );

    const customDeckSet = $derived.by(() => {
        return new Set(selectedDeck?.lemmas ?? []);
    });

    const customNewCardPool = $derived.by(() => {
        if (!selectedDeck) return [];
        const newSet = new Set(getNewCards().map((c) => c.lemma));
        return selectedDeck.lemmas.filter((lemma) => newSet.has(lemma));
    });

    const customDueCount = $derived.by(() => {
        if (!selectedDeck) return 0;
        const now = new Date();
        const cards = getAllCards();
        const deckSet = new Set(selectedDeck.lemmas);
        let count = 0;
        for (const card of cards) {
            if (!deckSet.has(card.lemma)) continue;
            if (card.state === State.New) {
                count++;
            } else if (new Date(card.due) <= now) {
                count++;
            }
        }
        return count;
    });

    const deckLearnedCountMap = $derived.by(() => {
        const cards = getAllCards();
        const learnedSet = new Set<string>();
        for (const card of cards) {
            if (card.state !== State.New) {
                learnedSet.add(card.lemma);
            }
        }
        const map = new Map<string, number>();
        for (const deck of customDecks) {
            let count = 0;
            for (const lemma of deck.lemmas) {
                if (learnedSet.has(lemma)) count++;
            }
            map.set(deck.id, count);
        }
        return map;
    });

    const learnedLemmaCount = $derived.by(() => {
        const cards = getAllCards();
        const learnedLemmas = new Set<string>();
        for (const card of cards) {
            if (card.state !== State.New) {
                learnedLemmas.add(card.lemma);
            }
        }
        return learnedLemmas.size;
    });

    const filteredNewCardPool = $derived.by(() => {
        let pool = vocab.index || [];

        pool = pool.filter((w) => newCardLemmas.has(w.lemma));
        pool = pool.filter((w) => w.primary_pos !== "PROPN");

        if (smartMode) {
            pool = pool.sort((a, b) => b.importance_score - a.importance_score);
        }

        return pool.map((w) => w.lemma);
    });

    const actualNewCardCount = $derived(
        Math.min(newCardLimit, filteredNewCardPool.length),
    );

    const todayTotal = $derived(
        srs.deckStats.reviewCount + dueLearningCount + actualNewCardCount,
    );

    const hasCardsToStudy = $derived(
        srs.deckStats.reviewCount > 0 ||
            dueLearningCount > 0 ||
            actualNewCardCount > 0,
    );

    const excludedLemmas = $derived.by(() => {
        const propnLemmas = (vocab.index || [])
            .filter((w) => w.primary_pos === "PROPN")
            .map((w) => w.lemma);
        return new Set(propnLemmas);
    });

    const customExcludedLemmas = $derived.by(() => {
        const exclude = new Set<string>(excludedLemmas);
        if (!selectedDeck) return exclude;
        for (const item of vocab.index || []) {
            if (!customDeckSet.has(item.lemma)) {
                exclude.add(item.lemma);
            }
        }
        return exclude;
    });

    function handleStart() {
        onStart(filteredNewCardPool, excludedLemmas);
    }

    function handleStartCustomDeck() {
        if (!selectedDeck) return;
        onStart(customNewCardPool, customExcludedLemmas);
    }
</script>

<div class="dashboard-layout">
    <div
        class="main-card bg-surface-primary rounded-lg border border-border p-6 lg:p-8"
    >
        <h2
            class="text-xl lg:text-2xl font-semibold tracking-tight text-content-primary mb-6"
        >
            今日進度
        </h2>

        <div class="stats-section">
            <div class="stats-hero">
                <div class="stats-hero-number">{todayTotal}</div>
                <div class="stats-hero-label">張卡片</div>
            </div>

            <div class="stats-row">
                <div class="stats-item">
                    <span class="stats-dot stats-dot-review"></span>
                    <span class="stats-value">{srs.deckStats.reviewCount}</span>
                    <span class="stats-label">複習</span>
                    <HelpTooltip text="已記住的卡片，到了預定的複習時間" />
                </div>
                <div class="stats-item">
                    <span class="stats-dot stats-dot-learning"></span>
                    <span class="stats-value">{dueLearningCount}</span>
                    <span class="stats-label">熟悉中</span>
                    <HelpTooltip
                        text="正在學習的卡片，需要多次練習來鞏固記憶"
                    />
                </div>
                <div class="stats-item">
                    <span class="stats-dot stats-dot-new"></span>
                    <span class="stats-value">{actualNewCardCount}</span>
                    <span class="stats-label">新單字</span>
                    <HelpTooltip text="尚未開始學習的新卡片" />
                </div>
                <div class="stats-item">
                    <span class="stats-dot stats-dot-mastered"></span>
                    <span class="stats-value">{learnedLemmaCount}</span>
                    <span class="stats-label">已掌握</span>
                    <HelpTooltip text="累計已學習過的單字總數" />
                </div>
            </div>
        </div>

        {#if app.isMobile}
            <button
                onclick={() => (showSettings = !showSettings)}
                class="settings-toggle"
            >
                <span>偏好設定</span>
                <svg
                    class="w-4 h-4 text-content-tertiary transition-transform {showSettings
                        ? 'rotate-180'
                        : ''}"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="m19 9-7 7-7-7"
                    />
                </svg>
            </button>
        {/if}

        {#if app.isMobile && showSettings}
            <div class="border-t border-border pt-4 mb-4">
                {@render settingsContent()}
            </div>
        {/if}

        <button
            onclick={handleStart}
            disabled={!hasCardsToStudy}
            class="btn-start"
        >
            {#if hasCardsToStudy}
                開始練習
            {:else}
                今日完成
            {/if}
        </button>

        {#if !app.isMobile}
            <div class="mt-6 pt-6 border-t border-border">
                {@render settingsContent()}
            </div>
        {/if}
    </div>

    <div class="deck-card bg-surface-primary rounded-lg border border-border">
        <div class="deck-header">
            <h3 class="text-base font-semibold text-content-primary">
                我的卡組
            </h3>
            <button type="button" onclick={openCreateDeck} class="btn-text">
                + 建立
            </button>
        </div>

        <div class="deck-body">
            {#if customDecks.length === 0}
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <svg
                            class="w-6 h-6"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
                            />
                        </svg>
                    </div>
                    <p class="text-sm text-content-secondary">尚無卡組</p>
                    <p class="text-xs text-content-tertiary mt-1">
                        建立專屬卡組，針對課程或章節集中練習
                    </p>
                </div>
            {:else}
                <div class="deck-list">
                    {#each customDecks as deck}
                        {@const isSelected = selectedDeckId === deck.id}
                        {@const learnedCount =
                            deckLearnedCountMap.get(deck.id) || 0}
                        {@const total = deck.lemmas.length}
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <div
                            onclick={() => (selectedDeckId = deck.id)}
                            onkeydown={(e) =>
                                e.key === "Enter" && (selectedDeckId = deck.id)}
                            class="deck-item {isSelected
                                ? 'deck-item-selected'
                                : ''}"
                            role="button"
                            tabindex="0"
                        >
                            <div class="deck-content">
                                <div class="deck-name">{deck.name}</div>
                                <div class="deck-meta">
                                    <span class="deck-progress-learned"
                                        >{learnedCount}</span
                                    >
                                    <span class="deck-progress-sep">/</span>
                                    <span>{total}</span>
                                </div>
                            </div>
                            <div class="deck-actions">
                                <button
                                    type="button"
                                    onclick={(event) => {
                                        event.stopPropagation();
                                        openEditDeck(deck);
                                    }}
                                    class="deck-action-btn"
                                    aria-label="編輯卡組"
                                >
                                    <svg
                                        class="w-4 h-4"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                        stroke-width="1.5"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Z"
                                        />
                                    </svg>
                                </button>
                                <button
                                    type="button"
                                    onclick={(event) => {
                                        event.stopPropagation();
                                        handleDeleteDeck(deck.id);
                                    }}
                                    class="deck-action-btn deck-action-btn-danger"
                                    aria-label="刪除卡組"
                                >
                                    <svg
                                        class="w-4 h-4"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                        stroke-width="1.5"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                                        />
                                    </svg>
                                </button>
                            </div>
                        </div>
                    {/each}
                </div>

                {#if selectedDeck}
                    <div class="deck-footer">
                        <button
                            type="button"
                            onclick={handleStartCustomDeck}
                            disabled={customDueCount === 0 ||
                                !vocab.index ||
                                vocab.index.length === 0}
                            class="btn-start-secondary"
                        >
                            {#if customDueCount > 0}
                                開始練習
                                <span class="btn-start-count"
                                    >{customDueCount} 張</span
                                >
                            {:else}
                                今日完成
                            {/if}
                        </button>
                    </div>
                {/if}
            {/if}
        </div>
    </div>
</div>

{#if app.isMobile}
    <BottomSheet isOpen={isDeckModalOpen} onClose={handleModalClose}>
        <DeckEditor
            initialName={editingDeck?.name ?? `卡組 ${customDecks.length + 1}`}
            initialLemmas={editingDeck?.lemmas ?? []}
            onSave={handleDeckSave}
            onCancel={handleModalClose}
            isEditing={!!editingDeckId}
        />
    </BottomSheet>
{:else if isDeckModalOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="modal-backdrop" onclick={handleModalClose} role="presentation">
        <div
            class="modal-container"
            onclick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            tabindex="-1"
        >
            <DeckEditor
                initialName={editingDeck?.name ??
                    `卡組 ${customDecks.length + 1}`}
                initialLemmas={editingDeck?.lemmas ?? []}
                onSave={handleDeckSave}
                onCancel={handleModalClose}
                isEditing={!!editingDeckId}
            />
        </div>
    </div>
{/if}

{#snippet settingsContent()}
    <div class="space-y-5">
        <div
            class="flex items-center justify-between p-3 bg-surface-page/60 rounded-lg"
        >
            <div>
                <span class="text-sm font-medium text-content-primary"
                    >智慧排序</span
                >
                <p class="text-xs text-content-tertiary mt-0.5">
                    {smartMode ? "依重要程度排序新卡片" : "隨機順序呈現新卡片"}
                </p>
            </div>
            <button
                type="button"
                onclick={() => (smartMode = !smartMode)}
                class="relative w-10 h-6 rounded-full transition-colors {smartMode
                    ? 'bg-accent'
                    : 'bg-border'}"
                role="switch"
                aria-checked={smartMode}
                aria-label="智慧排序"
            >
                <span
                    class="absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-sm transition-transform {smartMode
                        ? 'translate-x-4'
                        : 'translate-x-0'}"
                ></span>
            </button>
        </div>

        <div class="slider-field">
            <div class="slider-header">
                <label
                    for="new-card-limit"
                    class="text-sm font-medium text-content-secondary"
                >
                    每日新卡片
                </label>
                <span class="slider-value">{newCardLimit}</span>
            </div>
            <input
                id="new-card-limit"
                type="range"
                bind:value={newCardLimit}
                min="0"
                max="50"
                step="5"
                class="slider-input"
            />
            <div class="slider-labels">
                <span>0</span>
                <span>50</span>
            </div>
        </div>

        <div class="space-y-2.5">
            <label class="flex items-center gap-3 cursor-pointer group">
                <input
                    type="checkbox"
                    bind:checked={autoSpeak}
                    class="w-4 h-4 rounded border-border-hover text-accent focus:ring-0 focus:ring-offset-0"
                />
                <span
                    class="text-sm text-content-secondary group-hover:text-content-primary transition-colors"
                >
                    自動朗讀單字
                </span>
            </label>
        </div>
    </div>
{/snippet}

<style>
    /* Layout */
    .dashboard-layout {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    @media (min-width: 1024px) {
        .dashboard-layout {
            display: grid;
            grid-template-columns: 1fr 320px;
            gap: 1.25rem;
            align-items: start;
        }
    }

    .main-card {
        min-width: 0;
    }

    /* Stats Section */
    .stats-section {
        margin-bottom: 1.5rem;
    }

    .stats-hero {
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }

    .stats-hero-number {
        font-size: 3.5rem;
        font-weight: 600;
        line-height: 1;
        letter-spacing: -0.03em;
        color: var(--color-content-primary);
    }

    .stats-hero-label {
        font-size: 1.125rem;
        color: var(--color-content-tertiary);
    }

    .stats-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem 1.25rem;
    }

    .stats-item {
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }

    .stats-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .stats-dot-review {
        background-color: var(--color-srs-again);
        opacity: 0.7;
    }

    .stats-dot-learning {
        background-color: var(--color-srs-hard);
        opacity: 0.7;
    }

    .stats-dot-new {
        background-color: var(--color-srs-easy);
        opacity: 0.7;
    }

    .stats-dot-mastered {
        background-color: var(--color-srs-good);
        opacity: 0.7;
    }

    .stats-value {
        font-size: 0.9375rem;
        font-weight: 600;
        color: var(--color-content-primary);
    }

    .stats-label {
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
    }

    /* Buttons */
    .btn-start {
        width: 100%;
        padding: 0.875rem 1.25rem;
        background-color: var(--color-content-primary);
        color: white;
        border-radius: 0.5rem;
        font-size: 1rem;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.15s ease;
    }

    .btn-start:hover:not(:disabled) {
        background-color: var(--color-content-primary-hover);
    }

    .btn-start:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-start-secondary {
        width: 100%;
        padding: 0.625rem 1rem;
        background-color: var(--color-surface-page);
        color: var(--color-content-primary);
        border: 1px solid var(--color-border);
        border-radius: 0.5rem;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s ease;
    }

    .btn-start-secondary:hover:not(:disabled) {
        background-color: var(--color-surface-hover);
        border-color: var(--color-border-hover);
    }

    .btn-start-secondary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-start-count {
        margin-left: 0.375rem;
        opacity: 0.6;
    }

    .btn-text {
        font-size: 0.875rem;
        color: var(--color-content-secondary);
        cursor: pointer;
        transition: color 0.15s ease;
    }

    .btn-text:hover {
        color: var(--color-content-primary);
    }

    .settings-toggle {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.625rem 0.25rem;
        font-size: 0.875rem;
        color: var(--color-content-secondary);
        cursor: pointer;
        transition: color 0.15s ease;
        margin-bottom: 1rem;
    }

    .settings-toggle:hover {
        color: var(--color-content-primary);
    }

    /* Deck Card */
    .deck-card {
        display: flex;
        flex-direction: column;
    }

    .deck-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--color-border);
    }

    .deck-body {
        flex: 1;
        padding: 1rem;
        overflow-y: auto;
    }

    .deck-footer {
        padding: 1rem;
        margin-top: 0.5rem;
        border-top: 1px solid var(--color-border);
    }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem 1rem;
        text-align: center;
    }

    .empty-state-icon {
        width: 3rem;
        height: 3rem;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--color-surface-page);
        border-radius: 50%;
        color: var(--color-content-tertiary);
        margin-bottom: 0.75rem;
    }

    .deck-list {
        display: flex;
        flex-direction: column;
        gap: 0.375rem;
    }

    .deck-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        width: 100%;
        padding: 0.625rem 0.75rem;
        border-radius: 0.375rem;
        background-color: transparent;
        text-align: left;
        cursor: pointer;
        transition: background-color 0.15s ease;
        animation: slideIn 0.2s ease-out;
        animation-fill-mode: both;
    }

    .deck-item:nth-child(1) {
        animation-delay: 0ms;
    }
    .deck-item:nth-child(2) {
        animation-delay: 30ms;
    }
    .deck-item:nth-child(3) {
        animation-delay: 60ms;
    }
    .deck-item:nth-child(4) {
        animation-delay: 90ms;
    }
    .deck-item:nth-child(5) {
        animation-delay: 120ms;
    }
    .deck-item:nth-child(n + 6) {
        animation-delay: 150ms;
    }

    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-8px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    .deck-item:hover {
        background-color: var(--color-surface-hover);
    }

    .deck-item-selected {
        background-color: var(--color-surface-page);
    }

    .deck-item-selected:hover {
        background-color: var(--color-surface-page);
    }

    .deck-content {
        flex: 1;
        min-width: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
    }

    .deck-name {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--color-content-primary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .deck-meta {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
        flex-shrink: 0;
    }

    .deck-progress-learned {
        color: var(--color-content-secondary);
        font-weight: 500;
    }

    .deck-progress-sep {
        opacity: 0.4;
        margin: 0 2px;
    }

    .deck-actions {
        display: flex;
        align-items: center;
        gap: 0.125rem;
        opacity: 0;
        transition: opacity 0.15s ease;
    }

    .deck-item:hover .deck-actions {
        opacity: 1;
    }

    @media (hover: none) {
        .deck-actions {
            opacity: 1;
        }
    }

    .deck-action-btn {
        padding: 0.375rem;
        border-radius: 0.375rem;
        color: var(--color-content-tertiary);
        cursor: pointer;
        transition: all 0.15s ease;
    }

    .deck-action-btn:hover {
        color: var(--color-content-primary);
        background-color: var(--color-surface-hover);
    }

    .deck-action-btn-danger:hover {
        color: var(--color-srs-again);
        background-color: var(--color-srs-again-soft);
    }

    /* Slider */
    .slider-field {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .slider-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .slider-value {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--color-content-primary);
        min-width: 1.5rem;
        text-align: right;
    }

    .slider-input {
        -webkit-appearance: none;
        appearance: none;
        width: 100%;
        height: 6px;
        background: var(--color-border);
        border-radius: 3px;
        cursor: pointer;
        transition: background 0.15s ease;
    }

    .slider-input:hover {
        background: var(--color-border-hover);
    }

    .slider-input::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 18px;
        height: 18px;
        background: var(--color-content-primary);
        border-radius: 50%;
        cursor: pointer;
        transition:
            transform 0.15s ease,
            box-shadow 0.15s ease;
    }

    .slider-input::-webkit-slider-thumb:hover {
        transform: scale(1.15);
        box-shadow: 0 0 0 4px var(--color-surface-hover);
    }

    .slider-input::-moz-range-thumb {
        width: 18px;
        height: 18px;
        background: var(--color-content-primary);
        border: none;
        border-radius: 50%;
        cursor: pointer;
        transition:
            transform 0.15s ease,
            box-shadow 0.15s ease;
    }

    .slider-input::-moz-range-thumb:hover {
        transform: scale(1.15);
        box-shadow: 0 0 0 4px var(--color-surface-hover);
    }

    .slider-input::-moz-range-track {
        background: transparent;
    }

    .slider-labels {
        display: flex;
        justify-content: space-between;
        font-size: 0.6875rem;
        color: var(--color-content-tertiary);
    }

    /* Modal */
    .modal-backdrop {
        position: fixed;
        inset: 0;
        z-index: 100;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(0, 0, 0, 0.3);
    }

    .modal-container {
        width: 100%;
        max-width: 420px;
        max-height: calc(100vh - 80px);
        background-color: var(--color-surface-primary);
        border-radius: 0.75rem;
        box-shadow: var(--shadow-float);
        overflow: hidden;
    }
</style>
