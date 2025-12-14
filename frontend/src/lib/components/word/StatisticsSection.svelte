<script lang="ts">
    import type { FrequencyData, VocabSense } from "$lib/types/vocab";
    import YearDistributionChart from "$lib/components/charts/YearDistributionChart.svelte";

    interface Props {
        frequency: FrequencyData;
        senses: VocabSense[];
    }

    let { frequency, senses }: Props = $props();

    const yearDistribution = $derived.by(() => {
        const yearCounts = new Map<number, number>();
        for (const sense of senses) {
            for (const example of sense.examples) {
                const year = example.source.year;
                yearCounts.set(year, (yearCounts.get(year) ?? 0) + 1);
            }
        }
        return Array.from(yearCounts.entries()).map(([year, count]) => ({
            year,
            count,
        }));
    });

    const posDistribution = $derived.by(() => {
        const posCounts = new Map<string, number>();
        for (const sense of senses) {
            const pos = sense.pos;
            posCounts.set(pos, (posCounts.get(pos) ?? 0) + sense.examples.length);
            if (sense.examples.length === 0) {
                posCounts.set(pos, (posCounts.get(pos) ?? 0) + 1);
            }
        }
        const total = Array.from(posCounts.values()).reduce((a, b) => a + b, 0);
        return Array.from(posCounts.entries())
            .map(([pos, count]) => ({
                pos,
                count,
                percentage: total > 0 ? Math.round((count / total) * 100) : 0,
            }))
            .sort((a, b) => b.count - a.count);
    });

    const importanceScore = $derived(
        frequency.ml_score ?? frequency.weighted_score / 30,
    );

    const importancePercentage = $derived(Math.round(importanceScore * 100));
</script>

<div class="statistics-section space-y-5">
    <div class="stat-grid grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="stat-item text-center py-3 px-2 rounded-lg bg-surface-page/60">
            <div
                class="text-xl font-semibold text-content-primary tracking-tight"
            >
                {frequency.total_occurrences}
            </div>
            <div class="text-xs text-content-secondary mt-1">總出現次數</div>
        </div>
        <div class="stat-item text-center py-3 px-2 rounded-lg bg-surface-page/60">
            <div
                class="text-xl font-semibold text-content-primary tracking-tight"
            >
                {frequency.tested_count}
            </div>
            <div class="text-xs text-content-secondary mt-1">考題出現</div>
        </div>
        <div class="stat-item text-center py-3 px-2 rounded-lg bg-surface-page/60">
            <div
                class="text-xl font-semibold text-content-primary tracking-tight"
            >
                {frequency.year_spread}
            </div>
            <div class="text-xs text-content-secondary mt-1">跨越年數</div>
        </div>
        <div class="stat-item text-center py-3 px-2 rounded-lg bg-surface-page/60">
            <div
                class="text-xl font-semibold text-accent tracking-tight"
            >
                {importancePercentage}%
            </div>
            <div class="text-xs text-content-secondary mt-1">重要性</div>
        </div>
    </div>

    {#if yearDistribution.length > 0}
        <div class="year-distribution">
            <h4 class="text-xs font-medium text-content-tertiary mb-3">
                年份分布
            </h4>
            <YearDistributionChart data={yearDistribution} />
        </div>
    {/if}

    {#if posDistribution.length > 1}
        <div class="pos-distribution">
            <h4 class="text-xs font-medium text-content-tertiary mb-3">
                詞性分布
            </h4>
            <div class="space-y-2">
                {#each posDistribution as { pos, percentage }}
                    <div class="pos-bar flex items-center gap-3">
                        <span
                            class="text-xs font-medium text-content-secondary w-12 uppercase"
                            >{pos}</span
                        >
                        <div
                            class="flex-1 h-2 bg-surface-secondary rounded-full overflow-hidden"
                        >
                            <div
                                class="h-full bg-accent/60 rounded-full transition-all"
                                style="width: {percentage}%"
                            ></div>
                        </div>
                        <span class="text-xs text-content-tertiary w-10"
                            >{percentage}%</span
                        >
                    </div>
                {/each}
            </div>
        </div>
    {/if}
</div>
