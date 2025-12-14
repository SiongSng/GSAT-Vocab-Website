<script lang="ts">
    import type { VocabIndexItem } from "$lib/types/vocab";

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

    function formatPos(pos: string): string {
        const posMap: Record<string, string> = {
            NOUN: "n.",
            VERB: "v.",
            ADJ: "adj.",
            ADV: "adv.",
            PROPN: "n.",
            ADP: "prep.",
            CONJ: "conj.",
            PRON: "pron.",
            DET: "det.",
            INTJ: "int.",
        };
        return posMap[pos] ?? pos.toLowerCase();
    }

    function formatLevel(level: number | null): string {
        if (level === null) return "";
        return `L${level}`;
    }

    function getImportancePercent(score: number): number {
        return Math.min(Math.round(score * 100), 100);
    }

    function getTierBadge(tier: string): { label: string; class: string } | null {
        switch (tier) {
            case "tested":
                return { label: "考題", class: "tier-tested" };
            case "translation":
                return { label: "翻譯", class: "tier-translation" };
            default:
                return null;
        }
    }
</script>

{#if isGridMode}
    <button
        class="browse-cell {isActive ? 'active-item' : ''}"
        {onclick}
        type="button"
    >
        <span class="font-medium">{word.lemma}</span>
        {#if word.level !== null}
            <span class="grid-level">L{word.level}</span>
        {/if}
    </button>
{:else}
    <button
        class="list-item {isActive ? 'active-item' : ''}"
        {onclick}
        type="button"
    >
        <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 flex-wrap">
                <span class="font-semibold text-content-primary">{word.lemma}</span>
                <span class="meta-text">{formatPos(word.primary_pos)}</span>
                {#if word.level !== null}
                    <span class="meta-separator">·</span>
                    <span class="meta-text">{formatLevel(word.level)}</span>
                {/if}
                {#if word.in_official_list}
                    <span class="official-badge">官方</span>
                {/if}
                {#if getTierBadge(word.tier)}
                    {@const badge = getTierBadge(word.tier)}
                    <span class="tier-badge {badge?.class}">{badge?.label}</span>
                {/if}
            </div>
            {#if word.zh_preview}
                <p class="text-xs text-content-secondary mt-1 truncate">
                    {word.zh_preview}
                </p>
            {/if}
            <div class="stats-row">
                <span class="stat-item">{word.count}次</span>
                {#if word.year_spread > 0}
                    <span class="meta-separator">·</span>
                    <span class="stat-item">{word.year_spread}年</span>
                {/if}
                {#if word.tested_count > 0}
                    <span class="meta-separator">·</span>
                    <span class="stat-item">{word.tested_count}題</span>
                {/if}
            </div>
        </div>
        <div class="flex flex-col items-end gap-1 flex-shrink-0">
            <div class="importance-container">
                <div class="importance-bar">
                    <div
                        class="importance-fill"
                        style="width: {getImportancePercent(word.importance_score)}%"
                    ></div>
                </div>
                <span class="importance-label">{getImportancePercent(word.importance_score)}%</span>
            </div>
            <span class="text-xs text-content-tertiary">#{rank}</span>
        </div>
    </button>
{/if}

<style>
    .browse-cell {
        padding: 0.5rem 0.75rem;
        background-color: var(--color-surface-primary);
        border-radius: 6px;
        font-size: 0.875rem;
        color: var(--color-content-primary);
        border: 1px solid var(--color-border);
        cursor: pointer;
        transition: all 0.15s ease;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.25rem;
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

    .grid-level {
        font-size: 0.625rem;
        font-weight: 500;
        color: var(--color-content-tertiary);
    }

    .list-item {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 0.75rem 1rem;
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

    .meta-text {
        font-size: 0.6875rem;
        font-weight: 500;
        color: var(--color-content-tertiary);
    }

    .meta-separator {
        font-size: 0.625rem;
        color: var(--color-content-tertiary);
        opacity: 0.5;
    }

    .official-badge {
        font-size: 0.625rem;
        font-weight: 600;
        color: var(--color-accent);
        padding: 0.125rem 0.375rem;
        background-color: var(--color-accent-soft);
        border-radius: 4px;
    }

    .tier-badge {
        font-size: 0.625rem;
        font-weight: 600;
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
    }

    .tier-tested {
        color: var(--color-srs-good);
        background-color: var(--color-srs-good-soft);
    }

    .tier-translation {
        color: var(--color-srs-easy);
        background-color: var(--color-srs-easy-soft);
    }

    .stats-row {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        margin-top: 0.375rem;
    }

    .stat-item {
        font-size: 0.625rem;
        color: var(--color-content-tertiary);
    }

    .importance-container {
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }

    .importance-bar {
        width: 2.5rem;
        height: 4px;
        background-color: var(--color-surface-page);
        border-radius: 2px;
        overflow: hidden;
    }

    .importance-fill {
        height: 100%;
        background-color: var(--color-accent);
        border-radius: 2px;
        transition: width 0.2s ease;
    }

    .importance-label {
        font-size: 0.625rem;
        font-weight: 600;
        color: var(--color-content-tertiary);
        min-width: 2rem;
        text-align: right;
    }
</style>
