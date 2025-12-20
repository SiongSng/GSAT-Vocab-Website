<script lang="ts">
    interface YearData {
        year: number;
        count: number;
    }

    interface Props {
        data: YearData[];
    }

    let { data }: Props = $props();

    const sortedData = $derived(
        [...data].sort((a, b) => a.year - b.year).slice(-10),
    );

    const maxCount = $derived(Math.max(...sortedData.map((d) => d.count), 1));

    function getBarHeight(count: number): number {
        return (count / maxCount) * 100;
    }
</script>

<div class="year-chart">
    {#if sortedData.length > 0}
        <div class="chart-container">
            {#each sortedData as item}
                <div class="bar-column">
                    <div class="bar-area">
                        <div
                            class="bar"
                            style="height: {getBarHeight(item.count)}%"
                            title="{item.year}: {item.count}次"
                        ></div>
                    </div>
                    <span class="year-label">
                        '{String(item.year).slice(-2)}
                    </span>
                </div>
            {/each}
        </div>
    {:else}
        <p class="text-sm text-content-tertiary text-center py-4">
            暫無年份分布資料
        </p>
    {/if}
</div>

<style>
    .chart-container {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 4px;
        height: 80px;
    }

    .bar-column {
        flex: 1;
        min-width: 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    .bar-area {
        width: 100%;
        height: 60px;
        display: flex;
        align-items: flex-end;
        justify-content: center;
    }

    .bar {
        width: 100%;
        max-width: 24px;
        min-height: 4px;
        background-color: var(--color-accent);
        opacity: 0.7;
        border-radius: 2px 2px 0 0;
        transition: opacity 0.15s ease;
    }

    .bar:hover {
        opacity: 1;
    }

    .year-label {
        font-size: 0.6875rem;
        font-family: ui-monospace, monospace;
        color: var(--color-content-tertiary);
        margin-top: 6px;
    }
</style>
