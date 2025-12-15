<script lang="ts">
    import { addWordsToSRS, getSRSStore } from "$lib/stores/srs.svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { getAppStore } from "$lib/stores/app.svelte";
    import { getNewCards, getAllCards } from "$lib/stores/srs-storage";
    import { State } from "ts-fsrs";
    import HelpTooltip from "$lib/components/ui/HelpTooltip.svelte";
    import BottomSheet from "$lib/components/ui/BottomSheet.svelte";

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
    const SEPARATOR_PATTERN = /[\s,，、;；]+/;
    const CUSTOM_PREVIEW_LIMIT = 18;

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
    let deckNameInput = $state("");
    let deckInput = $state("");
    let deckStatus: string | null = $state(null);

    function loadSettings(): void {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const settings: StudySettings = JSON.parse(saved);
                newCardLimit = settings.newCardLimit ?? defaultSettings.newCardLimit;
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
                                id: crypto.randomUUID?.() ?? `deck-${Date.now()}`,
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

    function parseDeckInput(): string[] {
        const parts = deckInput
            .split(SEPARATOR_PATTERN)
            .map((p) => p.trim())
            .filter(Boolean);
        return normalizeLemmaList(parts);
    }

    function upsertDeck(): void {
        if (vocabLemmaMap.size === 0) {
            deckStatus = "單字表尚未載入完成";
            return;
        }
        const name = deckNameInput.trim();
        if (!name) {
            deckStatus = "請輸入卡組名稱";
            return;
        }
        const lemmas = parseDeckInput();
        if (lemmas.length === 0) {
            deckStatus = "找不到有效的單字，請用逗號或換行分隔";
            return;
        }

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
            deckId = crypto.randomUUID?.() ?? `deck-${now}-${Math.random().toString(36).slice(2, 8)}`;
            decks.push({ id: deckId, name, lemmas, createdAt: now });
        }

        const newOnes = lemmas.filter((lemma) => !existingLemmaSet.has(lemma));
        if (newOnes.length > 0) {
            addWordsToSRS(newOnes);
        }

        customDecks = decks;
        selectedDeckId = deckId;
        saveCustomDecks(decks);
        deckStatus = null;
        isDeckModalOpen = false;
    }

    function openCreateDeck(): void {
        editingDeckId = null;
        deckNameInput = `卡組 ${customDecks.length + 1}`;
        deckInput = "";
        deckStatus = null;
        isDeckModalOpen = true;
    }

    function openEditDeck(deck: CustomDeck): void {
        editingDeckId = deck.id;
        deckNameInput = deck.name;
        deckInput = deck.lemmas.join(", ");
        deckStatus = null;
        isDeckModalOpen = true;
    }

    function handleDeleteDeck(deckId: string): void {
        customDecks = customDecks.filter((d) => d.id !== deckId);
        if (selectedDeckId === deckId) {
            selectedDeckId = customDecks[0]?.id ?? null;
        }
        saveCustomDecks(customDecks);
    }

    const newCardLemmas = $derived.by(() => {
        return new Set(getNewCards().map((c) => c.lemma));
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

    const customDeckSet = $derived.by(() => {
        return new Set(selectedDeck?.lemmas ?? []);
    });

    const customNewCardPool = $derived.by(() => {
        if (!selectedDeck) return [];
        const newSet = new Set(getNewCards().map((c) => c.lemma));
        return selectedDeck.lemmas.filter((lemma) => newSet.has(lemma));
    });

    const customDeckPreview = $derived((selectedDeck?.lemmas ?? []).slice(0, CUSTOM_PREVIEW_LIMIT));

    const deckNewCountMap = $derived.by(() => {
        const set = new Set(getNewCards().map((c) => c.lemma));
        const map = new Map<string, number>();
        for (const deck of customDecks) {
            let count = 0;
            for (const lemma of deck.lemmas) {
                if (set.has(lemma)) count++;
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
        srs.deckStats.reviewCount +
            srs.deckStats.learningCount +
            actualNewCardCount,
    );

    const hasCardsToStudy = $derived(
        srs.deckStats.reviewCount > 0 ||
            srs.deckStats.learningCount > 0 ||
            filteredNewCardPool.length > 0,
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

<div class="flex flex-col lg:flex-row gap-5">
    <div
        class="bg-surface-primary rounded-lg border border-border p-6 lg:p-8 flex-[1.5]"
    >
        <h2
            class="text-xl lg:text-2xl font-semibold tracking-tight text-content-primary mb-8"
        >
            今日學習
        </h2>

        <div class="grid grid-cols-4 gap-3 lg:gap-4 mb-8">
            <div class="text-center py-4 lg:py-5 px-2 rounded-lg bg-surface-page/60">
                <div class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight leading-none">
                    {srs.deckStats.reviewCount}
                </div>
                <div class="flex items-center justify-center gap-1 text-xs lg:text-sm text-content-secondary mt-1.5">
                    <span>待複習</span>
                    <HelpTooltip text="已學會的卡片，到了排程的複習時間" />
                </div>
                <div class="w-1.5 h-1.5 rounded-full bg-srs-again/70 mx-auto mt-2.5"></div>
            </div>
            <div class="text-center py-4 lg:py-5 px-2 rounded-lg bg-surface-page/60">
                <div class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight leading-none">
                    {srs.deckStats.learningCount}
                </div>
                <div class="flex items-center justify-center gap-1 text-xs lg:text-sm text-content-secondary mt-1.5">
                    <span>學習中</span>
                    <HelpTooltip text="剛開始學的卡片，還在短間隔複習階段" />
                </div>
                <div class="w-1.5 h-1.5 rounded-full bg-srs-hard/70 mx-auto mt-2.5"></div>
            </div>
            <div class="text-center py-4 lg:py-5 px-2 rounded-lg bg-surface-page/60">
                <div class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight leading-none">
                    {filteredNewCardPool.length}
                </div>
                <div class="flex items-center justify-center gap-1 text-xs lg:text-sm text-content-secondary mt-1.5">
                    <span>新卡片</span>
                    <HelpTooltip text="從未學過的卡片" />
                </div>
                <div class="w-1.5 h-1.5 rounded-full bg-srs-easy/70 mx-auto mt-2.5"></div>
            </div>
            <div class="text-center py-4 lg:py-5 px-2 rounded-lg bg-surface-page/60">
                <div class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight leading-none">
                    {srs.deckStats.relearningCount}
                </div>
                <div class="flex items-center justify-center gap-1 text-xs lg:text-sm text-content-secondary mt-1.5">
                    <span>待鞏固</span>
                    <HelpTooltip text="複習時忘記了，需要重新鞏固記憶" />
                </div>
                <div class="w-1.5 h-1.5 rounded-full bg-srs-again/70 mx-auto mt-2.5"></div>
            </div>
        </div>

        <div class="mb-6 p-3 bg-surface-page/40 rounded-lg">
            <div class="flex items-center justify-between text-sm">
                <span class="text-content-tertiary">已學習詞彙</span>
                <span class="font-medium text-content-primary">{learnedLemmaCount} 個</span>
            </div>
        </div>

        {#if app.isMobile}
            <button
                onclick={() => (showSettings = !showSettings)}
                class="w-full flex items-center justify-between py-2.5 px-1 text-sm text-content-secondary hover:text-content-primary transition-colors rounded mb-4"
            >
                <span>學習設定</span>
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
            class="w-full py-3 px-5 bg-content-primary text-white rounded-lg text-base font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
        >
            {#if hasCardsToStudy}
                開始學習
                <span class="text-white/60 ml-1.5">約 {todayTotal} 張</span>
            {:else}
                今日已完成
            {/if}
        </button>

        {#if hasCardsToStudy}
            <div class="text-sm text-content-tertiary text-center mt-3">
                {#if srs.deckStats.learningCount > 0}
                    {srs.deckStats.learningCount} 張學習中
                {/if}
                {#if srs.deckStats.reviewCount > 0}
                    {#if srs.deckStats.learningCount > 0}+{/if}
                    {srs.deckStats.reviewCount} 張複習
                {/if}
                {#if actualNewCardCount > 0}
                    {#if srs.deckStats.learningCount > 0 || srs.deckStats.reviewCount > 0}+{/if}
                    最多 {actualNewCardCount} 張新卡片
                {/if}
            </div>
        {/if}

        <div class="mt-8 border-t border-border pt-6">
            <div class="flex items-center justify-between gap-3 mb-4">
                <div>
                    <h3 class="text-lg font-semibold tracking-tight text-content-primary">
                        自訂卡組（多課程）
                    </h3>
                    <p class="text-sm text-content-tertiary mt-1">
                        為不同課程建立卡組，學習紀錄與 SRS 排程同步。
                    </p>
                </div>
                <button
                    type="button"
                    onclick={openCreateDeck}
                    class="px-3 py-2 rounded-md bg-surface-page text-content-primary border border-border hover:border-border-hover transition-colors"
                >
                    新增卡組
                </button>
            </div>

            {#if customDecks.length === 0}
                <div class="text-sm text-content-tertiary bg-surface-page/60 border border-border rounded-lg p-4">
                    目前尚未建立卡組，點擊「新增卡組」開始設定你的課程。
                </div>
            {:else}
                <div class="space-y-3">
                    {#each customDecks as deck}
                        <div class="flex items-center gap-3 p-3 rounded-lg border {selectedDeckId === deck.id ? 'border-accent/60 bg-accent/5' : 'border-border bg-surface-page/60'}">
                            <label class="flex-1 flex items-center gap-3 cursor-pointer">
                                <input
                                    type="radio"
                                    name="custom-deck"
                                    value={deck.id}
                                    checked={selectedDeckId === deck.id}
                                    onclick={() => (selectedDeckId = deck.id)}
                                    class="w-4 h-4 accent-accent"
                                />
                                <div class="flex-1">
                                    <div class="flex items-center gap-2">
                                        <span class="text-sm font-medium text-content-primary">{deck.name}</span>
                                        <span class="text-[11px] px-2 py-0.5 rounded bg-surface-primary border border-border text-content-tertiary">
                                            {deck.lemmas.length} 詞
                                        </span>
                                        <span class="text-[11px] px-2 py-0.5 rounded bg-surface-primary border border-border text-srs-easy">
                                            新卡 {deckNewCountMap.get(deck.id) || 0}
                                        </span>
                                    </div>
                                    <div class="text-xs text-content-tertiary mt-1">
                                        {deck.lemmas.slice(0, 4).join("、")}{deck.lemmas.length > 4 ? "…" : ""}
                                    </div>
                                </div>
                            </label>
                            <div class="flex items-center gap-2">
                                <button
                                    type="button"
                                    onclick={(event) => {
                                        event.stopPropagation();
                                        openEditDeck(deck);
                                    }}
                                    class="px-2.5 py-1.5 text-xs rounded-md border border-border text-content-secondary hover:text-content-primary hover:border-border-hover transition-colors"
                                >
                                    編輯
                                </button>
                                <button
                                    type="button"
                                    onclick={(event) => {
                                        event.stopPropagation();
                                        handleDeleteDeck(deck.id);
                                    }}
                                    class="px-2.5 py-1.5 text-xs rounded-md text-content-tertiary hover:text-content-primary transition-colors"
                                >
                                    刪除
                                </button>
                            </div>
                        </div>
                    {/each}
                </div>

                {#if selectedDeck}
                    <div class="mt-4 flex items-center justify-between">
                        <div class="text-xs text-content-tertiary">
                            預覽：{customDeckPreview.join("、")}{selectedDeck.lemmas.length > customDeckPreview.length ? "…" : ""}
                        </div>
                        <button
                            type="button"
                            onclick={handleStartCustomDeck}
                            disabled={customNewCardPool.length === 0 || !vocab.index || vocab.index.length === 0}
                            class="px-3.5 py-2 rounded-md bg-content-primary text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            使用「{selectedDeck.name}」開始學習
                        </button>
                    </div>
                {/if}
            {/if}
        </div>
    </div>

    {#if !app.isMobile}
        <div
            class="bg-surface-primary rounded-lg border border-border p-6 lg:p-7 flex-1 max-w-md"
        >
            <h2
                class="text-lg font-semibold tracking-tight text-content-primary mb-5"
            >
                學習設定
            </h2>
            {@render settingsContent()}
        </div>
    {/if}
</div>

<BottomSheet isOpen={isDeckModalOpen} onClose={() => (isDeckModalOpen = false)}>
    {@render deckModalContent()}
</BottomSheet>

{#snippet deckModalContent()}
    <div class="py-4">
        <div class="flex items-center justify-between mb-3">
            <div>
                <h3 class="text-lg font-semibold text-content-primary">
                    {editingDeckId ? "編輯卡組" : "建立卡組"}
                </h3>
                <p class="text-sm text-content-tertiary mt-1">
                    以逗號、空格或換行分隔單字，會自動對齊字庫並去重。
                </p>
            </div>
            <button
                type="button"
                onclick={() => (isDeckModalOpen = false)}
                class="text-content-tertiary hover:text-content-primary transition-colors"
                aria-label="close modal"
            >
                ✕
            </button>
        </div>

        <div class="space-y-3">
            <div>
                <label for="deck-name" class="block text-sm font-medium text-content-secondary mb-1">
                    卡組名稱
                </label>
                <input
                    id="deck-name"
                    type="text"
                    bind:value={deckNameInput}
                    class="w-full px-3.5 py-2.5 text-sm bg-surface-primary border border-border rounded-md focus:outline-none focus:border-border-hover transition-colors"
                    placeholder="例如：高一上 Unit 1"
                />
            </div>

            <div>
                <label for="deck-lemmas" class="block text-sm font-medium text-content-secondary mb-1">
                    單字清單
                </label>
                <textarea
                    id="deck-lemmas"
                    rows="6"
                    bind:value={deckInput}
                    class="w-full px-3.5 py-2.5 text-sm bg-surface-primary border border-border rounded-md focus:outline-none focus:border-border-hover transition-colors"
                    placeholder="abandon, ability, achieve"
                ></textarea>
                <p class="text-xs text-content-tertiary mt-1">
                    支援分隔符：空白、逗號、頓號、分號。
                </p>
            </div>

            {#if deckStatus}
                <div class="text-xs text-srs-hard">
                    {deckStatus}
                </div>
            {/if}

            <div class="flex items-center justify-end gap-2 pt-1">
                <button
                    type="button"
                    onclick={() => (isDeckModalOpen = false)}
                    class="px-3.5 py-2 rounded-md text-content-secondary hover:text-content-primary transition-colors"
                >
                    取消
                </button>
                <button
                    type="button"
                    onclick={upsertDeck}
                    class="px-3.5 py-2 rounded-md bg-content-primary text-white font-medium hover:opacity-90 transition-opacity"
                >
                    儲存卡組
                </button>
            </div>
        </div>
    </div>
{/snippet}

{#snippet settingsContent()}
    <div class="space-y-5">
        <div class="flex items-center justify-between p-3 bg-surface-page/60 rounded-lg">
            <div>
                <span class="text-sm font-medium text-content-primary">智慧推薦模式</span>
                <p class="text-xs text-content-tertiary mt-0.5">
                    {smartMode ? "根據 ML 模型自動安排學習順序" : "隨機順序學習新卡片"}
                </p>
            </div>
            <button
                type="button"
                onclick={() => (smartMode = !smartMode)}
                class="relative w-10 h-6 rounded-full transition-colors {smartMode ? 'bg-accent' : 'bg-border'}"
                role="switch"
                aria-checked={smartMode}
                aria-label="智慧推薦模式"
            >
                <span
                    class="absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-sm transition-transform {smartMode ? 'translate-x-4' : 'translate-x-0'}"
                ></span>
            </button>
        </div>

        <div>
            <label
                for="new-card-limit"
                class="block text-sm font-medium text-content-secondary mb-2"
            >
                每次新卡片上限
            </label>
            <input
                id="new-card-limit"
                type="number"
                bind:value={newCardLimit}
                min="0"
                max="100"
                class="w-full px-3.5 py-2.5 text-sm bg-surface-primary border border-border rounded-md focus:outline-none focus:border-border-hover transition-colors"
            />
            <p class="text-xs text-content-tertiary mt-1.5">
                設為 0 則只複習已學過的卡片
            </p>
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
                    自動播放發音
                </span>
            </label>
        </div>
    </div>
{/snippet}
