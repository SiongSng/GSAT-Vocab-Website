<script lang="ts">
    import { tick } from "svelte";
    import { getVocabStore, selectWord } from "$lib/stores/vocab.svelte";
    import { getAppStore, closeMobileDetail } from "$lib/stores/app.svelte";
    import { speakText } from "$lib/tts";
    import CollapsibleSection from "$lib/components/ui/CollapsibleSection.svelte";
    import SenseTabs from "$lib/components/word/SenseTabs.svelte";
    import StatisticsSection from "$lib/components/word/StatisticsSection.svelte";
    import ConfusionNotes from "$lib/components/word/ConfusionNotes.svelte";
    import RelatedWords from "$lib/components/word/RelatedWords.svelte";
    import RootAnalysis from "$lib/components/word/RootAnalysis.svelte";

    const vocab = getVocabStore();
    const app = getAppStore();

    let audioPlayer: HTMLAudioElement | null = null;
    let isPlayingWord = $state(false);
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

        return () => {
            if (skeletonTimer) {
                clearTimeout(skeletonTimer);
                skeletonTimer = null;
            }
        };
    });

    const isLoadingDetail = $derived(isActuallyLoading && showSkeleton);

    const hasConfusionNotes = $derived(
        entry?.confusion_notes != null && entry.confusion_notes.length > 0,
    );
    const hasRootInfo = $derived(entry?.root_info != null);
    const hasRelatedWords = $derived(
        (entry?.synonyms != null && entry.synonyms.length > 0) ||
            (entry?.antonyms != null && entry.antonyms.length > 0) ||
            (entry?.derived_forms != null && entry.derived_forms.length > 0),
    );

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

    function handleRelatedWordClick(lemma: string) {
        selectWord(lemma);
    }

    function formatLevel(level: number | null): string {
        if (level === null) return "";
        return `L${level}`;
    }

    function formatImportance(
        frequency:
            | {
                  ml_score: number | null;
                  weighted_score: number;
              }
            | null
            | undefined,
    ): string {
        if (!frequency) return "N/A";
        const score = frequency.ml_score ?? frequency.weighted_score / 30;
        return `${Math.round(score * 100)}%`;
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
            <!-- Header -->
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
                    <div class="flex items-center gap-1.5 flex-wrap text-sm">
                        {#if entry.level !== null}
                            <span class="text-content-tertiary"
                                >{formatLevel(entry.level)}</span
                            >
                            <span class="text-border-hover">·</span>
                        {/if}
                        {#if entry.in_official_list}
                            <span class="text-accent">官方</span>
                            <span class="text-border-hover">·</span>
                        {/if}
                        <span class="text-content-tertiary"
                            >重要 {formatImportance(entry.frequency)}</span
                        >
                    </div>
                </div>
            </div>

            <!-- Sense Tabs -->
            {#if entry.senses && entry.senses.length > 0}
                <div class="senses-section mb-6">
                    <SenseTabs senses={entry.senses} lemma={entry.lemma} />
                </div>
            {/if}

            <!-- Collapsible Sections -->
            <div
                class="collapsible-sections space-y-1 border-t border-border pt-4"
            >
                <!-- Statistics -->
                {#if entry.frequency && entry.senses}
                    <CollapsibleSection
                        title="統計數據"
                        icon="chart"
                        defaultOpen={false}
                    >
                        <StatisticsSection
                            frequency={entry.frequency}
                            senses={entry.senses}
                        />
                    </CollapsibleSection>
                {/if}

                <!-- Root Analysis -->
                {#if hasRootInfo && entry.root_info}
                    <CollapsibleSection
                        title="字根分析"
                        icon="puzzle"
                        defaultOpen={false}
                    >
                        <RootAnalysis rootInfo={entry.root_info} />
                    </CollapsibleSection>
                {/if}

                <!-- Confusion Notes -->
                {#if hasConfusionNotes && entry.confusion_notes}
                    <CollapsibleSection
                        title="易混淆詞彙"
                        icon="warning"
                        defaultOpen={false}
                    >
                        <ConfusionNotes
                            notes={entry.confusion_notes}
                            currentLemma={entry.lemma}
                        />
                    </CollapsibleSection>
                {/if}

                <!-- Related Words -->
                {#if hasRelatedWords}
                    <CollapsibleSection
                        title="相關詞彙"
                        icon="link"
                        defaultOpen={false}
                    >
                        <RelatedWords
                            synonyms={entry.synonyms}
                            antonyms={entry.antonyms}
                            derivedForms={entry.derived_forms}
                            onWordClick={handleRelatedWordClick}
                        />
                    </CollapsibleSection>
                {/if}
            </div>
        </div>
    {/if}
</section>

<style>
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
