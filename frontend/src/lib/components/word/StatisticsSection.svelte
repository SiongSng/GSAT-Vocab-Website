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
            for (const example of sense.examples ?? []) {
                const year = example.source.year;
                yearCounts.set(year, (yearCounts.get(year) ?? 0) + 1);
            }
        }
        return Array.from(yearCounts.entries())
            .map(([year, count]) => ({ year, count }))
            .sort((a, b) => a.year - b.year);
    });

    const posDistribution = $derived.by(() => {
        const posCounts = new Map<string, number>();
        for (const sense of senses) {
            const pos = sense.pos ?? "unknown";
            const exampleCount = sense.examples?.length ?? 0;
            const count = exampleCount > 0 ? exampleCount : 1;
            posCounts.set(pos, (posCounts.get(pos) ?? 0) + count);
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

    const posColors: Record<string, string> = {
        v: "var(--color-accent)",
        n: "var(--color-srs-good)",
        adj: "var(--color-srs-hard)",
        adv: "var(--color-srs-easy)",
        prep: "var(--color-srs-again)",
        conj: "#a78bfa",
        pron: "#f472b6",
        det: "#94a3b8",
        int: "#fb923c",
    };

    function getPosColor(pos: string): string {
        const normalizedPos = pos.toLowerCase().replace(".", "");
        return posColors[normalizedPos] ?? "var(--color-content-tertiary)";
    }

    function getPosLabel(pos: string): string {
        const labels: Record<string, string> = {
            v: "動詞",
            n: "名詞",
            adj: "形容詞",
            adv: "副詞",
            prep: "介系詞",
            conj: "連接詞",
            pron: "代名詞",
            det: "限定詞",
            int: "感嘆詞",
        };
        const normalizedPos = pos.toLowerCase().replace(".", "");
        return labels[normalizedPos] ?? pos;
    }
</script>

<div class="statistics-section space-y-5">
    <!-- Frequency Stats -->
    <div class="grid grid-cols-3 gap-3">
        <div class="text-center py-3 px-2 rounded-lg bg-surface-page">
            <div
                class="text-xl font-semibold text-content-primary tracking-tight"
            >
                {frequency.total_appearances}
            </div>
            <div class="text-xs text-content-tertiary mt-1">總出現</div>
        </div>
        <div class="text-center py-3 px-2 rounded-lg bg-surface-page">
            <div class="text-xl font-semibold text-accent tracking-tight">
                {frequency.tested_count}
            </div>
            <div class="text-xs text-content-tertiary mt-1">考題出現</div>
        </div>
        <div class="text-center py-3 px-2 rounded-lg bg-surface-page">
            <div
                class="text-xl font-semibold text-content-primary tracking-tight"
            >
                {frequency.year_spread}
            </div>
            <div class="text-xs text-content-tertiary mt-1">跨越年數</div>
        </div>
    </div>

    <!-- Year Distribution -->
    {#if yearDistribution.length > 0}
        <div class="year-distribution">
            <h4 class="text-xs font-medium text-content-tertiary mb-3">
                年份分布
            </h4>
            <YearDistributionChart data={yearDistribution} />
        </div>
    {/if}

    <!-- POS Distribution -->
    {#if posDistribution.length > 1}
        <div class="pos-distribution">
            <h4 class="text-xs font-medium text-content-tertiary mb-3">
                詞性分布
            </h4>

            <!-- Stacked bar -->
            <div class="flex h-2 rounded-full overflow-hidden mb-3">
                {#each posDistribution as { pos, percentage }}
                    {#if percentage > 0}
                        <div
                            class="h-full"
                            style="width: {percentage}%; background-color: {getPosColor(
                                pos,
                            )}"
                            title="{getPosLabel(pos)}: {percentage}%"
                        ></div>
                    {/if}
                {/each}
            </div>

            <!-- Legend -->
            <div class="flex flex-wrap gap-x-4 gap-y-1">
                {#each posDistribution as { pos, percentage }}
                    <div class="flex items-center gap-1.5">
                        <span
                            class="w-2 h-2 rounded-sm flex-shrink-0"
                            style="background-color: {getPosColor(pos)}"
                        ></span>
                        <span class="text-xs text-content-secondary">
                            {getPosLabel(pos)}
                        </span>
                        <span class="text-xs text-content-tertiary">
                            {percentage}%
                        </span>
                    </div>
                {/each}
            </div>
        </div>
    {/if}
</div>
