<script lang="ts">
    import { onMount } from "svelte";
    import {
        getSRSStore,
        initSRS,
        addWordsToSRS,
        startStudySession,
        endStudySession,
        type SessionOptions,
    } from "$lib/stores/srs.svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import StudyDashboard from "./StudyDashboard.svelte";
    import StudySession from "./StudySession.svelte";
    import SessionComplete from "./SessionComplete.svelte";

    type ViewState = "dashboard" | "studying" | "complete";

    const srs = getSRSStore();
    const vocab = getVocabStore();

    let viewState: ViewState = $state("dashboard");
    let isInitializing = $state(true);

    onMount(async () => {
        await initSRS();

        const words = vocab.index;
        if (words && words.length > 0) {
            const lemmas = words.map((w) => w.lemma);
            addWordsToSRS(lemmas);
        }

        isInitializing = false;
    });

    $effect(() => {
        if (srs.isStudying && srs.isComplete) {
            viewState = "complete";
        }
    });

    function handleStart(options: SessionOptions) {
        startStudySession(options);
        if (srs.studyQueue.length === 0) {
            endStudySession();
            return;
        }
        viewState = "studying";
    }

    function handleBackToDashboard() {
        endStudySession();
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
            <StudyDashboard onStart={handleStart} />
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
        padding: 1.5rem 1rem calc(env(safe-area-inset-bottom, 0px) + 5rem);
    }

    @media (min-width: 640px) {
        .view-container {
            padding: 3rem 1.5rem;
        }
    }
</style>
