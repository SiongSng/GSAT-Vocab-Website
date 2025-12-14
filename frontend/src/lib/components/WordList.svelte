<script lang="ts">
    import { tick } from "svelte";
    import type { VocabIndexItem } from "$lib/types/vocab";
    import { getAppStore, openMobileDetail } from "$lib/stores/app.svelte";
    import { selectWordAndNavigate, getVocabStore } from "$lib/stores/vocab.svelte";

    const ITEM_HEIGHT = 72;
    const GRID_ITEM_HEIGHT = 40;
    const BUFFER_COUNT = 5;

    interface Props {
        words: VocabIndexItem[];
        isGridMode?: boolean;
    }

    let { words, isGridMode = false }: Props = $props();

    const app = getAppStore();
    const vocab = getVocabStore();

    let rankMapCache: Map<string, number> | null = null;
    let lastIndexLength = 0;
    let listContainer: HTMLDivElement | null = null;
    let scrollTop = $state(0);
    let containerHeight = $state(0);

    function getRankMap(): Map<string, number> {
        const index = vocab.index;
        if (rankMapCache && index.length === lastIndexLength) {
            return rankMapCache;
        }
        const map = new Map<string, number>();
        for (let i = 0; i < index.length; i++) {
            map.set(index[i].lemma, i + 1);
        }
        rankMapCache = map;
        lastIndexLength = index.length;
        return map;
    }

    async function handleWordClick(word: VocabIndexItem) {
        await selectWordAndNavigate(word.lemma);
        if (app.isMobile) {
            openMobileDetail();
        }
    }

    function getRank(lemma: string): number {
        return getRankMap().get(lemma) ?? 0;
    }

    function handleScroll(e: Event) {
        const target = e.target as HTMLDivElement;
        scrollTop = target.scrollTop;
    }

    const gridColumns = $derived.by(() => {
        if (!isGridMode) return 1;
        if (containerHeight < 640) return 2;
        if (containerHeight < 768) return 3;
        return 4;
    });

    const itemsPerRow = $derived(isGridMode ? gridColumns : 1);
    const rowHeight = $derived(isGridMode ? GRID_ITEM_HEIGHT + 8 : ITEM_HEIGHT);
    const totalRows = $derived(Math.ceil(words.length / itemsPerRow));
    const totalHeight = $derived(totalRows * rowHeight);

    const visibleRange = $derived.by(() => {
        const startRow = Math.floor(scrollTop / rowHeight);
        const visibleRows = Math.ceil(containerHeight / rowHeight);
        const startIndex = Math.max(0, (startRow - BUFFER_COUNT) * itemsPerRow);
        const endIndex = Math.min(
            words.length,
            (startRow + visibleRows + BUFFER_COUNT) * itemsPerRow,
        );
        return {
            startIndex,
            endIndex,
            startRow: Math.max(0, startRow - BUFFER_COUNT),
        };
    });

    const visibleWords = $derived(
        words.slice(visibleRange.startIndex, visibleRange.endIndex),
    );
    const offsetY = $derived(visibleRange.startRow * rowHeight);

    $effect(() => {
        const selectedLemma = vocab.selectedLemma;
        void words;

        tick().then(() => {
            if (listContainer) {
                const prev = listContainer.querySelector(".active-item");
                if (prev) prev.classList.remove("active-item");

                if (selectedLemma) {
                    const el = listContainer.querySelector(
                        `[data-lemma="${CSS.escape(selectedLemma)}"]`,
                    );
                    if (el) el.classList.add("active-item");
                }
            }
        });
    });
</script>

<div
    class="word-list-container"
    bind:this={listContainer}
    bind:clientHeight={containerHeight}
    onscroll={handleScroll}
>
    {#if words.length === 0}
        <div
            class="flex flex-col items-center justify-center h-full px-4 py
-12"
        >
            <div
                class="w-12 h-12 rounded-full bg-surface-secondary flex items-center justify-center mb-4"
            >
                <svg
                    class="w-6 h-6 text-content-tertiary"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
                    />
                </svg>
            </div>
            <p class="text-sm text-content-secondary text-center">
                找不到符合條件的單詞
            </p>
        </div>
    {:else if isGridMode}
        <div class="virtual-scroll-wrapper" style="height: {totalHeight}px;">
            <div
                class="grid-container grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 p-3"
                style="transform: translateY({offsetY}px);"
            >
                {#each visibleWords as word (word.lemma)}
                    <button
                        class="browse-cell"
                        data-lemma={word.lemma}
                        onclick={() => handleWordClick(word)}
                        type="button"
                    >
                        {word.lemma}
                    </button>
                {/each}
            </div>
        </div>
    {:else}
        <div class="virtual-scroll-wrapper" style="height: {totalHeight}px;">
            <div class="word-list" style="transform: translateY({offsetY}px);">
                {#each visibleWords as word (word.lemma)}
                    <button
                        class="list-item"
                        data-lemma={word.lemma}
                        onclick={() => handleWordClick(word)}
                        type="button"
                    >
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="font-semibold text-content-primary"
                                    >{word.lemma}</span
                                >
                                <span
                                    class="text-xs font-medium text-content-tertiary"
                                    >{word.primary_pos}</span
                                >
                                {#if word.meaning_count > 1}
                                    <span
                                        class="text-xs px-1.5 py-0.5 bg-accent-soft text-accent rounded font-medium"
                                    >
                                        {word.meaning_count}義
                                    </span>
                                {/if}
                            </div>
                            {#if word.zh_preview}
                                <p
                                    class="text-xs text-content-secondary mt-1 truncate"
                                >
                                    {word.zh_preview.slice(0, 40)}...
                                </p>
                            {/if}
                        </div>
                        <div class="flex items-center gap-3 flex-shrink-0">
                            <span class="text-xs text-content-tertiary"
                                >#{getRank(word.lemma)}</span
                            >
                            <span
                                class="text-xs font-mono bg-surface-page text-content-secondary px-2 py-0.5 rounded-full"
                            >
                                {word.count}
                            </span>
                        </div>
                    </button>
                {/each}
            </div>
        </div>
    {/if}
</div>

<style>
    .word-list-container {
        height: 100%;
        overflow-y: auto;
        contain: strict;
        scrollbar-width: thin;
        scrollbar-color: var(--color-border-hover) transparent;
    }

    .word-list-container::-webkit-scrollbar {
        width: 6px;
    }

    .word-list-container::-webkit-scrollbar-track {
        background: transparent;
    }

    .word-list-container::-webkit-scrollbar-thumb {
        background-color: var(--color-border-hover);
        border-radius: 3px;
    }

    .word-list-container::-webkit-scrollbar-thumb:hover {
        background-color: var(--color-content-tertiary);
    }

    .virtual-scroll-wrapper {
        position: relative;
        width: 100%;
    }

    .word-list {
        display: flex;
        flex-direction: column;
        will-change: transform;
    }

    .list-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.875rem 1rem;
        cursor: pointer;
        border-bottom: 1px solid var(--color-border);
        background-color: var(--color-surface-primary);
        text-align: left;
        transition: background-color 0.15s ease;
        height: 72px;
        box-sizing: border-box;
    }

    .list-item:hover {
        background-color: var(--color-surface-hover);
    }

    .list-item:global(.active-item) {
        background-color: var(--color-accent-soft);
    }

    .browse-cell {
        padding: 0.5rem 0.75rem;
        background-color: var(--color-surface-primary);
        border-radius: 6px;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--color-content-primary);
        border: 1px solid var(--color-border);
        cursor: pointer;
        transition: all 0.15s ease;
        text-align: center;
    }

    .browse-cell:hover {
        background-color: var(--color-surface-hover);
        border-color: var(--color-border-hover);
    }

    .browse-cell:global(.active-item) {
        background-color: var(--color-accent-soft);
        border-color: var(--color-accent);
        color: var(--color-accent);
    }

    .grid-container {
        will-change: transform;
    }
</style>
