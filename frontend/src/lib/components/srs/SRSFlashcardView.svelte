<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import {
        getSRSStore,
        initSRS,
        startStudySession,
        prepareStudySession,
        endStudySession,
        type SessionOptions,
    } from "$lib/stores/srs.svelte";
    import StudyDashboard from "./StudyDashboard.svelte";
    import StudySession from "./StudySession.svelte";
    import SessionComplete from "./SessionComplete.svelte";

    type ViewState = "dashboard" | "studying" | "complete";

    const srs = getSRSStore();

    let viewState: ViewState = $state("dashboard");
    let isInitializing = $state(true);
    let isStarting = $state(false);
    let startError = $state<string | null>(null);
    let isDestroyed = false;

    onMount(async () => {
        await initSRS();
        isInitializing = false;
    });

    onDestroy(() => {
        isDestroyed = true;
        void endStudySession();
    });

    $effect(() => {
        if (srs.isStudying && srs.isComplete) {
            viewState = "complete";
        }
    });

    async function handleStart(options: SessionOptions) {
        if (isStarting) return;
        isStarting = true;
        startError = null;
        try {
            const preparedOptions = await prepareStudySession(options);
            if (isDestroyed) return;
            startStudySession(preparedOptions);
            if (srs.studyQueue.length === 0) {
                await endStudySession();
                startError = "目前沒有可練習的卡片。";
                return;
            }
            viewState = "studying";
        } catch (error) {
            if (isDestroyed) return;
            console.error("Failed to start study session", error);
            await endStudySession();
            startError = "無法載入練習卡片，請再試一次。若問題持續，請重新載入頁面。";
        } finally {
            isStarting = false;
        }
    }

    function handleBackToDashboard() {
        void endStudySession();
        viewState = "dashboard";
    }
</script>

<div class="h-full overflow-auto bg-surface-page">
    <div class="view-container">
        {#if isInitializing}
            <div class="flex items-center justify-center min-h-[400px]">
                <div class="text-[14px] text-content-tertiary">載入中...</div>
            </div>
        {:else if viewState === "dashboard"}
            {#if startError}
                <p role="alert" class="mb-4 text-sm text-srs-again">{startError}</p>
            {/if}
            <StudyDashboard onStart={handleStart} {isStarting} />
        {:else if viewState === "studying" && !srs.isComplete}
            <StudySession />
        {:else if viewState === "complete" || srs.isComplete}
            <SessionComplete onBackToDashboard={handleBackToDashboard} />
        {/if}
    </div>
</div>

<style>
    .view-container {
        max-width: 56rem;
        margin: 0 auto;
        padding: 1.5rem 1rem;
        padding-bottom: calc(1.5rem + var(--bottom-nav-height));
    }

    @media (min-width: 640px) {
        .view-container {
            padding: 3rem 1.5rem;
        }
    }
</style>
