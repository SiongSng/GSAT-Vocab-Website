<script lang="ts">
    import { onMount } from "svelte";
    import {
        getSRSStore,
        initSRS,
        addWordsToSRS,
        startStudySession,
        endStudySession,
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

    function handleStart(words: string[]) {
        startStudySession({ customWords: words });
        viewState = "studying";
    }

    function handleContinueStudy(words: string[]) {
        startStudySession({ customWords: words });
        viewState = "studying";
    }

    function handleDone() {
        endStudySession();
        viewState = "dashboard";
    }
</script>

<div class="h-full overflow-auto bg-surface-page">
    <div class="max-w-4xl mx-auto px-4 py-8 sm:px-6 sm:py-12">
        {#if isInitializing}
            <div class="flex items-center justify-center min-h-[400px]">
                <div class="text-[14px] text-content-tertiary">載入中...</div>
            </div>
        {:else if viewState === "dashboard"}
            <StudyDashboard onStart={handleStart} />
        {:else if viewState === "studying" && !srs.isComplete}
            <StudySession />
        {:else if viewState === "complete" || srs.isComplete}
            <SessionComplete
                onContinue={handleContinueStudy}
                onDone={handleDone}
            />
        {/if}
    </div>
</div>
