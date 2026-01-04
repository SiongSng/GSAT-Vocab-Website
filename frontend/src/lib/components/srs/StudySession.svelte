<script lang="ts">
    import { Rating } from "ts-fsrs";
    import {
        getSRSStore,
        flipCard,
        rateCard,
        showAnswer,
    } from "$lib/stores/srs.svelte";
    import { getAppStore } from "$lib/stores/app.svelte";
    import { getSRSEligibleEntry, getWordCached, getPhraseCached } from "$lib/stores/vocab-db";
    import { createAudioController } from "$lib/tts";
    import type { WordEntry, PhraseEntry } from "$lib/types/vocab";
    type VocabEntry = WordEntry | PhraseEntry;
    import Flashcard from "./Flashcard.svelte";
    import RatingButtons from "./RatingButtons.svelte";
    import ProgressBar from "./ProgressBar.svelte";
    import { STORAGE_KEYS } from "$lib/storage-keys";

    const srs = getSRSStore();
    const app = getAppStore();

    let vocabEntry: VocabEntry | null = $state(null);
    let isLoadingDetail = $state(false);
    let lastCardKey = $state<string | null>(null);

    function getCardKey(
        card: { lemma: string; sense_id: string } | null,
    ): string | null {
        return card ? `${card.lemma}:${card.sense_id}` : null;
    }

    const audioController = createAudioController(
        () => srs.currentCard?.lemma ?? "",
    );

    const ratingMap = [Rating.Again, Rating.Hard, Rating.Good, Rating.Easy];

    function getAutoSpeak(): boolean {
        try {
            const saved = localStorage.getItem(STORAGE_KEYS.STUDY_SETTINGS);
            if (saved) {
                const settings = JSON.parse(saved);
                return settings.autoSpeak ?? true;
            }
        } catch {
            // ignore
        }
        return true;
    }

    $effect(() => {
        const card = srs.currentCard;
        const cardKey = getCardKey(card);

        if (cardKey && cardKey !== lastCardKey) {
            lastCardKey = cardKey;

            const cached = getWordCached(card!.lemma) ?? getPhraseCached(card!.lemma);
            if (cached) {
                vocabEntry = cached;
                isLoadingDetail = false;
            } else {
                loadWordDetail(card!.lemma);
            }

            if (getAutoSpeak()) {
                audioController.stop();
                setTimeout(() => audioController.play(), 50);
            }
        } else if (!card) {
            lastCardKey = null;
            vocabEntry = null;
        }
    });

    async function loadWordDetail(lemma: string) {
        isLoadingDetail = true;
        try {
            vocabEntry = (await getSRSEligibleEntry(lemma)) ?? null;
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

    function handleRate(rating: Rating) {
        rateCard(rating);
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

        {#if srs.cramMode}
            <div class="mt-5 text-center text-sm text-content-tertiary">
                {srs.progress.current} / {srs.progress.total}
            </div>
        {:else}
            <ProgressBar />
        {/if}
    {/if}
</div>
