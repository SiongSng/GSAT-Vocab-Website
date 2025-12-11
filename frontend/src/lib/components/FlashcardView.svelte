<script lang="ts">
    import {
        getFlashcardStore,
        openSetup,
        closeSetup,
        startFlashcards,
        flipCard,
        nextCard,
        previousCard,
        markKnown,
        markReview,
        setAutoSpeak,
        restartAll,
        restartReviewOnly,
        exportReviewList,
        playCurrentWordAudio,
    } from "$lib/stores/flashcard.svelte";
    import { getVocabStore, getFilters } from "$lib/stores/vocab.svelte";
    import { fetchWordDetail, type WordDetail } from "$lib/api";
    import type { VocabWord } from "$lib/types";

    const flashcard = getFlashcardStore();
    const vocab = getVocabStore();
    const filters = getFilters();

    let wordCount = $state(20);
    let selectedPos = $state<Set<string>>(new Set());
    let excludePropn = $state(true);
    let freqMin = $state(1);
    let freqMax = $state(20);
    let manualSearchTerm = $state("");
    let manualSelected = $state<Set<string>>(new Set());

    let currentWordDetail = $state<WordDetail | null>(null);
    let isLoadingDetail = $state(false);

    const posOptions = ["NOUN", "VERB", "ADJ", "ADV"];
    const posLabels: Record<string, string> = {
        NOUN: "名詞",
        VERB: "動詞",
        ADJ: "形容詞",
        ADV: "副詞",
    };

    const filteredPool = $derived.by(() => {
        let pool = vocab.index;

        pool = pool.filter((w) => w.count >= freqMin && w.count <= freqMax);

        if (selectedPos.size > 0) {
            pool = pool.filter((w) => selectedPos.has(w.primary_pos));
        }

        if (excludePropn) {
            pool = pool.filter((w) => w.primary_pos !== "PROPN");
        }

        return pool;
    });

    const manualFilteredList = $derived.by(() => {
        if (!manualSearchTerm) return filteredPool.slice(0, 100);
        const term = manualSearchTerm.toLowerCase();
        return filteredPool
            .filter((w) => w.lemma.toLowerCase().includes(term))
            .slice(0, 100);
    });

    function togglePos(pos: string) {
        const newSet = new Set(selectedPos);
        if (newSet.has(pos)) {
            newSet.delete(pos);
        } else {
            newSet.add(pos);
        }
        selectedPos = newSet;
    }

    function toggleManualWord(lemma: string) {
        const newSet = new Set(manualSelected);
        if (newSet.has(lemma)) {
            newSet.delete(lemma);
        } else {
            newSet.add(lemma);
        }
        manualSelected = newSet;
    }

    function handleStart() {
        let wordsToUse: VocabWord[];

        if (manualSelected.size > 0) {
            wordsToUse = vocab.index.filter((w) =>
                manualSelected.has(w.lemma),
            ) as VocabWord[];
        } else {
            const pool = filteredPool;
            const count = Math.min(wordCount, pool.length);
            const shuffled = [...pool].sort(() => Math.random() - 0.5);
            wordsToUse = shuffled.slice(0, count) as VocabWord[];
        }

        if (wordsToUse.length === 0) {
            alert("沒有符合條件的單字");
            return;
        }

        startFlashcards(wordsToUse);
        loadCurrentWordDetail();
    }

    function handleCancel() {
        closeSetup();
    }

    function handleFlip() {
        flipCard();
    }

    function handlePrev() {
        previousCard();
        loadCurrentWordDetail();
    }

    function handleNext() {
        nextCard();
        if (!flashcard.isComplete) {
            loadCurrentWordDetail();
        }
    }

    function handleKnown() {
        markKnown();
        if (!flashcard.isComplete) {
            loadCurrentWordDetail();
        }
    }

    function handleReview() {
        markReview();
        if (!flashcard.isComplete) {
            loadCurrentWordDetail();
        }
    }

    function handleAutoSpeakChange(e: Event) {
        const target = e.target as HTMLInputElement;
        setAutoSpeak(target.checked);
    }

    function handleRestartAll() {
        restartAll();
        loadCurrentWordDetail();
    }

    function handleRestartReview() {
        restartReviewOnly();
        loadCurrentWordDetail();
    }

    async function loadCurrentWordDetail() {
        const word = flashcard.currentWord;
        if (!word) {
            currentWordDetail = null;
            return;
        }

        isLoadingDetail = true;
        try {
            currentWordDetail = await fetchWordDetail(word.lemma);
        } catch (e) {
            console.error("Failed to load word detail:", e);
            currentWordDetail = null;
        } finally {
            isLoadingDetail = false;
        }
    }

    $effect(() => {
        if (
            flashcard.words.length === 0 &&
            !flashcard.isSetupOpen &&
            !flashcard.isComplete
        ) {
            openSetup();
        }
    });

    $effect(() => {
        freqMin = filters.freqMin;
        freqMax = filters.freqMax;
    });
</script>

<div
    class="flashcard-view h-full flex flex-col items-center justify-center p-5 sm:p-8 bg-surface-page overflow-y-auto"
>
    {#if flashcard.isSetupOpen}
        <div
            class="setup-panel w-full max-w-2xl bg-surface-primary rounded-lg border border-border p-6"
        >
            <h2
                class="text-xl lg:text-2xl font-semibold tracking-tight text-content-primary mb-6"
            >
                字卡設定
            </h2>

            <div class="space-y-5">
                <div>
                    <label
                        for="word-count"
                        class="block text-sm font-medium text-content-secondary mb-2"
                    >
                        單字數量
                    </label>
                    <input
                        id="word-count"
                        type="number"
                        min="1"
                        max="100"
                        bind:value={wordCount}
                        class="w-full px-3.5 py-2.5 text-sm"
                    />
                </div>

                <div>
                    <span
                        class="block text-sm font-medium text-content-secondary mb-2.5"
                    >
                        詞性篩選
                    </span>
                    <div class="flex flex-wrap gap-2">
                        <button
                            type="button"
                            class="pos-chip"
                            class:active={selectedPos.size === 0}
                            onclick={() => (selectedPos = new Set())}
                        >
                            全部
                        </button>
                        {#each posOptions as pos}
                            <button
                                type="button"
                                class="pos-chip"
                                class:active={selectedPos.has(pos)}
                                onclick={() => togglePos(pos)}
                            >
                                {posLabels[pos] || pos}
                            </button>
                        {/each}
                    </div>
                </div>

                <div>
                    <span
                        class="block text-sm font-medium text-content-secondary mb-2"
                    >
                        頻率範圍
                    </span>
                    <div class="flex gap-3 items-center">
                        <input
                            type="number"
                            min={vocab.freqRange.min}
                            max={vocab.freqRange.max}
                            bind:value={freqMin}
                            class="flex-1 px-3 py-2 text-sm"
                            placeholder="最小"
                        />
                        <span class="text-content-tertiary text-sm">至</span>
                        <input
                            type="number"
                            min={vocab.freqRange.min}
                            max={vocab.freqRange.max}
                            bind:value={freqMax}
                            class="flex-1 px-3 py-2 text-sm"
                            placeholder="最大"
                        />
                    </div>
                </div>

                <div class="space-y-2.5">
                    <label
                        class="flex items-center gap-2.5 cursor-pointer group"
                    >
                        <input type="checkbox" bind:checked={excludePropn} />
                        <span
                            class="text-sm text-content-secondary group-hover:text-content-primary transition-colors"
                        >
                            排除專有名詞
                        </span>
                    </label>

                    <label
                        class="flex items-center gap-2.5 cursor-pointer group"
                    >
                        <input
                            type="checkbox"
                            checked={flashcard.autoSpeak}
                            onchange={handleAutoSpeakChange}
                        />
                        <span
                            class="text-sm text-content-secondary group-hover:text-content-primary transition-colors"
                        >
                            自動播放發音
                        </span>
                    </label>
                </div>

                <details
                    class="border border-border rounded-lg overflow-hidden"
                >
                    <summary
                        class="px-4 py-3 cursor-pointer text-sm font-medium text-content-secondary hover:bg-surface-hover transition-colors"
                    >
                        手動選擇單字 ({manualSelected.size} 已選)
                    </summary>
                    <div
                        class="p-4 border-t border-border bg-surface-secondary/30"
                    >
                        <input
                            type="text"
                            placeholder="搜尋單字..."
                            bind:value={manualSearchTerm}
                            class="w-full px-3 py-2 mb-3 text-sm"
                        />
                        <div
                            class="max-h-48 overflow-y-auto space-y-1 custom-scrollbar"
                        >
                            {#each manualFilteredList as word}
                                <label
                                    class="flex items-center gap-2.5 p-2 hover:bg-surface-hover rounded-md cursor-pointer transition-colors"
                                >
                                    <input
                                        type="checkbox"
                                        checked={manualSelected.has(word.lemma)}
                                        onchange={() =>
                                            toggleManualWord(word.lemma)}
                                    />
                                    <span class="text-sm text-content-primary"
                                        >{word.lemma}</span
                                    >
                                    <span
                                        class="text-xs text-content-tertiary ml-auto"
                                        >{word.primary_pos}</span
                                    >
                                </label>
                            {/each}
                        </div>
                    </div>
                </details>

                <div class="text-sm text-content-tertiary">
                    可用單字數：{filteredPool.length}
                </div>

                <div class="flex gap-3 pt-2">
                    <button
                        type="button"
                        class="flex-1 px-5 py-2.5 bg-content-primary text-white font-medium rounded-md hover:opacity-90 transition-opacity"
                        onclick={handleStart}
                    >
                        開始練習
                    </button>
                    <button
                        type="button"
                        class="px-5 py-2.5 bg-surface-page text-content-primary font-medium rounded-md border border-border hover:bg-surface-hover transition-colors"
                        onclick={handleCancel}
                    >
                        取消
                    </button>
                </div>
            </div>
        </div>
    {:else if flashcard.isComplete}
        <div
            class="summary-panel w-full max-w-2xl bg-surface-primary rounded-lg border border-border p-6 lg:p-8"
        >
            <h3
                class="text-xl lg:text-2xl font-semibold tracking-tight text-content-primary mb-6"
            >
                本輪練習結算
            </h3>

            <div class="grid grid-cols-3 gap-3 mb-8 text-center">
                <div class="py-4 lg:py-5 px-3 rounded-md bg-surface-page/60">
                    <div
                        class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight"
                    >
                        {flashcard.progress.total}
                    </div>
                    <div class="text-sm text-content-secondary mt-1.5">
                        總題數
                    </div>
                </div>
                <div class="py-4 lg:py-5 px-3 rounded-md bg-srs-good/10">
                    <div
                        class="text-2xl lg:text-3xl font-semibold text-srs-good tracking-tight"
                    >
                        {flashcard.progress.known}
                    </div>
                    <div class="text-sm text-content-secondary mt-1.5">
                        已掌握
                    </div>
                </div>
                <div class="py-4 lg:py-5 px-3 rounded-md bg-srs-hard/10">
                    <div
                        class="text-2xl lg:text-3xl font-semibold text-srs-hard tracking-tight"
                    >
                        {flashcard.progress.review}
                    </div>
                    <div class="text-sm text-content-secondary mt-1.5">
                        需複習
                    </div>
                </div>
            </div>

            <div class="flex flex-wrap gap-3">
                <button
                    type="button"
                    class="px-5 py-2.5 bg-content-primary text-white font-medium rounded-md hover:opacity-90 transition-opacity text-sm"
                    onclick={handleRestartAll}
                >
                    重練全部
                </button>
                {#if flashcard.progress.review > 0}
                    <button
                        type="button"
                        class="px-5 py-2.5 bg-srs-hard text-white font-medium rounded-md hover:opacity-90 transition-opacity text-sm"
                        onclick={handleRestartReview}
                    >
                        只練需複習
                    </button>
                    <button
                        type="button"
                        class="px-5 py-2.5 bg-surface-page text-content-secondary font-medium rounded-md border border-border hover:bg-surface-hover transition-colors text-sm"
                        onclick={exportReviewList}
                    >
                        導出需複習清單
                    </button>
                {/if}
                <button
                    type="button"
                    class="ml-auto px-5 py-2.5 bg-surface-secondary text-content-secondary font-medium rounded-md hover:bg-surface-hover transition-colors text-sm"
                    onclick={openSetup}
                >
                    返回設定
                </button>
            </div>
        </div>
    {:else if flashcard.currentWord}
        <div
            class="flashcard w-full max-w-2xl h-96 perspective-1000 cursor-pointer"
            onclick={handleFlip}
            role="button"
            tabindex="0"
            onkeydown={(e) => e.key === "Enter" && handleFlip()}
        >
            <div
                class="flashcard-inner relative w-full h-full transition-transform duration-500 transform-style-preserve-3d"
                class:flipped={flashcard.isFlipped}
            >
                <div
                    class="flashcard-front absolute inset-0 bg
-surface-primary border border-border rounded-xl flex flex-col items-center justify-center p-8 backface-hidden"
                >
                    <button
                        type="button"
                        class="absolute top-4 right-4 p-2.5 rounded-md hover:bg-surface-hover transition-colors"
                        onclick={(e) => {
                            e.stopPropagation();
                            playCurrentWordAudio();
                        }}
                        title="播放發音"
                    >
                        <svg
                            class="w-5 h-5 text-content-tertiary hover:text-content-secondary transition-colors"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
                            />
                        </svg>
                    </button>
                    <h2
                        class="text-4xl md:text-5xl font-semibold text-accent mb-4 break-words text-center tracking-tight"
                    >
                        {flashcard.currentWord.lemma}
                    </h2>
                    <p class="text-content-tertiary">
                        {flashcard.currentWord.primary_pos}
                    </p>
                    <p class="text-sm text-content-tertiary mt-8">
                        點擊查看釋義
                    </p>
                </div>

                <div
                    class="flashcard-back absolute inset-0 bg-accent-soft border border-accent/20 rounded-xl flex flex-col items-center justify-center p-8 backface-hidden rotate-y-180"
                >
                    <div
                        class="text-center space-y-4 max-w-xl overflow-y-auto max-h-80 custom-scrollbar"
                    >
                        {#if isLoadingDetail}
                            <p class="text-content-secondary">載入中...</p>
                        {:else if currentWordDetail?.meanings}
                            {#each currentWordDetail.meanings.slice(0, 3) as meaning}
                                <div class="meaning-item">
                                    <span
                                        class="text-xs font-medium px-2 py-0.5 bg-accent/20 text-accent rounded"
                                    >
                                        {meaning.pos}
                                    </span>
                                    <p
                                        class="text-lg text-content-primary mt-1.5"
                                    >
                                        {meaning.zh_def}
                                    </p>
                                    <p class="text-sm text-content-secondary">
                                        {meaning.en_def}
                                    </p>
                                </div>
                            {/each}
                        {:else}
                            <p class="text-content-secondary">無法載入釋義</p>
                        {/if}
                    </div>
                    <p class="text-sm text-content-tertiary mt-8">點擊返回</p>
                </div>
            </div>
        </div>

        <div class="mt-6 flex flex-wrap gap-2 justify-center">
            <button
                type="button"
                class="p-2.5 bg-surface-primary border border-border rounded-md hover:bg-surface-hover transition-colors disabled:opacity-50"
                onclick={handlePrev}
                disabled={flashcard.currentIndex === 0}
                aria-label="上一張"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-5 h-5 text-content-secondary"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M15.75 19.5 8.25 12l7.5-7.5"
                    />
                </svg>
            </button>
            <button
                type="button"
                class="px-5 py-2.5 bg-srs-good text-white font-medium rounded-md hover:opacity-90 transition-opacity text-sm"
                onclick={handleKnown}
            >
                已掌握
            </button>
            <button
                type="button"
                class="px-5 py-2.5 bg-srs-hard text-white font-medium rounded-md hover:opacity-90 transition-opacity text-sm"
                onclick={handleReview}
            >
                需複習
            </button>
            <button
                type="button"
                class="p-2.5 bg-surface-primary border border-border rounded-md hover:bg-surface-hover transition-colors"
                onclick={handleNext}
                aria-label="下一張"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-5 h-5 text-content-secondary"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="m8.25 4.5 7.5 7.5-7.5 7.5"
                    />
                </svg>
            </button>
        </div>

        <div class="mt-4 text-center">
            <p class="text-sm text-content-tertiary">
                {flashcard.progress.current} / {flashcard.progress.total}
                {#if flashcard.progress.known > 0 || flashcard.progress.review > 0}
                    <span class="ml-2 text-content-secondary">
                        (✓ {flashcard.progress.known} | ⟳ {flashcard.progress
                            .review})
                    </span>
                {/if}
            </p>
        </div>
    {/if}
</div>

<style>
    .perspective-1000 {
        perspective: 1000px;
    }

    .transform-style-preserve-3d {
        transform-style: preserve-3d;
    }

    .backface-hidden {
        backface-visibility: hidden;
    }

    .rotate-y-180 {
        transform: rotateY(180deg);
    }

    .flashcard-inner.flipped {
        transform: rotateY(180deg);
    }

    .pos-chip {
        padding: 0.375rem 0.75rem;
        background-color: var(--color-surface-page);
        border-radius: 6px;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--color-content-secondary);
        transition: all 0.15s ease;
        cursor: pointer;
        border: 1px solid transparent;
    }

    .pos-chip:hover {
        background-color: var(--color-surface-hover);
        border-color: var(--color-border);
    }

    .pos-chip.active {
        background-color: var(--color-accent-soft);
        color: var(--color-accent);
        border-color: transparent;
    }

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
</style>
