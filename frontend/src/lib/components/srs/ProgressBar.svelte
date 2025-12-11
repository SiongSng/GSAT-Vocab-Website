<script lang="ts">
    import { State } from "ts-fsrs";
    import { getSRSStore } from "$lib/stores/srs.svelte";

    const srs = getSRSStore();

    const progressPercent = $derived(
        srs.studyQueue && srs.studyQueue.length > 0
            ? (srs.currentCardIndex / srs.studyQueue.length) * 100
            : 0,
    );

    const newRemaining = $derived(
        srs.studyQueue
            ? srs.studyQueue.filter(
                  (c, i) => i >= srs.currentCardIndex && c.state === State.New,
              ).length
            : 0,
    );

    const learningRemaining = $derived(
        srs.studyQueue
            ? srs.studyQueue.filter(
                  (c, i) =>
                      i >= srs.currentCardIndex &&
                      (c.state === State.Learning ||
                          c.state === State.Relearning),
              ).length
            : 0,
    );

    const reviewRemaining = $derived(
        srs.studyQueue
            ? srs.studyQueue.filter(
                  (c, i) =>
                      i >= srs.currentCardIndex && c.state === State.Review,
              ).length
            : 0,
    );
</script>

<div class="mt-5">
    <div class="h-1 bg-surface-page rounded-full overflow-hidden mb-3">
        <div
            class="h-full bg-accent/60 rounded-full transition-all duration-300"
            style="width: {progressPercent}%"
        ></div>
    </div>
    <div
        class="flex items-center justify-center gap-4 text-sm text-content-tertiary"
    >
        <span class="font-medium text-content-secondary">
            {srs.progress.current} / {srs.progress.total}
        </span>
        <span class="text-border-hover">•</span>
        {#if newRemaining > 0}
            <span class="text-srs-easy">{newRemaining} 新</span>
        {/if}
        {#if learningRemaining > 0}
            <span class="text-srs-hard">{learningRemaining} 學習中</span>
        {/if}
        {#if reviewRemaining > 0}
            <span class="text-srs-again">{reviewRemaining} 複習</span>
        {/if}
    </div>
</div>
