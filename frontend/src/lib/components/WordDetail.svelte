<script lang="ts">
    import { tick } from "svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { getAppStore, closeMobileDetail } from "$lib/stores/app.svelte";
    import { speakText } from "$lib/tts";

    const vocab = getVocabStore();
    const app = getAppStore();

    let audioPlayer: HTMLAudioElement | null = null;
    let isPlayingWord = $state(false);
    let playingSentenceIndex = $state<number | null>(null);
    let showSkeleton = $state(false);
    let skeletonTimer: ReturnType<typeof setTimeout> | null = null;

    const entry = $derived(vocab.selectedEntry);
    const selectedLemma = $derived(vocab.selectedLemma);
    const isActuallyLoading = $derived(
        selectedLemma !== null && entry?.lemma !== selectedLemma,
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

    const allExamples = $derived.by(() => {
        if (!entry?.senses) return [];
        return entry.senses.flatMap((sense, senseIdx) =>
            sense.examples.map((ex) => ({
                text: ex.text,
                source: `${ex.source.year} ${ex.source.exam_type}`,
                senseIdx,
            })),
        );
    });

    async function playWordAudio() {
        if (!entry || isPlayingWord) return;
        isPlayingWord = true;
        try {
            const url = await speakText(entry.lemma);
            if (!audioPlayer) audioPlayer = new Audio();
            audioPlayer.src = url;
            audioPlayer.onended = () => (isPlayingWord = false);
            audioPlayer.onerror = () => (isPlayingWord = false);
            await audioPlayer.play();
        } catch {
            isPlayingWord = false;
        }
    }

    async function playSentenceAudio(text: string, index: number) {
        if (playingSentenceIndex === index) return;
        playingSentenceIndex = index;
        try {
            const url = await speakText(text);
            if (!audioPlayer) audioPlayer = new Audio();
            audioPlayer.src = url;
            audioPlayer.onended = () => (playingSentenceIndex = null);
            audioPlayer.onerror = () => (playingSentenceIndex = null);
            await audioPlayer.play();
        } catch {
            playingSentenceIndex = null;
        }
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

    function formatLevel(level: number | null): string {
        if (level === null) return "";
        return `Level ${level}`;
    }

    function formatTier(tier: string): string {
        const tierMap: Record<string, string> = {
            tested: "考題詞彙",
            translation: "翻譯詞彙",
            phrase: "片語",
            pattern: "句型",
            basic: "基礎",
        };
        return tierMap[tier] ?? tier;
    }
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
                    : "從左側開始搜尋、篩選，或點擊任意單字"}
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
    {:else if entry}
        <div class="detail-content pt-12 lg:pt-0">
            <div class="flex items-start justify-between mb-6">
                <div>
                    <div class="flex items-center gap-3 mb-2">
                        <h2
                            class="text-2xl lg:text-3xl font-semibold tracking-tight text-accent"
                        >
                            {entry.lemma}
                        </h2>
                        <button
                            class="p-2 rounded-md hover:bg-surface-hover transition-colors"
                            class:animate-pulse={isPlayingWord}
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
                    <div class="flex items-center gap-2 flex-wrap text-sm">
                        <span class="text-content-tertiary">#{getRank(entry.lemma)}</span>
                        <span class="text-border-hover">·</span>
                        <span class="text-content-tertiary">出現 {entry.frequency.total_occurrences} 次</span>
                        {#if entry.level !== null}
                            <span class="text-border-hover">·</span>
                            <span class="text-content-tertiary">{formatLevel(entry.level)}</span>
                        {/if}
                        {#if entry.in_official_list}
                            <span class="px-1.5 py-0.5 text-xs font-medium bg-accent-soft text-accent rounded">官方詞彙</span>
                        {/if}
                        <span class="px-1.5 py-0.5 text-xs font-medium bg-surface-secondary text-content-secondary rounded">{formatTier(entry.tier)}</span>
                    </div>
                </div>
            </div>

            {#if entry.senses && entry.senses.length > 0}
                <div class="meanings-section mb-6">
                    <h3 class="section-header">詞義</h3>
                    <div class="space-y-2.5">
                        {#each entry.senses as sense, i}
                            <div
                                class="meaning-item bg-surface-primary rounded-lg p-4 border border-border shadow-card transition-shadow hover:shadow-card-hover"
                            >
                                <div class="flex items-center gap-2 mb-2">
                                    <span
                                        class="text-xs font-medium px-2 py-0.5 bg-accent-soft text-accent rounded"
                                    >
                                        {sense.pos}
                                    </span>
                                    <span class="text-xs text-content-tertiary">#{i + 1}</span>
                                    {#if sense.tested_in_exam}
                                        <span class="text-xs font-medium px-1.5 py-0.5 bg-srs-good-soft text-srs-good rounded">曾考</span>
                                    {/if}
                                </div>
                                <p class="text-content-primary mb-1">
                                    {sense.zh_def}
                                </p>
                                <p class="text-sm text-content-secondary">
                                    {sense.en_def}
                                </p>
                                {#if sense.generated_example}
                                    <p class="text-sm text-content-tertiary mt-2 italic">
                                        {sense.generated_example}
                                    </p>
                                {/if}
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}

            {#if entry.confusion_notes && entry.confusion_notes.length > 0}
                <div class="confusion-section mb-6">
                    <h3 class="section-header">易混淆詞</h3>
                    <div class="space-y-2.5">
                        {#each entry.confusion_notes as note}
                            <div class="bg-surface-primary rounded-lg p-4 border border-border shadow-card">
                                <div class="flex items-center gap-2 mb-2">
                                    <span class="font-medium text-srs-hard">{note.confused_with}</span>
                                </div>
                                <p class="text-sm text-content-secondary mb-2">{note.distinction}</p>
                                <p class="text-xs text-content-tertiary italic">{note.memory_tip}</p>
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}

            {#if entry.root_info}
                <div class="root-section mb-6">
                    <h3 class="section-header">記憶策略</h3>
                    <div class="bg-surface-primary rounded-lg p-4 border border-border shadow-card">
                        {#if entry.root_info.root_breakdown}
                            <p class="text-sm text-content-primary mb-2">
                                <span class="font-medium">字根拆解：</span>{entry.root_info.root_breakdown}
                            </p>
                        {/if}
                        <p class="text-sm text-content-secondary">{entry.root_info.memory_strategy}</p>
                    </div>
                </div>
            {/if}

            {#if entry.synonyms && entry.synonyms.length > 0}
                <div class="related-section mb-6">
                    <h3 class="section-header">同義詞</h3>
                    <div class="flex flex-wrap gap-2">
                        {#each entry.synonyms as syn}
                            <span class="px-2.5 py-1 text-sm bg-surface-primary border border-border rounded-md text-content-secondary">{syn}</span>
                        {/each}
                    </div>
                </div>
            {/if}

            {#if entry.antonyms && entry.antonyms.length > 0}
                <div class="related-section mb-6">
                    <h3 class="section-header">反義詞</h3>
                    <div class="flex flex-wrap gap-2">
                        {#each entry.antonyms as ant}
                            <span class="px-2.5 py-1 text-sm bg-surface-primary border border-border rounded-md text-content-secondary">{ant}</span>
                        {/each}
                    </div>
                </div>
            {/if}

            {#if entry.derived_forms && entry.derived_forms.length > 0}
                <div class="related-section mb-6">
                    <h3 class="section-header">衍生詞</h3>
                    <div class="flex flex-wrap gap-2">
                        {#each entry.derived_forms as form}
                            <span class="px-2.5 py-1 text-sm bg-surface-primary border border-border rounded-md text-content-secondary">{form}</span>
                        {/each}
                    </div>
                </div>
            {/if}

            {#if allExamples.length > 0}
                <div class="sentences-section">
                    <h3 class="section-header">
                        考古題例句
                        <span class="text-content-tertiary font-normal">
                            ({allExamples.length})
                        </span>
                    </h3>
                    <div class="space-y-2.5">
                        {#each allExamples as example, i (example.text)}
                            <div
                                class="sentence-item bg-surface-primary rounded-lg p-4 border border-border shadow-card animate-fade-in"
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
                                                example.text,
                                                entry.lemma,
                                            )}
                                        </p>
                                        <p
                                            class="text-xs text-content-tertiary mt-2"
                                        >
                                            — {example.source}
                                        </p>
                                    </div>
                                    <button
                                        class="p-1.5 rounded-md hover:bg-surface-hover transition-colors flex-shrink-0"
                                        class:animate-pulse={playingSentenceIndex === i}
                                        onclick={() =>
                                            playSentenceAudio(
                                                example.text,
                                                i,
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
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}
        </div>
    {/if}
</section>

<style>
    :global(.highlight) {
        background: linear-gradient(
            to top,
            var(--color-highlight) 0%,
            var(--color-highlight) 60%,
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

    @keyframes shimmer {
        0% {
            background-position: 200% 0;
        }
        100% {
            background-position: -200% 0;
        }
    }
</style>
