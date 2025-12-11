<script lang="ts">
    import { Rating } from "ts-fsrs";
    import { getIntervalText } from "$lib/stores/srs.svelte";

    interface Props {
        onRate: (rating: Rating) => void;
        showHint?: boolean;
    }

    let { onRate, showHint = false }: Props = $props();

    const buttons = [
        { rating: Rating.Again, label: "忘記", color: "srs-again" },
        { rating: Rating.Hard, label: "困難", color: "srs-hard" },
        { rating: Rating.Good, label: "普通", color: "srs-good" },
        { rating: Rating.Easy, label: "簡單", color: "srs-easy" },
    ] as const;
</script>

<div class="grid grid-cols-4 gap-2">
    {#each buttons as { rating, label, color }}
        <button
            onclick={() => onRate(rating)}
            class="rating-button flex flex-col items-center py-3.5 px-2 rounded-lg border border-transparent transition-all group"
            data-color={color}
        >
            <span
                class="text-base font-medium text-content-secondary transition-colors"
            >
                {label}
            </span>
            <span class="text-sm text-content-tertiary mt-1">
                {getIntervalText(rating)}
            </span>
        </button>
    {/each}
</div>

{#if showHint}
    <div class="mt-3 text-center">
        <p class="text-xs text-content-tertiary/50">1 · 2 · 3 · 4</p>
    </div>
{/if}

<style>
    .rating-button[data-color="srs-again"]:hover {
        border-color: var(--color-srs-again-border);
        background-color: var(--color-srs-again-soft);
    }
    .rating-button[data-color="srs-again"]:hover span:first-child {
        color: var(--color-srs-again);
    }

    .rating-button[data-color="srs-hard"]:hover {
        border-color: var(--color-srs-hard-border);
        background-color: var(--color-srs-hard-soft);
    }
    .rating-button[data-color="srs-hard"]:hover span:first-child {
        color: var(--color-srs-hard);
    }

    .rating-button[data-color="srs-good"]:hover {
        border-color: var(--color-srs-good-border);
        background-color: var(--color-srs-good-soft);
    }
    .rating-button[data-color="srs-good"]:hover span:first-child {
        color: var(--color-srs-good);
    }

    .rating-button[data-color="srs-easy"]:hover {
        border-color: var(--color-srs-easy-border);
        background-color: var(--color-srs-easy-soft);
    }
    .rating-button[data-color="srs-easy"]:hover span:first-child {
        color: var(--color-srs-easy);
    }

    .rating-button:focus-visible {
        outline: none;
        box-shadow: 0 0 0 2px var(--color-surface-primary), 0 0 0 4px var(--color-accent);
    }
</style>
