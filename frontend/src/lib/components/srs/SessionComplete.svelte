<script lang="ts">
    import { getSRSStore } from "$lib/stores/srs.svelte";
    import { getAllCards } from "$lib/stores/srs-storage";
    import { State } from "ts-fsrs";

    interface Props {
        onBackToDashboard: () => void;
    }

    let { onBackToDashboard }: Props = $props();

    const srs = getSRSStore();

    const learnedLemmaCount = $derived.by(() => {
        const cards = getAllCards();
        const learnedLemmas = new Set<string>();
        for (const card of cards) {
            if (card.state !== State.New) {
                learnedLemmas.add(card.lemma);
            }
        }
        return learnedLemmas.size;
    });

    const sessionDuration = $derived.by(() => {
        const start = srs.sessionStats.startTime;
        const end = srs.sessionStats.endTime ?? new Date();
        const diffMs = end.getTime() - start.getTime();
        const diffMinutes = Math.round(diffMs / (1000 * 60));
        if (diffMinutes < 1) return "<1 分鐘";
        if (diffMinutes < 60) return `${diffMinutes} 分鐘`;
        const hours = Math.floor(diffMinutes / 60);
        const mins = diffMinutes % 60;
        return `${hours} 小時 ${mins} 分鐘`;
    });

    const total = $derived(srs.sessionStats.cardsStudied);

    const ratingStats = $derived.by(() => {
        const t = total || 1;
        return {
            easy: {
                count: srs.sessionStats.easyCount,
                percent: Math.round((srs.sessionStats.easyCount / t) * 100),
            },
            good: {
                count: srs.sessionStats.goodCount,
                percent: Math.round((srs.sessionStats.goodCount / t) * 100),
            },
            hard: {
                count: srs.sessionStats.hardCount,
                percent: Math.round((srs.sessionStats.hardCount / t) * 100),
            },
            again: {
                count: srs.sessionStats.againCount,
                percent: Math.round((srs.sessionStats.againCount / t) * 100),
            },
        };
    });

    const hasMoreCards = $derived(
        srs.deckStats.newCount > 0 ||
            srs.deckStats.learningCount > 0 ||
            srs.deckStats.reviewCount > 0,
    );
</script>

<div
    class="bg-surface-primary rounded-lg border border-border shadow-card p-7 max-w-lg mx-auto"
>
    <div class="text-center mb-7">
        <div
            class="w-12 h-12 mx-auto mb-3 rounded-full bg-srs-good/10 flex items-center justify-center"
        >
            <svg
                class="w-6 h-6 text-srs-good"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                stroke-width="2"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="m4.5 12.75 6 6 9-13.5"
                />
            </svg>
        </div>
        <h2 class="text-xl font-semibold tracking-tight text-content-primary">
            今日完成
        </h2>
        <p class="text-base text-content-tertiary mt-1">
            學習時間: {sessionDuration}
        </p>
    </div>

    <div class="grid grid-cols-2 gap-3 mb-6">
        <div class="p-4 rounded-md bg-surface-page/60 text-center">
            <div
                class="text-2xl font-semibold text-content-primary tracking-tight"
            >
                {srs.sessionStats.cardsStudied}
            </div>
            <div class="text-sm text-content-tertiary mt-1">完成卡片</div>
        </div>
        <div class="p-4 rounded-md bg-surface-page/60 text-center">
            <div
                class="text-2xl font-semibold text-content-primary tracking-tight"
            >
                {learnedLemmaCount}
            </div>
            <div class="text-sm text-content-tertiary mt-1">已學詞彙</div>
        </div>
    </div>

    {#if total > 0}
        <div class="mb-6 p-4 rounded-md bg-surface-page/40">
            <div class="text-sm font-medium text-content-secondary mb-3">
                正確率分布
            </div>
            <div class="space-y-2.5">
                <div class="flex items-center gap-3">
                    <span class="text-xs text-content-tertiary w-10">簡單</span>
                    <div
                        class="flex-1 h-3 bg-surface-secondary rounded-full overflow-hidden"
                    >
                        <div
                            class="h-full bg-srs-easy transition-all duration-500"
                            style="width: {ratingStats.easy.percent}%"
                        ></div>
                    </div>
                    <span class="text-xs text-content-secondary w-14 text-right"
                        >{ratingStats.easy.percent}% ({ratingStats.easy
                            .count})</span
                    >
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-xs text-content-tertiary w-10">良好</span>
                    <div
                        class="flex-1 h-3 bg-surface-secondary rounded-full overflow-hidden"
                    >
                        <div
                            class="h-full bg-srs-good transition-all duration-500"
                            style="width: {ratingStats.good.percent}%"
                        ></div>
                    </div>
                    <span class="text-xs text-content-secondary w-14 text-right"
                        >{ratingStats.good.percent}% ({ratingStats.good
                            .count})</span
                    >
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-xs text-content-tertiary w-10">困難</span>
                    <div
                        class="flex-1 h-3 bg-surface-secondary rounded-full overflow-hidden"
                    >
                        <div
                            class="h-full bg-srs-hard transition-all duration-500"
                            style="width: {ratingStats.hard.percent}%"
                        ></div>
                    </div>
                    <span class="text-xs text-content-secondary w-14 text-right"
                        >{ratingStats.hard.percent}% ({ratingStats.hard
                            .count})</span
                    >
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-xs text-content-tertiary w-10">重來</span>
                    <div
                        class="flex-1 h-3 bg-surface-secondary rounded-full overflow-hidden"
                    >
                        <div
                            class="h-full bg-srs-again transition-all duration-500"
                            style="width: {ratingStats.again.percent}%"
                        ></div>
                    </div>
                    <span class="text-xs text-content-secondary w-14 text-right"
                        >{ratingStats.again.percent}% ({ratingStats.again
                            .count})</span
                    >
                </div>
            </div>
        </div>
    {/if}

    {#if hasMoreCards}
        <div
            class="p-4 rounded-md border border-border/60 bg-surface-secondary/30 mb-6"
        >
            <div class="text-sm font-medium text-content-secondary mb-2">
                還有更多卡片
            </div>
            <div class="flex gap-5 text-base">
                {#if srs.deckStats.learningCount > 0}
                    <span class="text-srs-hard"
                        >{srs.deckStats.learningCount} 學習中</span
                    >
                {/if}
                {#if srs.deckStats.reviewCount > 0}
                    <span class="text-srs-again"
                        >{srs.deckStats.reviewCount} 待複習</span
                    >
                {/if}
                {#if srs.deckStats.newCount > 0}
                    <span class="text-srs-easy"
                        >{srs.deckStats.newCount} 新卡片</span
                    >
                {/if}
            </div>
        </div>
    {/if}

    <button
        onclick={onBackToDashboard}
        class="w-full py-2.5 px-5 bg-content-primary text-white rounded-md text-base font-medium hover:opacity-90 transition-opacity"
    >
        {hasMoreCards ? "繼續學習" : "返回首頁"}
    </button>
</div>
