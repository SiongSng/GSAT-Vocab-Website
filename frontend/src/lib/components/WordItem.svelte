<script lang="ts">
    import type { VocabIndexItem } from "$lib/api";

    interface Props {
        word: VocabIndexItem;
        rank: number;
        isGridMode?: boolean;
        isActive?: boolean;
        onclick?: () => void;
    }

    let {
        word,
        rank,
        isGridMode = false,
        isActive = false,
        onclick,
    }: Props = $props();
</script>

{#if isGridMode}
    <button
        class="browse-cell {isActive ? 'active-item' : ''}"
        {onclick}
        type="button"
    >
        {word.lemma}
    </button>
{:else}
    <button
        class="list-item {isActive ? 'active-item' : ''}"
        {onclick}
        type="button"
    >
        <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
                <span class="font-semibold text-content-primary"
                    >{word.lemma}</span
                >
                <span class="text-xs font-medium text-content-tertiary"
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
                <p class="text-xs text-content-secondary mt-1 truncate">
                    {word.zh_preview.slice(0, 40)}...
                </p>
            {/if}
        </div>
        <div class="flex items-center gap-3 flex-shrink-0">
            <span class="text-xs text-content-tertiary">#{rank}</span>
            <span
                class="text-xs font-mono bg-surface-page text-content-secondary px-2 py-0.5 rounded-full"
            >
                {word.count}
            </span>
        </div>
    </button>
{/if}

<style>
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

    .list-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.875rem 1rem;
        cursor: pointer;
        border-bottom: 1px solid var(--color-border);
        background-color: var(--color-surface-primary);
        transition: background-color 0.15s ease;
        width: 100%;
        text-align: left;
    }

    .list-item:hover {
        background-color: var(--color-surface-hover);
    }

    .list-item.active-item {
        background-color: var(--color-accent-soft);
    }
</style>
