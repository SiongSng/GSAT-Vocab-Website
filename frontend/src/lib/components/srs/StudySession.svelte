<script lang="ts">
    import { Rating } from "ts-fsrs";
    import type { VocabDetail } from "$lib/types";
    import {
        getSRSStore,
        flipCard,
        rateCard,
        showAnswer,
        playCurrentCardAudio,
    } from "$lib/stores/srs.svelte";
    import { fetchWordDetail } from "$lib/api";
    import Flashcard from "./Flashcard.svelte";
    import RatingButtons from "./RatingButtons.svelte";
    import ProgressBar from "./ProgressBar.svelte";

    const srs = getSRSStore();

    let wordDetail: VocabDetail | null = $state(null);
    let isLoadingDetail = $state(false);
    let autoSpeak = $state(true);

    $effect(() => {
        try {
            const saved = localStorage.getItem("gsat_srs_auto_speak");
            autoSpeak = saved !== "false";
        } catch {
            autoSpeak = true;
        }
    });

    $effect(() => {
        const card = srs.currentCard;
        if (card) {
            loadWordDetail(card.lemma);
            if (autoSpeak) {
                setTimeout(() => playCurrentCardAudio(), 100);
            }
        } else {
            wordDetail = null;
        }
    });

    async function loadWordDetail(lemma: string) {
        isLoadingDetail = true;
        try {
            wordDetail = await fetchWordDetail(lemma);
        } catch {
            wordDetail = null;
        } finally {
            isLoadingDetail = false;
        }
    }

    function handleFlip() {
        if (!srs.isFlipped) {
            showAnswer();
        } else {
            flipCard();
        }
    }

    async function handleRate(rating: Rating) {
        await rateCard(rating);
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === " " && !srs.isFlipped) {
            event.preventDefault();
            showAnswer();
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="max-w-lg mx-auto">
    {#if srs.currentCard}
        <Flashcard
            card={srs.currentCard}
            {wordDetail}
            isFlipped={srs.isFlipped}
            isLoading={isLoadingDetail}
            onFlip={handleFlip}
        />

        {#if srs.isFlipped}
            <div class="mt-5">
                <RatingButtons onRate={handleRate} />
            </div>
        {/if}

        <ProgressBar />
    {/if}
</div>
