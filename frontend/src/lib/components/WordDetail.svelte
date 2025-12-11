<script lang="ts">
    import { tick } from "svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { getAppStore, closeMobileDetail } from "$lib/stores/app.svelte";
    import {
        fetchMoreSentences,
        getAudioUrl,
        getSentenceAudioUrl,
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

    $effect(() => {
        if (word) {
            additionalSentences = [];
            nextOffset = word.sentences?.next_offset ?? 0;
            totalSentences = word.sentences?.total_count ?? 0;
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

    function observeSentinel(node: HTMLElement) {
        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && !isLoadingMoreSentences) {
                    loadMoreSentences();
                }
            },
            { rootMargin: "100px" },
        );
        observer.observe(node);

        return {
            destroy() {
                observer.disconnect();
            },
        };
    }

    function playWordAudio() {
        if (!word) return;
        if (!audioPlayer) {
            audioPlayer = new Audio();
        }
        audioPlayer.src = getAudioUrl(word.lemma);
        audioPlayer.play().catch(() => {});
    }

    function playSentenceAudio(filename: string) {
        if (!audioPlayer) {
            audioPlayer = new Audio();
        }
        audioPlayer.src = getSentenceAudioUrl(filename);
        audioPlayer.play().catch(() => {});
    }

    function handleBackClick() {
        closeMobileDetail();
        tick().then(() => {
            const listContainer = document.querySelector(
                ".word-list-container",
            );
            if (listContainer) {
                listContainer.scrollTop = 0;
            }
        });
    }

    async function loadMoreSentences() {
        if (!word || isLoadingMoreSentences || !hasMoreSentences) return;

        isLoadingMoreSentences = true;
        try {
            const data = await fetchMoreSentences(word.lemma, nextOffset, 5);
            additionalSentences = [...additionalSentences, ...data.items];
            nextOffset = data.next_offset;
            totalSentences = data.total;
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
        return text.replace(regex, '<span class="highlight">$1</span>');
    }

    function getInflectionVariants(lemma: string): string[] {
        const lower = lemma.toLowerCase();
        const variants = [lemma, lower];

        variants.push(lower + "s");
        variants.push(lower + "es");
        variants.push(lower + "ed");
        variants.push(lower + "ing");
        variants.push(lower + "er");
        variants.push(lower + "est");
        variants.push(lower + "ly");

        if (lower.endsWith("e")) {
            variants.push(lower.slice(0, -1) + "ing");
            variants.push(lower + "d");
        }
        if (lower.endsWith("y")) {
            variants.push(lower.slice(0, -1) + "ies");
            variants.push(lower.slice(0, -1) + "ied");
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
    class="detail-panel h-full w-full bg-surface-page p-6 lg:p-8 overflow-y-auto relative"
>
    {#if app.isMobile}
        <button
            class="lg:hidden absolute top-4 left-4 p-2 rounded-md bg-surface-primary/80 backdrop-blur-sm hover:bg-surface-hover border border-border z-50 transition-colors"
            onclick={handleBackClick}
            type="button"
            aria-label="Back to list"
        >
            <svg
                class="w-5 h-5 text-content-secondary"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
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
        <div
            class="h-full flex flex-col items-center justify-center text-center px-4"
        >
            <div
                class="w-16 h-16 rounded-full bg-surface-secondary flex items-center justify-center mb-5"
            >
                <svg
                    class="w-8 h-8 text-content-tertiary"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
                    />
                </svg>
            </div>
            <h2
                class="text-xl font-semibold tracking-tight text-content-primary mb-2"
            >
                歡迎使用單字探索工具
            </h2>
            <p class="text-sm text-content-secondary max-w-xs">
                {vocab.isLoading
                    ? "正在載入數據..."
                    : "從左側開始搜尋、篩選，或點擊「隨機一字」"}
            </p>
        </div>
    {:else if isLoadingDetail}
        <div class="detail-content pt-12 lg:pt-0">
            <div class="flex items-start justify-between mb-6">
                <div>
                    <div class="flex items-center gap-3 mb-2">
                        <div class="skeleton-text h-9 w-36"></div>
                        <div class="skeleton-circle w-9 h-9"></div>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="skeleton-text h-4 w-10"></div>
                        <div class="skeleton-text h-4 w-16"></div>
                    </div>
                </div>
            </div>

            <div class="meanings-section mb-6">
                <div class="skeleton-text h-5 w-14 mb-3"></div>
                <div class="space-y-3">
                    {#each [1, 2] as _}
                        <div
                            class="bg-surface-primary rounded-lg p-4 border border-border"
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

            <div class="pos-distribution-section mb-6">
                <div class="skeleton-text h-5 w-16 mb-3"></div>
                <div
                    class="bg-surface-primary rounded-lg p-4 border border-border"
                >
                    <div class="space-y-3">
                        {#each [1, 2, 3] as _}
                            <div>
                                <div class="flex justify-between mb-1.5">
                                    <div class="skeleton-text h-4 w-14"></div>
                                    <div class="skeleton-text h-4 w-16"></div>
                                </div>
                                <div
                                    class="h-1.5 bg-surface-secondary rounded-full overflow-hidden"
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
                <div class="skeleton-text h-5 w-20 mb-3"></div>
                <div class="space-y-2.5">
                    {#each [1, 2, 3] as _}
                        <div
                            class="bg-surface-primary rounded-lg p-4 border border-border"
                        >
                            <div class="flex items-start gap-3">
                                <div class="skeleton-text h-4 w-4 mt-0.5"></div>
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
                            class="text-2xl lg:text-3xl font-semibold tracking-tight text-accent"
                        >
                            {word.lemma}
                        </h2>
                        <button
                            class="p-2 rounded-md hover:bg-surface-hover transition-colors"
                            onclick={playWordAudio}
                            title="播放發音"
                            type="button"
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
                    </div>
                    <div
                        class="flex items-center gap-2 text-sm text-content-tertiary"
                    >
                        <span>#{getRank(word.lemma)}</span>
                        <span class="text-border-hover">•</span>
                        <span>出現 {word.count} 次</span>
                    </div>
                </div>
            </div>

            {#if word.meanings && word.meanings.length > 0}
                <div class="meanings-section mb-6">
                    <h3
                        class="text-sm font-medium text-content-secondary mb-3 uppercase tracking-wide"
                    >
                        詞義
                    </h3>
                    <div class="space-y-2.5">
                        {#each word.meanings as meaning, i}
                            <div
                                class="meaning-item bg-surface-primary rounded-lg p-4 border border-border"
                            >
                                <div class="flex items-center gap-2 mb-2">
                                    <span
                                        class="text-xs font-medium px-2 py-0.5 bg-accent-soft text-accent rounded"
                                    >
                                        {meaning.pos}
                                    </span>
                                    <span class="text-xs text-content-tertiary"
                                        >#{i + 1}</span
                                    >
                                </div>
                                <p class="text-content-primary mb-1">
                                    {meaning.zh_def}
                                </p>
                                <p class="text-sm text-content-secondary">
                                    {meaning.en_def}
                                </p>
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}

            {#if word.pos_distribution && Object.keys(word.pos_distribution).length > 0}
                <div class="pos-distribution-section mb-6">
                    <h3
                        class="text-sm font-medium text-content-secondary mb-3 uppercase tracking-wide"
                    >
                        詞性分布
                    </h3>
                    <div
                        class="bg-surface-primary rounded-lg p-4 border border-border"
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
                                        class="flex justify-between text-sm mb-1.5"
                                    >
                                        <span
                                            class="font-medium text-content-primary"
                                            >{pos}</span
                                        >
                                        <span class="text-content-tertiary"
                                            >{count} ({percentage}%)</span
                                        >
                                    </div>
                                    <div
                                        class="h-1.5 bg-surface-page rounded-full overflow-hidden"
                                    >
                                        <div
                                            class="h-full bg-accent rounded-full transition-all duration-300"
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
                    <h3
                        class="text-sm font-medium text-content-secondary mb-3 uppercase tracking-wide"
                    >
                        例句
                        <span
                            class="text-content-tertiary font-normal normal-case"
                        >
                            ({allSentences.length}/{totalSentences ||
                                word.sentences?.total_count ||
                                0})
                        </span>
                    </h3>
                    <div class="space-y-2.5">
                        {#each allSentences as sentence, i (sentence.text)}
                            <div
                                class="sentence-item bg-surface-primary rounded-lg p-4 border border-border animate-fade-in"
                            >
                                <div class="flex items-start gap-3">
                                    <span
                                        class="text-xs text-content-tertiary mt-0.5 font-medium"
                                        >{i + 1}</span
                                    >
                                    <div class="flex-1 min-w-0">
                                        <p
                                            class="text-content-primary leading-relaxed"
                                        >
                                            {@html highlightWord(
                                                sentence.text,
                                                word.lemma,
                                            )}
                                        </p>
                                        {#if sentence.source}
                                            <p
                                                class="text-xs text-content-tertiary mt-2"
                                            >
                                                — {sentence.source}
                                            </p>
                                        {/if}
                                    </div>
                                    {#if sentence.audio_file}
                                        <button
                                            class="p-1.5 rounded-md hover:bg-surface-hover transition-colors flex-shrink-0"
                                            onclick={() =>
                                                playSentenceAudio(
                                                    sentence.audio_file!,
                                                )}
                                            title="播放例句"
                                            type="button"
                                        >
                                            <svg
                                                class="w-4 h-4 text-content-tertiary"
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
                        <div
                            use:observeSentinel
                            class="mt-4 flex items-center justify-center py-6"
                        >
                            <div class="loading-spinner"></div>
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    {/if}
</section>

<style>
    :global(.highlight) {
        background: linear-gradient(
            to top,
            rgba(251, 191, 36, 0.35) 0%,
            rgba(251, 191, 36, 0.35) 60%,
            transparent 60%
        );
        padding: 0 3px;
        margin: 0 -3px;
        border-radius: 2px;
        font-weight: 500;
    }

    .animate-fade-in {
        animation: fadeIn 0.25s ease-out;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    .loading-spinner {
        width: 24px;
        height: 24px;
        border: 2px solid var(--color-border);
        border-top-color: var(--color-accent);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    .detail-panel {
        scrollbar-width: thin;
        scrollbar-color: var(--color-border-hover) transparent;
    }

    .detail-panel::-webkit-scrollbar {
        width: 6px;
    }

    .detail-panel::-webkit-scrollbar-track {
        background: transparent;
    }

    .detail-panel::-webkit-scrollbar-thumb {
        background-color: var(--color-border-hover);
        border-radius: 3px;
    }

    .detail-panel::-webkit-scrollbar-thumb:hover {
        background-color: var(--color-content-tertiary);
    }

    .skeleton-text {
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

    .skeleton-circle {
        background: linear-gradient(
            90deg,
            var(--color-surface-secondary) 25%,
            var(--color-surface-page) 50%,
            var(--color-surface-secondary) 75%
        );
        background-size: 200% 100%;
        animation: shimmer 2.5s infinite;
        border-radius: 9999px;
    }

    .skeleton-bar {
        background: linear-gradient(
            90deg,
            var(--color-accent-soft) 25%,
            rgba(32, 125, 255, 0.05) 50%,
            var(--color-accent-soft) 75%
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
