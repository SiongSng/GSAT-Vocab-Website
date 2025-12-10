<script lang="ts">
    import { tick } from "svelte";
    import type { VocabIndexItem } from "$lib/api";
    import { getAppStore, openMobileDetail } from "$lib/stores/app.svelte";
    import { selectWord, getVocabStore } from "$lib/stores/vocab.svelte";

    const SKELETON_COUNT = 12;

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
    let previousActiveElement: HTMLElement | null = null;

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
        await selectWord(word.lemma);
        if (app.isMobile) {
            openMobileDetail();
        }
    }

    function getRank(lemma: string): number {
        return getRankMap().get(lemma) ?? 0;
    }

    $effect(() => {
        const selectedLemma = vocab.selectedLemma;
        const _ = words;

        tick().then(() => {
            if (previousActiveElement) {
                previousActiveElement.classList.remove("active-item");
                previousActiveElement = null;
            }
            if (selectedLemma && listContainer) {
                const el = listContainer.querySelector(
                    `[data-lemma="${CSS.escape(selectedLemma)}"]`,
                ) as HTMLElement | null;
                if (el) {
                    el.classList.add("active-item");
                    previousActiveElement = el;
                }
            }
        });
    });
</script>

<div class="word-list-container" bind:this={listContainer}>
    {#if !vocab.isReady}
        <div class="word-list">
            {#each Array(SKELETON_COUNT) as _, i}
                <div class="skeleton-item">
                    <div class="flex-1">
                        <div class="flex items-center gap-2">
                            <div class="skeleton-text w-24"></div>
                            <div class="skeleton-text w-12"></div>
                        </div>
                        <div class="skeleton-text w-48 mt-2"></div>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="skeleton-text w-8"></div>
                        <div class="skeleton-badge"></div>
                    </div>
                </div>
            {/each}
        </div>
    {:else if words.length === 0}
        <p class="p-4 text-slate-500 text-center">找不到符合條件的單詞</p>
    {:else if isGridMode}
        <div
            class="grid-container grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 p-2"
        >
            {#each words as word (word.lemma)}
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
    {:else}
        <div class="word-list">
            {#each words as word (word.lemma)}
                <button
                    class="list-item"
                    data-lemma={word.lemma}
                    onclick={() => handleWordClick(word)}
                    type="button"
                >
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="font-semibold text-slate-800"
                                >{word.lemma}</span
                            >
                            <span class="text-xs font-medium text-slate-500"
                                >{word.primary_pos}</span
                            >
                            {#if word.meaning_count > 1}
                                <span
                                    class="text-xs px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded"
                                >
                                    {word.meaning_count}義
                                </span>
                            {/if}
                        </div>
                        {#if word.zh_preview}
                            <p class="text-xs text-slate-600 mt-1 truncate">
                                {word.zh_preview.slice(0, 40)}...
                            </p>
                        {/if}
                    </div>
                    <div class="flex items-center gap-3 flex-shrink-0">
                        <span class="text-xs text-slate-400"
                            >#{getRank(word.lemma)}</span
                        >
                        <span
                            class="text-sm font-mono bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full"
                        >
                            {word.count}
                        </span>
                    </div>
                </button>
            {/each}
        </div>
    {/if}
</div>

<style>
    .word-list-container {
        height: 100%;
        overflow-y: auto;
        contain: strict;
    }

    .word-list {
        display: flex;
        flex-direction: column;
    }

    .list-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        cursor: pointer;
        border-bottom: 1px solid rgb(241 245 249);
        background-color: white;
        text-align: left;
        transition: background-color 0.15s ease;
        content-visibility: auto;
        contain-intrinsic-size: auto 72px;
    }

    .list-item:hover {
        background-color: rgb(241 245 249);
    }

    .list-item:global(.active-item) {
        background-color: rgb(238 242 255);
    }

    .browse-cell {
        padding: 0.5rem 0.75rem;
        background-color: white;
        border-radius: 0.5rem;
        font-size: 0.875rem;
        font-weight: 500;
        color: rgb(51 65 85);
        border: 1px solid rgb(226 232 240);
        cursor: pointer;
        transition: all 0.15s ease;
        text-align: center;
    }

    .browse-cell:hover {
        background-color: rgb(241 245 249);
        border-color: rgb(199 210 254);
        transform: translateY(-1px);
    }

    .browse-cell:global(.active-item) {
        background-color: rgb(238 242 255);
        border-color: rgb(129 140 248);
        color: rgb(67 56 202);
    }

    .grid-container {
        content-visibility: auto;
        contain-intrinsic-size: auto 500px;
    }

    .skeleton-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid rgb(241 245 249);
        background-color: white;
    }

    .skeleton-text {
        height: 0.875rem;
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

    .skeleton-badge {
        width: 2.5rem;
        height: 1.5rem;
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

    @keyframes shimmer {
        0% {
            background-position: 200% 0;
        }
        100% {
            background-position: -200% 0;
        }
    }
</style>
