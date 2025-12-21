<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { getAllDailyStats, onDataChange } from "$lib/stores/srs-storage";
    import { calculateStreak, type StreakInfo } from "$lib/utils/stats";
    import { navigate } from "$lib/stores/router.svelte";

    let streakInfo: StreakInfo = $state({
        currentStreak: 0,
        longestStreak: 0,
        lastStudyDate: null,
        isActiveToday: false,
    });

    async function loadStreak() {
        const stats = await getAllDailyStats();
        streakInfo = calculateStreak(stats);
    }

    const unsubscribe = onDataChange(() => {
        loadStreak();
    });

    onMount(() => {
        loadStreak();
    });

    onDestroy(() => {
        unsubscribe();
    });

    function handleClick() {
        navigate({ name: "stats" });
    }
</script>

<button
    class="streak-badge"
    class:active={streakInfo.currentStreak > 0}
    onclick={handleClick}
    title="連續學習 {streakInfo.currentStreak} 天"
>
    <svg class="streak-icon" viewBox="0 0 24 24" fill="currentColor">
        <path
            fill-rule="evenodd"
            clip-rule="evenodd"
            d="M12.534 2.232a.75.75 0 0 0-1.068 0c-1.615 1.653-2.703 3.515-3.327 5.307-.553 1.588-.722 3.08-.667 4.327-1.124-.627-1.91-1.561-2.307-2.573a.75.75 0 0 0-1.36-.057c-.798 1.57-.834 3.528-.235 5.336.607 1.83 1.892 3.524 3.87 4.583C9.398 20.105 10.685 20.5 12 20.5c1.315 0 2.602-.395 3.56-1.345 1.978-1.059 3.263-2.753 3.87-4.583.599-1.808.563-3.766-.235-5.336a.75.75 0 0 0-1.36.057c-.397 1.012-1.183 1.946-2.307 2.573.055-1.247-.114-2.739-.667-4.327-.624-1.792-1.712-3.654-3.327-5.307ZM12 18.5c-.935 0-1.865-.283-2.598-.84C8.044 16.63 7.082 14.978 7 13c1.065.625 2.275.875 3.375.625.55-.125.875-.675.75-1.225-.125-.55-.625-.925-1.175-.8-.56.113-1.298-.012-2.05-.512.15-1.238.475-2.612 1.1-3.963.5 1.15.875 2.35 1.025 3.475.075.55.575.95 1.125.875.55-.075.925-.55.875-1.1-.075-.55-.2-1.125-.375-1.713 1.6 1.75 2.35 3.488 2.35 4.838 0 .55.45 1 1 1s1-.45 1-1c0-.563-.063-1.113-.188-1.65.688.825 1.138 1.763 1.188 2.65-.082 1.978-1.044 3.63-2.402 4.66-.733.557-1.663.84-2.598.84Z"
        />
    </svg>
    {#if streakInfo.currentStreak > 0}
        <span class="streak-count">{streakInfo.currentStreak}</span>
    {/if}
</button>

<style>
    .streak-badge {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.375rem 0.5rem;
        border-radius: 0.5rem;
        color: var(--color-content-tertiary);
        cursor: pointer;
        transition: all 0.15s ease;
        background: transparent;
        border: none;
    }

    .streak-badge:hover {
        background-color: var(--color-surface-hover);
    }

    .streak-badge.active {
        color: var(--color-srs-hard);
    }

    .streak-badge.active:hover {
        background-color: var(--color-srs-hard-soft);
    }

    .streak-icon {
        width: 1.25rem;
        height: 1.25rem;
    }

    .streak-count {
        font-size: 0.875rem;
        font-weight: 700;
        color: inherit;
    }
</style>
