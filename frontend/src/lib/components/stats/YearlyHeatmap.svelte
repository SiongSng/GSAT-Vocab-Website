<script lang="ts">
    import type { HeatmapCell } from "$lib/utils/stats";

    interface Props {
        data: HeatmapCell[][];
    }

    let { data }: Props = $props();

    const months = [
        "1月",
        "2月",
        "3月",
        "4月",
        "5月",
        "6月",
        "7月",
        "8月",
        "9月",
        "10月",
        "11月",
        "12月",
    ];

    const dayLabels = ["", "一", "", "三", "", "五", ""];

    // Calculate month labels with spans
    const monthLabels = $derived(() => {
        if (data.length === 0) return [];

        const labels: { month: string; startWeek: number; span: number }[] = [];
        let currentMonth = -1;
        let currentYear = -1;
        let startIndex = 0;

        data.forEach((week, weekIndex) => {
            if (week.length === 0) return;
            const firstCell = week.find((c) => c.date);
            if (!firstCell) return;

            const date = new Date(firstCell.date + "T00:00:00");
            const year = date.getFullYear();
            const month = date.getMonth();

            if (month !== currentMonth || year !== currentYear) {
                if (currentMonth !== -1 && labels.length > 0) {
                    labels[labels.length - 1].span = weekIndex - startIndex;
                }
                labels.push({
                    month: months[month],
                    startWeek: weekIndex,
                    span: 1,
                });
                currentMonth = month;
                currentYear = year;
                startIndex = weekIndex;
            }
        });

        if (labels.length > 0) {
            labels[labels.length - 1].span = data.length - startIndex;
        }

        return labels;
    });

    function formatTooltip(cell: HeatmapCell): string {
        if (cell.count === 0) {
            return `${cell.date}: 無學習記錄`;
        }
        return `${cell.date}: ${cell.count} 張卡片`;
    }
</script>

<div class="heatmap-container-outer">
    <div class="heatmap-header">
        <h3 class="chart-title">過去 6 個月</h3>
        <div class="legend">
            <span class="legend-text">少</span>
            <div class="legend-cells">
                <div class="cell level-0"></div>
                <div class="cell level-1"></div>
                <div class="cell level-2"></div>
                <div class="cell level-3"></div>
                <div class="cell level-4"></div>
            </div>
            <span class="legend-text">多</span>
        </div>
    </div>

    <div class="heatmap-grid">
        <!-- Month Labels (Row 1) -->
        {#each monthLabels() as label}
            <div
                class="month-label"
                style="grid-column: {label.startWeek +
                    2} / span {label.span}; grid-row: 1;"
            >
                {label.month}
            </div>
        {/each}

        <!-- Day Labels (Col 1, Rows 2-8) -->
        {#each dayLabels as label, i}
            <div class="day-label" style="grid-column: 1; grid-row: {i + 2};">
                {label}
            </div>
        {/each}

        <!-- Heatmap Cells -->
        {#each data as week, weekIndex}
            <!-- We don't use week container anymore to allow subgrid-like alignment if needed,
                 but actually we can just place cells directly. -->
            {#each week as cell, dayIndex}
                <div
                    class="cell level-{cell.level}"
                    title={formatTooltip(cell)}
                    style="grid-column: {weekIndex + 2}; grid-row: {dayIndex +
                        2};"
                ></div>
            {/each}
        {/each}
    </div>
</div>

<style>
    .heatmap-container-outer {
        width: 100%;
        overflow-x: auto;
    }

    .heatmap-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .chart-title {
        font-size: 0.8125rem;
        font-weight: 600;
        color: var(--color-section-header);
    }

    .legend {
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }

    .legend-text {
        font-size: 0.6875rem;
        color: var(--color-content-tertiary);
    }

    .legend-cells {
        display: flex;
        gap: 2px;
    }

    .legend-cells .cell {
        width: 10px;
        height: 10px;
    }

    /* Grid Layout - GitHub style responsive */
    .heatmap-grid {
        display: grid;
        grid-template-columns: 1.25rem repeat(27, minmax(0, 1fr));
        grid-template-rows: auto repeat(7, minmax(0, 1fr));
        gap: 2px;
        width: 100%;
        min-width: 400px;
    }

    @media (min-width: 768px) {
        .heatmap-grid {
            gap: 5px;
        }
    }

    .month-label {
        font-size: 0.625rem;
        color: var(--color-content-tertiary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        padding-bottom: 0.25rem;
        align-self: end;
    }

    .day-label {
        font-size: 0.5625rem;
        color: var(--color-content-tertiary);
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 4px;
    }

    .cell {
        width: 100%;
        aspect-ratio: 1;
        border-radius: 2px;
        background-color: var(--color-surface-secondary);
    }

    .cell.level-0 {
        background-color: var(--color-surface-secondary);
    }
    .cell.level-1 {
        background-color: rgba(32, 125, 255, 0.2);
    }
    .cell.level-2 {
        background-color: rgba(32, 125, 255, 0.4);
    }
    .cell.level-3 {
        background-color: rgba(32, 125, 255, 0.6);
    }
    .cell.level-4 {
        background-color: var(--color-accent);
    }
</style>
