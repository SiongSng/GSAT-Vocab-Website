<script lang="ts">
    import { State } from "ts-fsrs";
    import { getSRSStore } from "$lib/stores/srs.svelte";

    const srs = getSRSStore();

    const progressPct = $derived(
        srs.progress.total > 0
            ? (srs.progress.current / srs.progress.total) * 100
            : 0,
    );

    const newCount = $derived(
        srs.studyQueue?.filter(
            (c, i) => i >= srs.currentCardIndex && c.state === State.New,
        ).length || 0,
    );

    const learningCount = $derived(
        srs.studyQueue?.filter(
            (c, i) =>
                i >= srs.currentCardIndex &&
                (c.state === State.Learning || c.state === State.Relearning),
        ).length || 0,
    );

    const reviewCount = $derived(
        srs.studyQueue?.filter(
            (c, i) => i >= srs.currentCardIndex && c.state === State.Review,
        ).length || 0,
    );
</script>

<div class="mt-5">
    <div class="h-1 bg-surface-page rounded-full overflow-hidden mb-3">
        <div
            class="h-full bg-accent/60 rounded-full transition-all duration-300"
            style="width: {progressPct}%"
        ></div>
    </div>
    <div class="flex items-center justify-center gap-4 text-sm text-content-tertiary">
        <span class="font-medium text-content-secondary">
            {srs.progress.current} / {srs.progress.total}
        </span>
        <span class="text-border-hover">•</span>
        {#if newCount > 0}
            <span class="text-srs-easy">{newCount} 待學</span>
        {/if}
        {#if learningCount > 0}
            <span class="text-srs-hard">{learningCount} 學習中</span>
        {/if}
        {#if reviewCount > 0}
            <span class="text-srs-again">{reviewCount} 待複習</span>
        {/if}
    </div>
</div>
