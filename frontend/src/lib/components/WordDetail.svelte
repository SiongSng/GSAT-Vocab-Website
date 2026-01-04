<script lang="ts">
    import { tick } from "svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { getAppStore, closeMobileDetail } from "$lib/stores/app.svelte";
    import type { WordEntry, PhraseEntry, PatternEntry } from "$lib/types/vocab";
    import PatternDetail from "$lib/components/PatternDetail.svelte";
    import EntryDetailContent from "$lib/components/word/EntryDetailContent.svelte";

    const vocab = getVocabStore();
    const app = getAppStore();

    let showSkeleton = $state(false);
    let skeletonTimer: ReturnType<typeof setTimeout> | null = null;

    const entry = $derived(vocab.selectedEntry);
    const entryType = $derived(vocab.selectedEntryType);
    const selectedLemma = $derived(vocab.selectedLemma);
    const isActuallyLoading = $derived(
        selectedLemma !== null && entry?.lemma !== selectedLemma,
    );

    const wordEntry = $derived(
        entryType === "word" ? (entry as WordEntry) : null,
    );
    const phraseEntry = $derived(
        entryType === "phrase" ? (entry as PhraseEntry) : null,
    );
    const patternEntry = $derived(
        entryType === "pattern" ? (entry as PatternEntry) : null,
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
            <div class="mb-6">
                <div class="flex items-start justify-between mb-3">
                    <div>
                        <div class="skeleton-text h-8 w-36 mb-2"></div>
                        <div class="skeleton-text h-4 w-24"></div>
                    </div>
                    <div class="skeleton-circle w-10 h-10"></div>
                </div>
            </div>
            <div class="skeleton-text h-10 w-full mb-4"></div>
            <div class="space-y-3">
                {#each [1, 2] as _}
                    <div class="skeleton-text h-24 w-full rounded-lg"></div>
                {/each}
            </div>
        </div>
    {:else if patternEntry}
        <div class="pt-14 lg:pt-0">
            <PatternDetail entry={patternEntry} />
        </div>
    {:else if wordEntry}
        <div class="detail-content p-6 lg:p-8 pt-14 lg:pt-8">
            <EntryDetailContent entry={wordEntry} />
        </div>
    {:else if phraseEntry}
        <div class="detail-content p-6 lg:p-8 pt-14 lg:pt-8">
            <EntryDetailContent entry={phraseEntry} />
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
