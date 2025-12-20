<script lang="ts">
    import { tick } from "svelte";
    import { getVocabStore, selectWord } from "$lib/stores/vocab.svelte";
    import { getAppStore, closeMobileDetail } from "$lib/stores/app.svelte";
    import { speakText } from "$lib/tts";
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
    let activeDeepDive = $state<string | null>(null);

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

    $effect(() => {
        if (entry) {
            if (entry.frequency && entry.senses) {
                activeDeepDive = "stats";
            } else if (entry.root_info) {
                activeDeepDive = "root";
            } else if (
                entry.confusion_notes &&
                entry.confusion_notes.length > 0
            ) {
                activeDeepDive = "confusion";
            } else if (
                entry.synonyms ||
                entry.antonyms ||
                entry.derived_forms
            ) {
                activeDeepDive = "related";
            } else {
                activeDeepDive = null;
            }
        }
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

    const memoryTip = $derived(entry?.root_info?.memory_strategy ?? null);

    const importanceScore = $derived(() => {
        if (!entry?.frequency) return 0;
        return entry.frequency.ml_score ?? entry.frequency.weighted_score / 30;
    });

    const importancePercentage = $derived(Math.round(importanceScore() * 100));

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

    function toggleDeepDive(section: string) {
        activeDeepDive = activeDeepDive === section ? null : section;
    }
</script>

<section
    class="detail-panel h-full w-full bg-surface-page overflow-y-auto relative"
>
    {#if app.isMobile}
        <button
            class="lg:hidden fixed top-4 left-4 p-2 rounded-md bg-surface-primary/80 backdrop-blur-sm hover:bg-surface-hover border border-border z-50 transition-colors"
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
        <div class="detail-content p-6 lg:p-8 pt-14 lg:pt-8">
            <!-- Skeleton: Header -->
            <div class="mb-6">
                <div class="flex items-start justify-between mb-3">
                    <div>
                        <div class="skeleton-text h-8 w-36 mb-2"></div>
                        <div class="skeleton-text h-4 w-24"></div>
                    </div>
                    <div class="skeleton-circle w-10 h-10"></div>
                </div>
            </div>

            <!-- Skeleton: Senses -->
            <div class="skeleton-text h-10 w-full mb-4"></div>
            <div class="space-y-3">
                {#each [1, 2] as _}
                    <div class="skeleton-text h-24 w-full rounded-lg"></div>
                {/each}
            </div>
        </div>
    {:else if entry}
        <div class="detail-content p-6 lg:p-8 pt-14 lg:pt-8">
            <!-- Header -->
            <header class="mb-6">
                <div class="flex items-start justify-between">
                    <div>
                        <h2
                            class="text-2xl lg:text-3xl font-semibold tracking-tight text-content-primary mb-1"
                        >
                            {entry.lemma}
                        </h2>
                        <div
                            class="flex items-center gap-1.5 text-sm text-content-tertiary"
                        >
                            {#if entry.level !== null}
                                <span>{formatLevel(entry.level)}</span>
                            {/if}
                            {#if entry.in_official_list}
                                {#if entry.level !== null}
                                    <span class="text-border-hover">·</span>
                                {/if}
                                <span class="text-accent">官方</span>
                            {/if}
                            {#if entry.frequency}
                                <span class="text-border-hover">·</span>
                                <span>重要 {importancePercentage}%</span>
                            {/if}
                        </div>
                    </div>
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

                <!-- Memory Tip -->
                {#if memoryTip}
                    <div
                        class="mt-4 p-3 bg-surface-secondary rounded-lg border border-border"
                    >
                        <div class="flex items-start gap-2.5">
                            <svg
                                class="w-4 h-4 text-content-tertiary flex-shrink-0 mt-0.5"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="1.5"
                                stroke="currentColor"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
                                />
                            </svg>
                            <p
                                class="text-sm text-content-secondary leading-relaxed"
                            >
                                {memoryTip}
                            </p>
                        </div>
                    </div>
                {/if}
            </header>

            <!-- Sense Tabs -->
            {#if entry.senses && entry.senses.length > 0}
                <div class="senses-section mb-6">
                    <SenseTabs senses={entry.senses} lemma={entry.lemma} />
                </div>
            {/if}

            <!-- Deep Dive Section -->
            {#if hasRootInfo || hasConfusionNotes || hasRelatedWords || entry.frequency}
                <div class="border-t border-border pt-5">
                    <h3 class="text-sm font-semibold text-section-header mb-3">
                        深入學習
                    </h3>

                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
                        <!-- Statistics -->
                        {#if entry.frequency && entry.senses}
                            <button
                                type="button"
                                class="deep-dive-btn"
                                class:active={activeDeepDive === "stats"}
                                onclick={() => toggleDeepDive("stats")}
                            >
                                <svg
                                    class="w-4 h-4"
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke-width="1.5"
                                    stroke="currentColor"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z"
                                    />
                                </svg>
                                <span>統計</span>
                            </button>
                        {/if}

                        <!-- Root Analysis -->
                        {#if hasRootInfo}
                            <button
                                type="button"
                                class="deep-dive-btn"
                                class:active={activeDeepDive === "root"}
                                onclick={() => toggleDeepDive("root")}
                            >
                                <svg
                                    class="w-4 h-4"
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke-width="1.5"
                                    stroke="currentColor"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M14.25 6.087c0-.355.186-.676.401-.959.221-.29.349-.634.349-1.003 0-1.036-1.007-1.875-2.25-1.875s-2.25.84-2.25 1.875c0 .369.128.713.349 1.003.215.283.401.604.401.959v0a.64.64 0 0 1-.657.643 48.39 48.39 0 0 1-4.163-.3c.186 1.613.293 3.25.315 4.907a.656.656 0 0 1-.658.663v0c-.355 0-.676-.186-.959-.401a1.647 1.647 0 0 0-1.003-.349c-1.036 0-1.875 1.007-1.875 2.25s.84 2.25 1.875 2.25c.369 0 .713-.128 1.003-.349.283-.215.604-.401.959-.401v0c.31 0 .555.26.532.57a48.039 48.039 0 0 1-.642 5.056c1.518.19 3.058.309 4.616.354a.64.64 0 0 0 .657-.643v0c0-.355-.186-.676-.401-.959a1.647 1.647 0 0 1-.349-1.003c0-1.035 1.008-1.875 2.25-1.875 1.243 0 2.25.84 2.25 1.875 0 .369-.128.713-.349 1.003-.215.283-.4.604-.4.959v0c0 .333.277.599.61.58a48.1 48.1 0 0 0 5.427-.63 48.05 48.05 0 0 0 .582-4.717.532.532 0 0 0-.533-.57v0c-.355 0-.676.186-.959.401-.29.221-.634.349-1.003.349-1.035 0-1.875-1.007-1.875-2.25s.84-2.25 1.875-2.25c.37 0 .713.128 1.003.349.283.215.604.401.96.401v0a.656.656 0 0 0 .658-.663 48.422 48.422 0 0 0-.37-5.36c-1.886.342-3.81.574-5.766.689a.578.578 0 0 1-.61-.58v0Z"
                                    />
                                </svg>
                                <span>字根</span>
                            </button>
                        {/if}

                        <!-- Confusion Notes -->
                        {#if hasConfusionNotes}
                            <button
                                type="button"
                                class="deep-dive-btn"
                                class:active={activeDeepDive === "confusion"}
                                onclick={() => toggleDeepDive("confusion")}
                            >
                                <svg
                                    class="w-4 h-4"
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke-width="1.5"
                                    stroke="currentColor"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
                                    />
                                </svg>
                                <span>易混淆</span>
                            </button>
                        {/if}

                        <!-- Related Words -->
                        {#if hasRelatedWords}
                            <button
                                type="button"
                                class="deep-dive-btn"
                                class:active={activeDeepDive === "related"}
                                onclick={() => toggleDeepDive("related")}
                            >
                                <svg
                                    class="w-4 h-4"
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke-width="1.5"
                                    stroke="currentColor"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"
                                    />
                                </svg>
                                <span>相關詞</span>
                            </button>
                        {/if}
                    </div>

                    <!-- Deep Dive Content -->
                    {#if activeDeepDive}
                        <div
                            class="bg-surface-primary rounded-lg border border-border p-4 animate-fade-in"
                        >
                            {#if activeDeepDive === "stats" && entry.frequency && entry.senses}
                                <StatisticsSection
                                    frequency={entry.frequency}
                                    senses={entry.senses}
                                />
                            {:else if activeDeepDive === "root" && entry.root_info}
                                <RootAnalysis rootInfo={entry.root_info} />
                            {:else if activeDeepDive === "confusion" && entry.confusion_notes}
                                <ConfusionNotes
                                    notes={entry.confusion_notes}
                                    currentLemma={entry.lemma}
                                />
                            {:else if activeDeepDive === "related"}
                                <RelatedWords
                                    synonyms={entry.synonyms}
                                    antonyms={entry.antonyms}
                                    derivedForms={entry.derived_forms}
                                    onWordClick={handleRelatedWordClick}
                                />
                            {/if}
                        </div>
                    {/if}
                </div>
            {/if}
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

    /* Deep Dive Button */
    .deep-dive-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.375rem;
        padding: 0.5rem 0.75rem;
        background: var(--color-surface-page);
        border: 1px solid transparent;
        border-radius: 6px;
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--color-content-secondary);
        cursor: pointer;
        transition: all 0.15s ease;
    }

    .deep-dive-btn:hover {
        background: var(--color-surface-hover);
        border-color: var(--color-border);
    }

    .deep-dive-btn.active {
        background: var(--color-accent-soft);
        border-color: transparent;
        color: var(--color-accent);
    }

    .deep-dive-btn svg {
        color: var(--color-content-tertiary);
        transition: color 0.15s ease;
    }

    .deep-dive-btn:hover svg,
    .deep-dive-btn.active svg {
        color: var(--color-accent);
    }

    /* Animation */
    .animate-fade-in {
        animation: fadeIn 0.15s ease-out;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-4px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* Skeleton */
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
