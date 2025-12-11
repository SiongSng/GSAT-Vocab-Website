<script lang="ts">
    import { Rating } from "ts-fsrs";
    import { getIntervalText } from "$lib/stores/srs.svelte";

    interface Props {
        onRate: (rating: Rating) => void;
    }

    let { onRate }: Props = $props();

    const buttons = [
        { rating: Rating.Again, label: "忘記", color: "srs-again" },
        { rating: Rating.Hard, label: "困難", color: "srs-hard" },
        { rating: Rating.Good, label: "普通", color: "srs-good" },
        { rating: Rating.Easy, label: "簡單", color: "srs-easy" },
    ] as const;

    function handleKeydown(event: KeyboardEvent) {
        if (event.key >= "1" && event.key <= "4") {
            const index = parseInt(event.key) - 1;
            onRate(buttons[index].rating);
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

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

<div class="mt-3 text-center">
    <p class="text-sm text-content-tertiary/50">按 1、2、3、4 快速選擇</p>
</div>

<style>
    .rating-button[data-color="srs-again"]:hover {
        border-color: rgba(229, 115, 115, 0.3);
        background-color: rgba(229, 115, 115, 0.05);
    }
    .rating-button[data-color="srs-again"]:hover span:first-child {
        color: #e57373;
    }

    .rating-button[data-color="srs-hard"]:hover {
        border-color: rgba(255, 183, 77, 0.3);
        background-color: rgba(255, 183, 77, 0.05);
    }
    .rating-button[data-color="srs-hard"]:hover span:first-child {
        color: #ffb74d;
    }

    .rating-button[data-color="srs-good"]:hover {
        border-color: rgba(129, 199, 132, 0.3);
        background-color: rgba(129, 199, 132, 0.05);
    }
    .rating-button[data-color="srs-good"]:hover span:first-child {
        color: #81c784;
    }

    .rating-button[data-color="srs-easy"]:hover {
        border-color: rgba(100, 181, 246, 0.3);
        background-color: rgba(100, 181, 246, 0.05);
    }
    .rating-button[data-color="srs-easy"]:hover span:first-child {
        color: #64b5f6;
    }
</style>
