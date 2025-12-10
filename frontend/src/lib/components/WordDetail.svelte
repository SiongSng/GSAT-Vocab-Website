<script lang="ts">
    import { getVocabStore, clearSelectedWord } from "$lib/stores/vocab.svelte";
    import { getAppStore, closeMobileDetail } from "$lib/stores/app.svelte";
    import {
        getAudioUrl,
        getSentenceAudioUrl,
        fetchMoreSentences,
        type SentencePreview,
    } from "$lib/api";

    const vocab = getVocabStore();
    const app = getAppStore();

    let isLoadingMoreSentences = $state(false);
    let additionalSentences = $state<SentencePreview[]>([]);
    let nextOffset = $state(0);
    let totalSentences = $state(0);
    let audioPlayer: HTMLAudioElement | null = null;
    let showSkeleton = $state(false);
    let skeletonTimer: ReturnType<typeof setTimeout> | null = null;

    const word = $derived(vocab.selectedWord);
    const selectedLemma = $derived(vocab.selectedLemma);
    const isActuallyLoading = $derived(
        selectedLemma !== null && word?.lemma !== selectedLemma,
    );

    $effect(() => {
        if (isActuallyLoading) {
            skeletonTimer = setTimeout(() => {
                showSkeleton = true;
            }, 150);
        } else {
            if (skeletonTimer) {
                clearTimeout(skeletonTimer);
                skeletonTimer = null;
            }
            showSkeleton = false;
        }
    });

    const isLoadingDetail = $derived(isActuallyLoading && showSkeleton);

    const allSentences = $derived.by(() => {
        if (!word?.sentences) return [];
        return [...(word.sentences.preview || []), ...additionalSentences];
    });

    const hasMoreSentences = $derived(
        word?.sentences ? nextOffset < totalSentences : false,
    );

    function playWordAudio() {
        if (!word) return;
        if (!audioPlayer) {
            audioPlayer = new Audio();
        }
        audioPlayer.src = getAudioUrl(word.lemma);
        audioPlayer.play().catch(() => {});
    }

    function playSentenceAudio(audioFile: string) {
        if (!audioPlayer) {
            audioPlayer = new Audio();
        }
        audioPlayer.src = getSentenceAudioUrl(audioFile);
        audioPlayer.play().catch(() => {});
    }

    function handleBackClick() {
        if (app.isMobile) {
            closeMobileDetail();
        } else {
            clearSelectedWord();
        }
    }

    async function loadMoreSentences() {
        if (!word || isLoadingMoreSentences || !hasMoreSentences) return;

        isLoadingMoreSentences = true;
        try {
            const data = await fetchMoreSentences(word.lemma, nextOffset, 5);
            additionalSentences = [...additionalSentences, ...data.items];
            nextOffset = data.next_offset;
            totalSentences = data.total_count;
        } catch (e) {
            console.error("Failed to load more sentences:", e);
        } finally {
            isLoadingMoreSentences = false;
        }
    }

    function highlightWord(text: string, lemma: string): string {
        const variants = getInflectionVariants(lemma);
        const pattern = variants
            .map((v) => v.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
            .join("|");
        const regex = new RegExp(`\\b(${pattern})\\b`, "gi");
        return text.replace(regex, '<mark class="highlight">$1</mark>');
    }

    function getInflectionVariants(lemma: string): string[] {
        const lower = lemma.toLowerCase();
        const variants = [lemma, lower];

        if (lower.endsWith("y")) {
            variants.push(lower.slice(0, -1) + "ies");
            variants.push(lower.slice(0, -1) + "ied");
        } else if (lower.endsWith("e")) {
            variants.push(lower + "s");
            variants.push(lower + "d");
            variants.push(lower.slice(0, -1) + "ing");
        } else {
            variants.push(lower + "s");
            variants.push(lower + "es");
            variants.push(lower + "ed");
            variants.push(lower + "ing");
        }

        return variants;
    }

    function getRank(lemma: string): number {
        const idx = vocab.index.findIndex((w) => w.lemma === lemma);
        return idx >= 0 ? idx + 1 : 0;
    }

    $effect(() => {
        if (word) {
            additionalSentences = [];
            nextOffset = word.sentences?.next_offset ?? 0;
            totalSentences = word.sentences?.total_count ?? 0;
        }
    });
</script>

<section
    class="detail-panel h-full w-full bg-slate-50 p-6 lg:p-8 overflow-y-auto relative"
>
    {#if app.isMobile}
        <button
            class="lg:hidden absolute top-4 left-4 p-2 rounded-full bg-white/60 backdrop-blur-sm hover:bg-slate-200 z-50"
            onclick={handleBackClick}
            type="button"
            aria-label="Back to list"
        >
            <svg
                class="w-6 h-6 text-slate-700"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="2"
                stroke="currentColor"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15.75 19.5 8.25 12l7.5-7.5"
                />
            </svg>
        </button>
    {/if}

    {#if !selectedLemma}
        <div class="h-full flex flex-col justify-center">
            <h2 class="text-2xl font-bold text-slate-800">
                歡迎使用單字探索工具
            </h2>
            <p class="mt-2 text-slate-500">
                從左側開始搜尋、篩選，或點擊「隨機一字」。
            </p>
            <div class="mt-12 text-center">
                <svg
                    class="w-24 h-24 mx-auto text-slate-300"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M10.5 6a7.5 7.5 0 1 0 7.5 7.5h-7.5V6Z"
                    />
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M13.5 10.5H21A7.5 7.5 0 0 0 13.5 3v7.5Z"
                    />
                </svg>
                <p class="mt-4 text-slate-400">
                    {vocab.isLoading
                        ? "正在載入數據..."
                        : "選擇一個單字開始學習"}
                </p>
            </div>
        </div>
    {:else if isLoadingDetail}
        <div class="detail-content pt-12 lg:pt-0">
            <div class="flex items-start justify-between mb-6">
                <div>
                    <div class="flex items-center gap-3 mb-2">
                        <div class="skeleton-text h-10 w-40"></div>
                        <div class="skeleton-circle w-10 h-10"></div>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="skeleton-text h-4 w-12"></div>
                        <div class="skeleton-text h-4 w-20"></div>
                    </div>
                </div>
            </div>

            <div class="meanings-section mb-8">
                <div class="skeleton-text h-6 w-16 mb-4"></div>
                <div class="space-y-4">
                    {#each [1, 2] as _}
                        <div
                            class="bg-white rounded-lg p-4 shadow-sm border border-slate-100"
                        >
                            <div class="flex items-center gap-2 mb-2">
                                <div class="skeleton-text h-5 w-12"></div>
                                <div class="skeleton-text h-4 w-6"></div>
                            </div>
                            <div class="skeleton-text h-4 w-full mb-2"></div>
                            <div class="skeleton-text h-4 w-3/4"></div>
                        </div>
                    {/each}
                </div>
            </div>

            <div class="pos-distribution-section mb-8">
                <div class="skeleton-text h-6 w-20 mb-4"></div>
                <div
                    class="bg-white rounded-lg p-4 shadow-sm border border-slate-100"
                >
                    <div class="space-y-3">
                        {#each [1, 2, 3] as _}
                            <div>
                                <div class="flex justify-between mb-1">
                                    <div class="skeleton-text h-4 w-16"></div>
                                    <div class="skeleton-text h-4 w-20"></div>
                                </div>
                                <div
                                    class="h-2 bg-slate-100 rounded-full overflow-hidden"
                                >
                                    <div
                                        class="skeleton-bar h-full rounded-full"
                                    ></div>
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            </div>

            <div class="sentences-section">
                <div class="skeleton-text h-6 w-24 mb-4"></div>
                <div class="space-y-3">
                    {#each [1, 2, 3] as _}
                        <div
                            class="bg-white rounded-lg p-4 shadow-sm border border-slate-100"
                        >
                            <div class="flex items-start gap-3">
                                <div class="skeleton-text h-4 w-4 mt-1"></div>
                                <div class="flex-1">
                                    <div
                                        class="skeleton-text h-4 w-full mb-2"
                                    ></div>
                                    <div class="skeleton-text h-4 w-5/6"></div>
                                </div>
                            </div>
                        </div>
                    {/each}
                </div>
            </div>
        </div>
    {:else if word}
        <div class="detail-content pt-12 lg:pt-0">
            <div class="flex items-start justify-between mb-6">
                <div>
                    <div class="flex items-center gap-3 mb-2">
                        <h2
                            class="text-3xl lg:text-4xl font-bold text-indigo-700"
                        >
                            {word.lemma}
                        </h2>
                        <button
                            class="p-2 rounded-full hover:bg-slate-200 transition-colors"
                            onclick={playWordAudio}
                            title="播放發音"
                            type="button"
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
                    </div>
                    <div class="flex items-center gap-2 text-sm text-slate-500">
                        <span>#{getRank(word.lemma)}</span>
                        <span>•</span>
                        <span>出現 {word.count} 次</span>
                    </div>
                </div>
            </div>

            {#if word.meanings && word.meanings.length > 0}
                <div class="meanings-section mb-8">
                    <h3 class="text-lg font-semibold text-slate-800 mb-4">
                        詞義
                    </h3>
                    <div class="space-y-4">
                        {#each word.meanings as meaning, i}
                            <div
                                class="meaning-item bg-white rounded-lg p-4 shadow-sm border border-slate-100"
                            >
                                <div class="flex items-center gap-2 mb-2">
                                    <span
                                        class="text-xs font-medium px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded"
                                    >
                                        {meaning.pos}
                                    </span>
                                    <span class="text-xs text-slate-400"
                                        >#{i + 1}</span
                                    >
                                </div>
                                <p class="text-slate-700 mb-1">
                                    {meaning.zh_def}
                                </p>
                                <p class="text-sm text-slate-500">
                                    {meaning.en_def}
                                </p>
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}

            {#if word.pos_distribution && Object.keys(word.pos_distribution).length > 0}
                <div class="pos-distribution-section mb-8">
                    <h3 class="text-lg font-semibold text-slate-800 mb-4">
                        詞性分布
                    </h3>
                    <div
                        class="bg-white rounded-lg p-4 shadow-sm border border-slate-100"
                    >
                        <div class="space-y-3">
                            {#each Object.entries(word.pos_distribution).sort((a, b) => b[1] - a[1]) as [pos, count]}
                                {@const total = Object.values(
                                    word.pos_distribution,
                                ).reduce((a, b) => a + b, 0)}
                                {@const percentage = Math.round(
                                    (count / total) * 100,
                                )}
                                <div class="pos-bar">
                                    <div
                                        class="flex justify-between text-sm mb-1"
                                    >
                                        <span class="font-medium text-slate-700"
                                            >{pos}</span
                                        >
                                        <span class="text-slate-500"
                                            >{count} ({percentage}%)</span
                                        >
                                    </div>
                                    <div
                                        class="h-2 bg-slate-100 rounded-full overflow-hidden"
                                    >
                                        <div
                                            class="h-full bg-indigo-500 rounded-full transition-all duration-300"
                                            style="width: {percentage}%"
                                        ></div>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    </div>
                </div>
            {/if}

            {#if allSentences.length > 0}
                <div class="sentences-section">
                    <h3 class="text-lg font-semibold text-slate-800 mb-4">
                        例句
                        <span class="text-sm font-normal text-slate-500">
                            ({allSentences.length}/{totalSentences})
                        </span>
                    </h3>
                    <div class="space-y-3">
                        {#each allSentences as sentence, i}
                            <div
                                class="sentence-item bg-white rounded-lg p-4 shadow-sm border border-slate-100"
                            >
                                <div class="flex items-start gap-3">
                                    <span class="text-xs text-slate-400 mt-1"
                                        >{i + 1}</span
                                    >
                                    <div class="flex-1">
                                        <p
                                            class="text-slate-700 leading-relaxed"
                                        >
                                            {@html highlightWord(
                                                sentence.text,
                                                word.lemma,
                                            )}
                                        </p>
                                        {#if sentence.source}
                                            <p
                                                class="text-xs text-slate-400 mt-2"
                                            >
                                                — {sentence.source}
                                            </p>
                                        {/if}
                                    </div>
                                    {#if sentence.audio_file}
                                        <button
                                            class="p-1.5 rounded-full hover:bg-slate-100 transition-colors flex-shrink-0"
                                            onclick={() =>
                                                playSentenceAudio(
                                                    sentence.audio_file!,
                                                )}
                                            title="播放例句"
                                            type="button"
                                        >
                                            <svg
                                                class="w-5 h-5 text-slate-500"
                                                xmlns="http://www.w3.org/2000/svg"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke-width="1.5"
                                                stroke="currentColor"
                                            >
                                                <path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"
                                                />
                                            </svg>
                                        </button>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>

                    {#if hasMoreSentences}
                        <button
                            class="mt-4 w-full py-2 px-4 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm text-slate-600 font-medium transition-colors disabled:opacity-50"
                            onclick={loadMoreSentences}
                            disabled={isLoadingMoreSentences}
                            type="button"
                        >
                            {#if isLoadingMoreSentences}
                                載入中...
                            {:else}
                                載入更多例句
                            {/if}
                        </button>
                    {/if}
                </div>
            {/if}
        </div>
    {/if}
</section>

<style>
    :global(.highlight) {
        background-color: rgb(254 249 195);
        padding: 0.125rem 0.25rem;
        border-radius: 0.25rem;
        font-weight: 500;
    }

    .detail-panel {
        scrollbar-width: thin;
        scrollbar-color: rgb(203 213 225) transparent;
    }

    .detail-panel::-webkit-scrollbar {
        width: 6px;
    }

    .detail-panel::-webkit-scrollbar-track {
        background: transparent;
    }

    .detail-panel::-webkit-scrollbar-thumb {
        background-color: rgb(203 213 225);
        border-radius: 3px;
    }

    .detail-panel::-webkit-scrollbar-thumb:hover {
        background-color: rgb(148 163 184);
    }

    .skeleton-text {
        background: linear-gradient(
            90deg,
            rgb(226 232 240) 25%,
            rgb(241 245 249) 50%,
            rgb(226 232 240) 75%
        );
        background-size: 200% 100%;
        animation: shimmer 2.5s infinite;
        border-radius: 0.25rem;
    }

    .skeleton-circle {
        background: linear-gradient(
            90deg,
            rgb(226 232 240) 25%,
            rgb(241 245 249) 50%,
            rgb(226 232 240) 75%
        );
        background-size: 200% 100%;
        animation: shimmer 2.5s infinite;
        border-radius: 9999px;
    }

    .skeleton-bar {
        background: linear-gradient(
            90deg,
            rgb(199 210 254) 25%,
            rgb(224 231 255) 50%,
            rgb(199 210 254) 75%
        );
        background-size: 200% 100%;
        animation: shimmer 2.5s infinite;
        width: 60%;
    }

    @keyframes shimmer {
        0% {
            background-position: 200% 0;
        }
        100% {
            background-position: -200% 0;
        }
    }
</style>
