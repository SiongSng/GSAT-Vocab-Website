<script lang="ts">
    import type { VocabIndexItem } from "$lib/types/vocab";
    import {
        isWordIndexItem,
        isPhraseIndexItem,
        isPatternIndexItem,
    } from "$lib/types/vocab";
    import {
        selectWordAndNavigate,
        getVocabStore,
    } from "$lib/stores/vocab.svelte";

    const ITEM_HEIGHT = 48;
    const GRID_ITEM_HEIGHT = 40;
    const BUFFER_COUNT = 5;

    interface Props {
        words: VocabIndexItem[];
        isGridMode?: boolean;
    }

    let { words, isGridMode = false }: Props = $props();

    const vocab = getVocabStore();

    let scrollTop = $state(0);
    let containerHeight = $state(0);

    async function handleWordClick(word: VocabIndexItem) {
        await selectWordAndNavigate(word.lemma, word.type);
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
</script>

<div
    class="word-list-container"
    bind:clientHeight={containerHeight}
    onscroll={handleScroll}
>
    {#if words.length === 0}
        <div
            class="flex flex-col items-center justify-center h-full px-4 py-12"
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
                        class:phrase-cell={word.type === "phrase"}
                        class:pattern-cell={word.type === "pattern"}
                        class:active-item={vocab.selectedLemma === word.lemma}
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
                        class:active-item={vocab.selectedLemma === word.lemma}
                        data-lemma={word.lemma}
                        onclick={() => handleWordClick(word)}
                        type="button"
                    >
                        <span class="item-lemma">{word.lemma}</span>
                        <span class="item-def">
                            {#if isWordIndexItem(word) || isPhraseIndexItem(word)}
                                {word.zh_preview || ""}
                            {:else if isPatternIndexItem(word)}
                                {word.pattern_category}
                            {/if}
                        </span>
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
        overflow-x: hidden;
        contain: strict;
        scrollbar-width: none; /* Firefox */
    }

    .word-list-container::-webkit-scrollbar {
        display: none; /* Chrome, Safari */
    }

    .virtual-scroll-wrapper {
        position: relative;
        width: 100%;
        padding-bottom: var(--bottom-nav-height);
    }

    .word-list {
        display: flex;
        flex-direction: column;
        will-change: transform;
    }

    .list-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0 0.75rem;
        cursor: pointer;
        border-left: 2px solid transparent;
        background-color: var(--color-surface-primary);
        text-align: left;
        height: 48px;
        box-sizing: border-box;
    }

    .list-item:hover {
        background-color: var(--color-surface-hover);
    }

    .list-item.active-item {
        background-color: var(--color-accent-soft);
        border-left-color: var(--color-accent);
    }

    .item-lemma {
        font-size: 0.9375rem;
        font-weight: 600;
        color: var(--color-content-primary);
        letter-spacing: -0.01em;
        flex-shrink: 0;
    }

    .item-def {
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
        min-width: 0;
    }

    .list-item.active-item .item-def {
        color: var(--color-content-secondary);
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

    .browse-cell.active-item {
        background-color: var(--color-accent-soft);
        border-color: var(--color-accent);
        color: var(--color-accent);
    }

    .browse-cell.phrase-cell {
        border-left: 3px solid #10b981;
    }

    .browse-cell.pattern-cell {
        border-left: 3px solid #8b5cf6;
    }

    .grid-container {
        will-change: transform;
    }
</style>
