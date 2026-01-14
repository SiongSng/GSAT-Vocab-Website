<script lang="ts">
    import { State } from "ts-fsrs";
    import { getSRSStore } from "$lib/stores/srs.svelte";

    const srs = getSRSStore();

    const progressPct = $derived(
        srs.progress.total > 0
            ? (srs.progress.current / srs.progress.total) * 100
            : 0,
    );

    const currentState = $derived(srs.currentCard?.state ?? null);

    const stateConfig = $derived.by(() => {
        switch (currentState) {
            case State.New:
                return { label: "新卡片" };
            case State.Learning:
                return { label: "學習中" };
            case State.Review:
                return { label: "複習" };
            case State.Relearning:
                return { label: "重學" };
            default:
                return null;
        }
    });
</script>

<div class="progress-container">
    <div class="progress-bar">
        <div
            class="progress-fill"
            style="width: {progressPct}%"
        ></div>
    </div>
    <div class="progress-info">
        {#if stateConfig}
            <span class="state-label">{stateConfig.label}</span>
            <span class="separator">·</span>
        {/if}
        <span class="progress-count">
            {srs.progress.current} / {srs.progress.total}
        </span>
    </div>
</div>

<style>
    .progress-container {
        margin-top: 1.25rem;
    }

    .progress-bar {
        height: 3px;
        background: var(--color-surface-page);
        border-radius: 2px;
        overflow: hidden;
        margin-bottom: 0.75rem;
    }

    .progress-fill {
        height: 100%;
        background: var(--color-accent);
        opacity: 0.5;
        border-radius: 2px;
        transition: width 0.3s ease;
    }

    .progress-info {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        font-size: 0.8125rem;
    }

    .state-label {
        color: var(--color-content-secondary);
    }

    .separator {
        color: var(--color-content-tertiary);
        opacity: 0.5;
    }

    .progress-count {
        color: var(--color-content-tertiary);
    }
</style>
