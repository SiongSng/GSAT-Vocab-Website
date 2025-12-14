<script lang="ts">
    import { Rating } from "ts-fsrs";
    import {
        getSRSStore,
        flipCard,
        rateCard,
        showAnswer,
        playCurrentCardAudio,
    } from "$lib/stores/srs.svelte";
    import { getAppStore } from "$lib/stores/app.svelte";
    import { getEntry } from "$lib/stores/vocab-db";
    import type { VocabEntry } from "$lib/types/vocab";
    import Flashcard from "./Flashcard.svelte";
    import RatingButtons from "./RatingButtons.svelte";
    import ProgressBar from "./ProgressBar.svelte";

    const srs = getSRSStore();
    const app = getAppStore();

    let vocabEntry: VocabEntry | null = $state(null);
    let isLoadingDetail = $state(false);
    let autoSpeak = $state(true);

    const ratingMap = [Rating.Again, Rating.Hard, Rating.Good, Rating.Easy];

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
            vocabEntry = null;
        }
    });

    async function loadWordDetail(lemma: string) {
        isLoadingDetail = true;
        try {
            vocabEntry = await getEntry(lemma) ?? null;
        } catch {
            vocabEntry = null;
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
        if (event.key === " ") {
            event.preventDefault();
            if (!srs.isFlipped) {
                showAnswer();
            }
        } else if (srs.isFlipped && event.key >= "1" && event.key <= "4") {
            event.preventDefault();
            const index = parseInt(event.key) - 1;
            handleRate(ratingMap[index]);
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="max-w-lg mx-auto">
    {#if srs.currentCard}
        <Flashcard
            card={srs.currentCard}
            {vocabEntry}
            isFlipped={srs.isFlipped}
            isLoading={isLoadingDetail}
            onFlip={handleFlip}
        />

        {#if srs.isFlipped}
            <div class="mt-5">
                <RatingButtons onRate={handleRate} showHint={!app.isMobile} />
            </div>
        {/if}

        <ProgressBar />
    {/if}
</div>
