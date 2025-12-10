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
    class="flashcard-view h-full flex flex-col items-center justify-center p-4 sm:p-8 bg-slate-50 overflow-y-auto"
>
    {#if flashcard.isSetupOpen}
        <div
            class="setup-panel w-full max-w-2xl bg-white rounded-xl shadow-lg p-6"
        >
            <h2 class="text-2xl font-bold text-slate-800 mb-6">字卡設定</h2>

            <div class="space-y-6">
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-2"
                        >單字數量</label
                    >
                    <input
                        type="number"
                        min="1"
                        max="100"
                        bind:value={wordCount}
                        class="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    />
                </div>

                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-2"
                        >詞性篩選</label
                    >
                    <div class="flex flex-wrap gap-2">
                        {#each posOptions as pos}
                            <button
                                type="button"
                                class="pos-chip px-3 py-1.5 rounded-full text-sm font-medium transition-colors"
                                class:active={selectedPos.has(pos)}
                                onclick={() => togglePos(pos)}
                            >
                                {pos}
                            </button>
                        {/each}
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-2"
                        >頻率範圍</label
                    >
                    <div class="flex gap-4">
                        <input
                            type="number"
                            min={vocab.freqRange.min}
                            max={vocab.freqRange.max}
                            bind:value={freqMin}
                            class="flex-1 px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                            placeholder="最小"
                        />
                        <input
                            type="number"
                            min={vocab.freqRange.min}
                            max={vocab.freqRange.max}
                            bind:value={freqMax}
                            class="flex-1 px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                            placeholder="最大"
                        />
                    </div>
                </div>

                <div>
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            bind:checked={excludePropn}
                            class="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                        />
                        <span class="text-sm text-slate-700">排除專有名詞</span>
                    </label>
                </div>

                <div>
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={flashcard.autoSpeak}
                            onchange={handleAutoSpeakChange}
                            class="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                        />
                        <span class="text-sm text-slate-700">自動播放發音</span>
                    </label>
                </div>

                <details class="border border-slate-200 rounded-lg">
                    <summary
                        class="px-4 py-3 cursor-pointer text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                        手動選擇單字 ({manualSelected.size} 已選)
                    </summary>
                    <div class="p-4 border-t border-slate-200">
                        <input
                            type="text"
                            placeholder="搜尋單字..."
                            bind:value={manualSearchTerm}
                            class="w-full px-3 py-2 mb-3 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                        />
                        <div class="max-h-48 overflow-y-auto space-y-1">
                            {#each manualFilteredList as word}
                                <label
                                    class="flex items-center gap-2 p-2 hover:bg-slate-50 rounded cursor-pointer"
                                >
                                    <input
                                        type="checkbox"
                                        checked={manualSelected.has(word.lemma)}
                                        onchange={() =>
                                            toggleManualWord(word.lemma)}
                                        class="w-4 h-4 text-indigo-600 rounded"
                                    />
                                    <span class="text-sm">{word.lemma}</span>
                                    <span class="text-xs text-slate-400 ml-auto"
                                        >{word.primary_pos}</span
                                    >
                                </label>
                            {/each}
                        </div>
                    </div>
                </details>

                <div class="text-sm text-slate-500">
                    可用單字數：{filteredPool.length}
                </div>

                <div class="flex gap-3 pt-4">
                    <button
                        type="button"
                        class="flex-1 px-4 py-2.5 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition-colors"
                        onclick={handleStart}
                    >
                        開始練習
                    </button>
                    <button
                        type="button"
                        class="px-4 py-2.5 bg-slate-200 text-slate-700 font-semibold rounded-lg hover:bg-slate-300 transition-colors"
                        onclick={handleCancel}
                    >
                        取消
                    </button>
                </div>
            </div>
        </div>
    {:else if flashcard.isComplete}
        <div
            class="summary-panel w-full max-w-2xl bg-white rounded-xl shadow-lg p-6"
        >
            <h3 class="text-2xl font-bold text-slate-800 mb-6">本輪練習結算</h3>

            <div class="grid grid-cols-3 gap-4 mb-8 text-center">
                <div class="p-4 bg-slate-50 rounded-lg">
                    <div class="text-3xl font-bold text-slate-800">
                        {flashcard.progress.total}
                    </div>
                    <div class="text-sm text-slate-500">總題數</div>
                </div>
                <div class="p-4 bg-green-50 rounded-lg">
                    <div class="text-3xl font-bold text-green-600">
                        {flashcard.progress.known}
                    </div>
                    <div class="text-sm text-slate-500">已掌握</div>
                </div>
                <div class="p-4 bg-yellow-50 rounded-lg">
                    <div class="text-3xl font-bold text-yellow-600">
                        {flashcard.progress.review}
                    </div>
                    <div class="text-sm text-slate-500">需複習</div>
                </div>
            </div>

            <div class="flex flex-wrap gap-3">
                <button
                    type="button"
                    class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                    onclick={handleRestartAll}
                >
                    重練全部
                </button>
                {#if flashcard.progress.review > 0}
                    <button
                        type="button"
                        class="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
                        onclick={handleRestartReview}
                    >
                        只練需複習
                    </button>
                    <button
                        type="button"
                        class="px-4 py-2 bg-slate-200 rounded-lg hover:bg-slate-300 transition-colors"
                        onclick={exportReviewList}
                    >
                        導出需複習清單
                    </button>
                {/if}
                <button
                    type="button"
                    class="ml-auto px-4 py-2 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
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
                    class="flashcard-front absolute inset-0 bg-white shadow-2xl rounded-2xl flex flex-col items-center justify-center p-8 backface-hidden"
                >
                    <button
                        type="button"
                        class="absolute top-3 right-3 p-2 rounded-full hover:bg-slate-100"
                        onclick={(e) => {
                            e.stopPropagation();
                            playCurrentWordAudio();
                        }}
                        title="播放發音"
                    >
                        <svg
                            class="w-6 h-6 text-slate-600"
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
                        class="text-4xl md:text-5xl font-bold text-indigo-700 mb-4 break-words text-center"
                    >
                        {flashcard.currentWord.lemma}
                    </h2>
                    <p class="text-slate-500">
                        {flashcard.currentWord.primary_pos}
                    </p>
                    <p class="text-sm text-slate-400 mt-8">點擊查看釋義</p>
                </div>

                <div
                    class="flashcard-back absolute inset-0 bg-indigo-50 shadow-2xl rounded-2xl flex flex-col items-center justify-center p-8 backface-hidden rotate-y-180"
                >
                    <div
                        class="text-center space-y-4 max-w-xl overflow-y-auto max-h-80"
                    >
                        {#if isLoadingDetail}
                            <p class="text-slate-500">載入中...</p>
                        {:else if currentWordDetail?.meanings}
                            {#each currentWordDetail.meanings.slice(0, 3) as meaning}
                                <div class="meaning-item">
                                    <span
                                        class="text-xs font-medium px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded"
                                    >
                                        {meaning.pos}
                                    </span>
                                    <p class="text-lg text-slate-800 mt-1">
                                        {meaning.zh_def}
                                    </p>
                                    <p class="text-sm text-slate-500">
                                        {meaning.en_def}
                                    </p>
                                </div>
                            {/each}
                        {:else}
                            <p class="text-slate-500">無法載入釋義</p>
                        {/if}
                    </div>
                    <p class="text-sm text-slate-400 mt-8">點擊返回</p>
                </div>
            </div>
        </div>

        <div class="mt-6 flex flex-wrap gap-2 justify-center">
            <button
                type="button"
                class="p-2 bg-slate-200 rounded-lg hover:bg-slate-300 transition-colors"
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
                    class="w-6 h-6"
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
                class="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                onclick={handleKnown}
            >
                已掌握
            </button>
            <button
                type="button"
                class="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
                onclick={handleReview}
            >
                需複習
            </button>
            <button
                type="button"
                class="p-2 bg-slate-200 rounded-lg hover:bg-slate-300 transition-colors"
                onclick={handleNext}
                aria-label="下一張"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-6 h-6"
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
            <p class="text-sm text-slate-500">
                {flashcard.progress.current} / {flashcard.progress.total}
                {#if flashcard.progress.known > 0 || flashcard.progress.review > 0}
                    <span class="ml-2">
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
        background-color: rgb(241 245 249);
        color: rgb(71 85 105);
        border: 1px solid transparent;
    }

    .pos-chip:hover {
        background-color: rgb(226 232 240);
    }

    .pos-chip.active {
        background-color: rgb(238 242 255);
        color: rgb(79 70 229);
        border-color: rgb(165 180 252);
    }
</style>
