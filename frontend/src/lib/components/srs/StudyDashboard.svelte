<script lang="ts">
    import { browser } from '$app/environment';
    import { safeGetItem, safeSetItem } from '$lib/utils/safe-storage';
    import {
        ensureEntryCard,
        getSessionCardCounts,
        type SessionOptions,
    } from "$lib/stores/srs.svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { getAppStore } from "$lib/stores/app.svelte";
    import {
        getAllCards,
        getTodayStats,
        onDataChange,
    } from "$lib/stores/srs-storage";
    import { getSRSEligibleEntryCached } from "$lib/stores/vocab-db";
    import { State } from "ts-fsrs";
    import HelpTooltip from "$lib/components/ui/HelpTooltip.svelte";
    import BottomSheet from "$lib/components/ui/BottomSheet.svelte";
    import DeckEditor from "./DeckEditor.svelte";
    import { onDestroy } from "svelte";
    import { STORAGE_KEYS } from "$lib/storage-keys";
    import { isWordIndexItem } from "$lib/types/vocab";

    import type { SRSCard } from "$lib/types/srs";

    interface Props {
        onStart: (options: SessionOptions) => void;
    }

    let { onStart }: Props = $props();

    const vocab = getVocabStore();
    const app = getAppStore();

    const LEVEL_OPTIONS = [1, 2, 3, 4, 5, 6] as const;

    export type StudyPriority = "mixed" | "new_first" | "review_first";
    export type VocabTypeFilter = "all" | "word" | "phrase";

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
        levelFilter: number[];
        studyPriority: StudyPriority;
        vocabTypeFilter: VocabTypeFilter;
    }

    const defaultSettings: StudySettings = {
        newCardLimit: 20,
        autoSpeak: true,
        smartMode: true,
        levelFilter: [],
        studyPriority: "mixed",
        vocabTypeFilter: "all",
    };

    let newCardLimit = $state(defaultSettings.newCardLimit);
    let autoSpeak = $state(defaultSettings.autoSpeak);
    let smartMode = $state(defaultSettings.smartMode);
    let levelFilter: number[] = $state(defaultSettings.levelFilter);
    let studyPriority: StudyPriority = $state(defaultSettings.studyPriority);
    let vocabTypeFilter: VocabTypeFilter = $state(defaultSettings.vocabTypeFilter);
    let showSettings = $state(false);
    let isCustomDeckLoaded = $state(false);
    let todayNewCardsStudied = $state(0);

    let customDecks: CustomDeck[] = $state([]);
    let selectedDeckId: string | null = $state(null);
    let isDeckModalOpen = $state(false);
    let editingDeckId: string | null = $state(null);
    let dataVersion = $state(0);

    const unsubscribeDataChange = onDataChange(() => {
        dataVersion++;
        loadTodayStats();
    });

    onDestroy(() => {
        unsubscribeDataChange();
    });

    function loadSettings(): void {
        if (!browser) return;
        try {
            const saved = safeGetItem(STORAGE_KEYS.STUDY_SETTINGS);
            if (saved) {
                const settings: StudySettings = JSON.parse(saved);
                newCardLimit =
                    settings.newCardLimit ?? defaultSettings.newCardLimit;
                autoSpeak = settings.autoSpeak ?? defaultSettings.autoSpeak;
                smartMode = settings.smartMode ?? defaultSettings.smartMode;
                levelFilter =
                    settings.levelFilter ?? defaultSettings.levelFilter;
                studyPriority =
                    settings.studyPriority ?? defaultSettings.studyPriority;
                vocabTypeFilter =
                    settings.vocabTypeFilter ?? defaultSettings.vocabTypeFilter;
            }
        } catch {
            // ignore
        }
    }

    function saveSettings(): void {
        if (!browser) return;
        try {
            const settings: StudySettings = {
                newCardLimit,
                autoSpeak,
                smartMode,
                levelFilter,
                studyPriority,
                vocabTypeFilter,
            };
            safeSetItem(
                STORAGE_KEYS.STUDY_SETTINGS,
                JSON.stringify(settings),
            );
        } catch {
            // ignore
        }
    }

    async function loadTodayStats(): Promise<void> {
        try {
            const stats = await getTodayStats();
            todayNewCardsStudied = stats.new_cards;
        } catch {
            todayNewCardsStudied = 0;
        }
    }

    function toggleLevelFilter(level: number): void {
        if (levelFilter.includes(level)) {
            levelFilter = levelFilter.filter((l) => l !== level);
        } else {
            levelFilter = [...levelFilter, level];
        }
    }

    loadSettings();
    loadTodayStats();

    $effect(() => {
        newCardLimit;
        autoSpeak;
        smartMode;
        levelFilter;
        studyPriority;
        vocabTypeFilter;
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
        if (!browser) return;
        try {
            safeSetItem(
                STORAGE_KEYS.CUSTOM_DECKS,
                JSON.stringify(decks),
            );
        } catch (err) {
            console.warn("Failed to save custom decks", err);
        }
    }

    function loadCustomDecks(): void {
        if (!browser) return;
        try {
            const saved = safeGetItem(STORAGE_KEYS.CUSTOM_DECKS);
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
        for (const lemma of newOnes) {
            const entry = getSRSEligibleEntryCached(lemma);
            if (entry) {
                ensureEntryCard(entry);
            }
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

    const allCardsSnapshot = $derived.by(() => {
        dataVersion;
        return getAllCards();
    });

    const existingLemmaSet = $derived.by(() => {
        return new Set(allCardsSnapshot.map((c) => c.lemma));
    });

    const learnedLemmaSet = $derived.by(() => {
        const set = new Set<string>();
        for (const card of allCardsSnapshot) {
            if (card.state !== State.New) {
                set.add(card.lemma);
            }
        }
        return set;
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
        // Include lemmas that are not yet learned
        return selectedDeck.lemmas.filter((lemma) => !learnedLemmaSet.has(lemma));
    });

    const deckLearnedCountMap = $derived.by(() => {
        const map = new Map<string, number>();
        for (const deck of customDecks) {
            let count = 0;
            for (const lemma of deck.lemmas) {
                if (learnedLemmaSet.has(lemma)) count++;
            }
            map.set(deck.id, count);
        }
        return map;
    });

    const learnedLemmaCount = $derived(learnedLemmaSet.size);

    const filteredNewCardPool = $derived.by(() => {
        let pool = vocab.index || [];

        // Only include words and phrases (patterns are not SRS eligible)
        pool = pool.filter((w) => w.type === "word" || w.type === "phrase");

        // Apply vocab type filter
        if (vocabTypeFilter !== "all") {
            pool = pool.filter((w) => w.type === vocabTypeFilter);
        }

        // Exclude already learned (non-New state) lemmas
        pool = pool.filter((w) => !learnedLemmaSet.has(w.lemma));
        pool = pool.filter((w) => !isWordIndexItem(w) || w.primary_pos !== "PROPN");

        // Level filter only applies to words (phrases don't have levels)
        if (levelFilter.length > 0) {
            pool = pool.filter(
                (w) => !isWordIndexItem(w) || (w.level !== null && levelFilter.includes(w.level)),
            );
        }

        if (smartMode) {
            pool = pool.sort((a, b) => {
                const aScore = "importance_score" in a ? a.importance_score : 0;
                const bScore = "importance_score" in b ? b.importance_score : 0;
                return bScore - aScore;
            });
        }

        return pool.map((w) => w.lemma);
    });

    const isUnlimited = $derived(newCardLimit >= 55);

    const excludedLemmas = $derived.by(() => {
        const propnLemmas = (vocab.index || [])
            .filter((w) => isWordIndexItem(w) && w.primary_pos === "PROPN")
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

    const actualNewCardLimit = $derived.by(() => {
        if (isUnlimited) {
            return Math.min(20, filteredNewCardPool.length);
        }
        return Math.max(0, newCardLimit - todayNewCardsStudied);
    });

    const sessionOptions = $derived.by<SessionOptions>(() => ({
        newLimit: actualNewCardLimit,
        selectionPool: filteredNewCardPool,
        excludeLemmas: excludedLemmas,
        priority: studyPriority,
        isCustomDeck: false,
    }));

    const sessionCounts = $derived.by(() => {
        const baseCounts = getSessionCardCounts(sessionOptions);
        const newCount = Math.min(actualNewCardLimit, filteredNewCardPool.length);
        return {
            newCount,
            learningCount: baseCounts.learningCount,
            reviewCount: baseCounts.reviewCount,
            total: baseCounts.learningCount + baseCounts.reviewCount + newCount,
        };
    });

    const customDeckSessionOptions = $derived.by<SessionOptions | null>(() => {
        if (!selectedDeck) return null;
        return {
            newLimit: customNewCardPool.length,
            selectionPool: customNewCardPool,
            excludeLemmas: customExcludedLemmas,
            priority: studyPriority,
            isCustomDeck: true,
        };
    });

    const customDeckSessionCounts = $derived.by(() => {
        if (!customDeckSessionOptions) return null;
        const baseCounts = getSessionCardCounts(customDeckSessionOptions);
        const newCount = customNewCardPool.length;
        return {
            newCount,
            learningCount: baseCounts.learningCount,
            reviewCount: baseCounts.reviewCount,
            total: baseCounts.learningCount + baseCounts.reviewCount + newCount,
        };
    });

    const hasCardsToStudy = $derived(sessionCounts.total > 0);

    function handleStart() {
        const poolLemmas = filteredNewCardPool.slice(0, actualNewCardLimit);
        const newCards: SRSCard[] = [];
        for (const lemma of poolLemmas) {
            const entry = getSRSEligibleEntryCached(lemma);
            if (entry) {
                const card = ensureEntryCard(entry);
                if (card) {
                    newCards.push(card);
                }
            }
        }
        onStart({ ...sessionOptions, newCards });
    }

    function handleStartCustomDeck() {
        if (!customDeckSessionOptions) return;
        const newCards: SRSCard[] = [];
        for (const lemma of customNewCardPool) {
            const entry = getSRSEligibleEntryCached(lemma);
            if (entry) {
                const card = ensureEntryCard(entry);
                if (card) {
                    newCards.push(card);
                }
            }
        }
        onStart({ ...customDeckSessionOptions, newCards });
    }

    function handleCramDeck() {
        if (!selectedDeck) return;
        onStart({
            newLimit: 0,
            excludeLemmas: customExcludedLemmas,
            cramMode: true,
        });
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
                <div class="stats-hero-number">{sessionCounts.total}</div>
                <div class="stats-hero-label">張卡片</div>
            </div>

            <div class="stats-row">
                <div class="stats-item">
                    <span class="stats-dot stats-dot-review"></span>
                    <span class="stats-value">{sessionCounts.reviewCount}</span>
                    <span class="stats-label">複習</span>
                    <HelpTooltip text="已記住的卡片，到了預定的複習時間" />
                </div>
                <div class="stats-item">
                    <span class="stats-dot stats-dot-learning"></span>
                    <span class="stats-value"
                        >{sessionCounts.learningCount}</span
                    >
                    <span class="stats-label">熟悉中</span>
                    <HelpTooltip
                        text="正在學習的卡片，需要多次練習來鞏固記憶"
                    />
                </div>
                <div class="stats-item">
                    <span class="stats-dot stats-dot-new"></span>
                    <span class="stats-value">{sessionCounts.newCount}</span>
                    <span class="stats-label">新單字</span>
                    <HelpTooltip text="尚未開始學習的新卡片" />
                </div>
                <div class="stats-item">
                    <span class="stats-dot stats-dot-mastered"></span>
                    <span class="stats-value">{learnedLemmaCount}</span>
                    <span class="stats-label">累計</span>
                    <HelpTooltip text="曾經學習過的單字總數（包含複習和熟悉中）" />
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
                        <div class="deck-footer-buttons">
                            <button
                                type="button"
                                onclick={handleStartCustomDeck}
                                disabled={!customDeckSessionCounts ||
                                    customDeckSessionCounts.total === 0 ||
                                    !vocab.index ||
                                    vocab.index.length === 0}
                                class="btn-start-secondary"
                            >
                                {#if customDeckSessionCounts && customDeckSessionCounts.total > 0}
                                    開始練習
                                    <span class="btn-start-count"
                                        >{customDeckSessionCounts.total} 張</span
                                    >
                                {:else}
                                    今日完成
                                {/if}
                            </button>
                            <button
                                type="button"
                                onclick={handleCramDeck}
                                disabled={!vocab.index ||
                                    vocab.index.length === 0 ||
                                    selectedDeck.lemmas.length === 0}
                                class="btn-cram"
                            >
                                抱佛腳
                            </button>
                        </div>
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
    <div class="settings-grid">
        <div class="setting-group">
            <h4 class="setting-group-title">新卡片設定</h4>

            <div class="setting-row">
                <div class="setting-row-label">
                    <span>每日上限</span>
                    <HelpTooltip text="每天最多學習的新卡片數量" />
                </div>
                <div class="setting-row-control">
                    <input
                        id="new-card-limit"
                        type="range"
                        bind:value={newCardLimit}
                        min="0"
                        max="55"
                        step="5"
                        class="slider-input"
                    />
                    <span class="slider-value"
                        >{newCardLimit >= 55 ? "∞" : newCardLimit}</span
                    >
                </div>
                {#if todayNewCardsStudied > 0 && !isUnlimited}
                    <p class="setting-row-hint full-width">
                        今日已學習 {todayNewCardsStudied} 張，剩餘 {actualNewCardLimit}
                        張
                    </p>
                {/if}
            </div>

            <div class="setting-row">
                <div class="setting-row-label">
                    <span>詞彙等級</span>
                    <HelpTooltip text="限制新卡片範圍為特定等級" />
                </div>
                <div class="setting-row-control">
                    <div class="chip-group">
                        {#each LEVEL_OPTIONS as level}
                            <button
                                type="button"
                                class="chip"
                                class:chip-active={levelFilter.includes(level)}
                                onclick={() => toggleLevelFilter(level)}
                            >
                                {level}
                            </button>
                        {/each}
                    </div>
                </div>
                <p class="setting-row-hint full-width">
                    {#if levelFilter.length === 0}
                        不限制等級
                    {:else}
                        僅學習等級 {[...levelFilter]
                            .sort((a, b) => a - b)
                            .join("、")} 的單字
                    {/if}
                </p>
            </div>

            <div class="setting-row">
                <div class="setting-row-label">
                    <span>詞彙類型</span>
                    <HelpTooltip text="限制新卡片範圍為單字或片語" />
                </div>
                <div class="setting-row-control full-width">
                    <div class="segmented-control">
                        <button
                            type="button"
                            class="segment"
                            class:segment-active={vocabTypeFilter === "all"}
                            onclick={() => (vocabTypeFilter = "all")}
                        >
                            全部
                        </button>
                        <button
                            type="button"
                            class="segment"
                            class:segment-active={vocabTypeFilter === "word"}
                            onclick={() => (vocabTypeFilter = "word")}
                        >
                            單字
                        </button>
                        <button
                            type="button"
                            class="segment"
                            class:segment-active={vocabTypeFilter === "phrase"}
                            onclick={() => (vocabTypeFilter = "phrase")}
                        >
                            片語
                        </button>
                    </div>
                </div>
            </div>

            <div class="setting-row">
                <div class="setting-row-label">
                    <span>智慧排序</span>
                    <HelpTooltip
                        text="依重要程度排序新卡片，優先學習高頻詞彙"
                    />
                </div>
                <div class="setting-row-control">
                    <button
                        type="button"
                        onclick={() => (smartMode = !smartMode)}
                        class="toggle"
                        class:toggle-active={smartMode}
                        role="switch"
                        aria-checked={smartMode}
                        aria-label="智慧排序"
                    >
                        <span class="toggle-thumb"></span>
                    </button>
                </div>
            </div>
        </div>

        <div class="setting-group">
            <h4 class="setting-group-title">學習偏好</h4>

            <div class="setting-row">
                <div class="setting-row-label">
                    <span>學習順序</span>
                    <HelpTooltip text="決定練習時優先出現的卡片類型" />
                </div>
                <div class="setting-row-control full-width">
                    <div class="segmented-control">
                        <button
                            type="button"
                            class="segment"
                            class:segment-active={studyPriority ===
                                "review_first"}
                            onclick={() => (studyPriority = "review_first")}
                        >
                            複習優先
                        </button>
                        <button
                            type="button"
                            class="segment"
                            class:segment-active={studyPriority === "mixed"}
                            onclick={() => (studyPriority = "mixed")}
                        >
                            混合
                        </button>
                        <button
                            type="button"
                            class="segment"
                            class:segment-active={studyPriority === "new_first"}
                            onclick={() => (studyPriority = "new_first")}
                        >
                            新卡優先
                        </button>
                    </div>
                </div>
            </div>

            <div class="setting-row">
                <div class="setting-row-label">
                    <span>自動朗讀</span>
                    <HelpTooltip text="顯示卡片時自動播放單字發音" />
                </div>
                <div class="setting-row-control">
                    <button
                        type="button"
                        onclick={() => (autoSpeak = !autoSpeak)}
                        class="toggle"
                        class:toggle-active={autoSpeak}
                        role="switch"
                        aria-checked={autoSpeak}
                        aria-label="自動朗讀"
                    >
                        <span class="toggle-thumb"></span>
                    </button>
                </div>
            </div>
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

    .deck-footer-buttons {
        display: flex;
        gap: 0.5rem;
    }

    .btn-cram {
        padding: 0.625rem 1rem;
        background-color: transparent;
        color: var(--color-content-secondary);
        border: 1px solid var(--color-border);
        border-radius: 0.5rem;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s ease;
        white-space: nowrap;
    }

    .btn-cram:hover:not(:disabled) {
        background-color: var(--color-surface-hover);
        border-color: var(--color-border-hover);
        color: var(--color-content-primary);
    }

    .btn-cram:disabled {
        opacity: 0.5;
        cursor: not-allowed;
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
        overflow: visible;
    }

    /* Settings Grid */
    .settings-grid {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    .setting-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .setting-group:not(:first-child) {
        padding-top: 1rem;
        border-top: 1px solid var(--color-border);
    }

    .setting-group-title {
        font-size: 0.8125rem;
        font-weight: 600;
        color: var(--color-section-header);
        margin: 0;
    }

    .setting-row {
        display: grid;
        grid-template-columns: 1fr auto;
        align-items: center;
        gap: 0.5rem 1rem;
        padding: 0.5rem 0;
    }

    .setting-row-label {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        font-size: 0.875rem;
        color: var(--color-content-primary);
    }

    .setting-row-control {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        justify-content: flex-end;
    }

    .setting-row-control.full-width {
        grid-column: 1 / -1;
        justify-content: stretch;
    }

    .setting-row-hint {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
        margin: 0;
    }

    .setting-row-hint.full-width {
        grid-column: 1 / -1;
    }

    /* Toggle Switch */
    .toggle {
        position: relative;
        width: 2rem;
        height: 1.125rem;
        background-color: var(--color-border-hover);
        border-radius: 0.5625rem;
        cursor: pointer;
        transition: background-color 0.15s ease;
        flex-shrink: 0;
    }

    .toggle-active {
        background-color: var(--color-content-primary);
    }

    .toggle-thumb {
        position: absolute;
        top: 0.1875rem;
        left: 0.1875rem;
        width: 0.75rem;
        height: 0.75rem;
        background-color: white;
        border-radius: 50%;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        transition: transform 0.15s ease;
    }

    .toggle-active .toggle-thumb {
        transform: translateX(0.875rem);
    }

    /* Chip Group */
    .chip-group {
        display: flex;
        gap: 0.25rem;
    }

    .chip {
        min-width: 1.75rem;
        height: 1.75rem;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--color-surface-page);
        border-radius: 4px;
        font-weight: 500;
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
        transition: all 0.15s ease;
        cursor: pointer;
        border: 1px solid transparent;
    }

    .chip:hover {
        background-color: var(--color-surface-hover);
        color: var(--color-content-secondary);
    }

    .chip-active {
        background-color: var(--color-accent-soft);
        color: var(--color-accent);
    }

    .chip-active:hover {
        background-color: var(--color-accent-soft);
        color: var(--color-accent);
    }

    /* Segmented Control */
    .segmented-control {
        display: flex;
        background-color: var(--color-surface-page);
        border-radius: 6px;
        padding: 0.25rem;
        gap: 0.25rem;
        width: 100%;
    }

    .segment {
        flex: 1;
        padding: 0.5rem 0.75rem;
        background-color: transparent;
        border-radius: 4px;
        font-weight: 500;
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
        transition: all 0.15s ease;
        cursor: pointer;
        text-align: center;
        white-space: nowrap;
    }

    .segment:hover:not(.segment-active) {
        color: var(--color-content-secondary);
    }

    .segment-active {
        background-color: var(--color-surface-primary);
        color: var(--color-content-primary);
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
    }

    /* Slider */
    .slider-input {
        -webkit-appearance: none;
        appearance: none;
        flex: 1;
        height: 4px;
        background: var(--color-border);
        border-radius: 2px;
        cursor: pointer;
        min-width: 80px;
    }

    .slider-input::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 14px;
        height: 14px;
        background: var(--color-content-primary);
        border-radius: 50%;
        cursor: pointer;
        transition: transform 0.1s ease;
    }

    .slider-input::-webkit-slider-thumb:hover {
        transform: scale(1.15);
    }

    .slider-input::-moz-range-thumb {
        width: 14px;
        height: 14px;
        background: var(--color-content-primary);
        border: none;
        border-radius: 50%;
        cursor: pointer;
    }

    .slider-input::-moz-range-track {
        background: transparent;
    }

    .slider-value {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--color-content-primary);
        min-width: 1.5rem;
        text-align: right;
    }
</style>
