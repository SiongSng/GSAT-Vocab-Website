<script lang="ts">
    import { getSRSStore } from "$lib/stores/srs.svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";

    interface Props {
        onContinue: (words: string[]) => void;
        onDone: () => void;
    }

    let { onContinue, onDone }: Props = $props();

    const srs = getSRSStore();
    const vocab = getVocabStore();

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

    const correctRate = $derived.by(() => {
        const total = srs.sessionStats.cardsStudied;
        if (total === 0) return 0;
        const correct = srs.sessionStats.goodCount + srs.sessionStats.easyCount;
        return Math.round((correct / total) * 100);
    });

    const hasMoreCards = $derived(
        srs.deckStats.newCount > 0 ||
            srs.deckStats.learningCount > 0 ||
            srs.deckStats.reviewCount > 0,
    );

    function handleContinue() {
        const pool = vocab.index || [];
        const filtered = pool.filter((w) => w.primary_pos !== "PROPN");
        const shuffled = [...filtered].sort(() => Math.random() - 0.5);
        const words = shuffled.slice(0, 20).map((w) => w.lemma);
        onContinue(words);
    }
</script>

<div
    class="bg-surface-primary rounded-lg border border-border p-7 max-w-lg mx-auto"
>
    <div class="text-center mb-7">
        <div class="text-4xl mb-2">🎉</div>
        <h2 class="text-xl font-semibold tracking-tight text-content-primary">
            學習完成
        </h2>
        <p class="text-base text-content-tertiary mt-1">今天辛苦了！</p>
    </div>

    <div class="grid grid-cols-2 gap-3 mb-6">
        <div class="p-4 rounded-md bg-surface-page/60 text-center">
            <div
                class="text-2xl font-semibold text-content-primary tracking-tight"
            >
                {srs.sessionStats.cardsStudied}
            </div>
            <div class="text-sm text-content-tertiary mt-1">已複習卡片</div>
        </div>
        <div class="p-4 rounded-md bg-surface-page/60 text-center">
            <div
                class="text-2xl font-semibold text-content-primary tracking-tight"
            >
                {correctRate}%
            </div>
            <div class="text-sm text-content-tertiary mt-1">正確率</div>
        </div>
        <div class="p-4 rounded-md bg-surface-page/60 text-center">
            <div
                class="text-2xl font-semibold text-content-primary tracking-tight"
            >
                {sessionDuration}
            </div>
            <div class="text-sm text-content-tertiary mt-1">學習時間</div>
        </div>
        <div class="p-4 rounded-md bg-surface-page/60 text-center">
            <div
                class="text-2xl font-semibold text-content-primary tracking-tight"
            >
                {srs.sessionStats.easyCount + srs.sessionStats.goodCount}
            </div>
            <div class="text-sm text-content-tertiary mt-1">已掌握</div>
        </div>
    </div>

    {#if hasMoreCards}
        <div
            class="p-4 rounded-md border border-border/60 bg-surface-secondary/30 mb-6"
        >
            <div class="text-sm font-medium text-content-secondary mb-2">
                還有更多卡片
            </div>
            <div class="flex gap-5 text-base">
                {#if srs.deckStats.reviewCount > 0}
                    <span class="text-srs-again"
                        >{srs.deckStats.reviewCount} 待複習</span
                    >
                {/if}
                {#if srs.deckStats.learningCount > 0}
                    <span class="text-srs-hard"
                        >{srs.deckStats.learningCount} 學習中</span
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

    <div class="flex gap-3">
        {#if hasMoreCards}
            <button
                onclick={handleContinue}
                class="flex-1 py-2.5 px-5 bg-content-primary text-white rounded-lg text-base font-medium hover:opacity-90 transition-opacity"
            >
                繼續學習
            </button>
        {/if}
        <button
            onclick={onDone}
            class="{hasMoreCards
                ? ''
                : 'flex-1'} py-2.5 px-5 bg-surface-page text-content-secondary rounded-lg text-base font-medium border border-border hover:border-border-hover transition-colors"
        >
            完成
        </button>
    </div>
</div>
