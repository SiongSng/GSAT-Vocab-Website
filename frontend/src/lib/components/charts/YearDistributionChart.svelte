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

    const maxCount = $derived(
        Math.max(...sortedData.map((d) => d.count), 1),
    );

    function getBarHeight(count: number): number {
        return (count / maxCount) * 100;
    }
</script>

<div class="year-chart">
    <div class="chart-container flex items-end justify-between gap-1 h-20">
        {#each sortedData as item}
            <div class="bar-wrapper flex flex-col items-center flex-1 group">
                <div
                    class="bar bg-accent/70 group-hover:bg-accent rounded-t transition-all min-h-[4px] w-full max-w-6"
                    style="height: {getBarHeight(item.count)}%"
                    title="{item.year}: {item.count}次"
                ></div>
                <span
                    class="text-xs text-content-tertiary mt-1.5 font-mono"
                >
                    '{String(item.year).slice(-2)}
                </span>
            </div>
        {/each}
    </div>
    {#if sortedData.length === 0}
        <p class="text-sm text-content-tertiary text-center py-4">
            暫無年份分布資料
        </p>
    {/if}
</div>

<style>
    .bar-wrapper {
        min-width: 20px;
    }
</style>
