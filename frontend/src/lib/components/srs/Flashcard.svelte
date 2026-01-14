<script lang="ts">
    import { cubicOut } from "svelte/easing";
    import type { SRSCard } from "$lib/types/srs";
    import { getPrioritizedSenses } from "$lib/types/srs";
    import type { VocabEntry } from "$lib/types/vocab";
    import { isWordEntry, isPhraseEntry } from "$lib/types/vocab";
    import HighlightedText from "$lib/components/ui/HighlightedText.svelte";
    import WordDetailModal from "./WordDetailModal.svelte";
    import { findSenseForCard, getSenseIndex } from "$lib/stores/srs.svelte";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";

    interface Props {
        card: SRSCard;
        vocabEntry: VocabEntry | null;
        isFlipped: boolean;
        isLoading: boolean;
        onFlip: () => void;
    }

    let { card, vocabEntry, isFlipped, isLoading, onFlip }: Props = $props();

    let isModalOpen = $state(false);

    const cardKey = $derived(`${card.lemma}:${card.sense_id}`);

    const isPhrase = $derived(vocabEntry ? isPhraseEntry(vocabEntry) : false);

    const currentSense = $derived.by(() => {
        return findSenseForCard(card, vocabEntry);
    });

    const senseIndex = $derived.by(() => {
        return getSenseIndex(vocabEntry, card.sense_id);
    });

    const totalSenses = $derived.by(() => {
        if (!vocabEntry) return 0;
        return getPrioritizedSenses(vocabEntry).length;
    });

    const memoryTip = $derived.by(() => {
        if (!vocabEntry || !isWordEntry(vocabEntry)) return null;
        return vocabEntry.root_info?.memory_strategy ?? null;
    });

    const currentExample = $derived.by(() => {
        if (!currentSense) return null;
        const generated = currentSense.generated_example?.trim();
        if (generated) {
            return generated;
        }
        return null;
    });

    function handleOpenModal(e: MouseEvent) {
        e.stopPropagation();
        isModalOpen = true;
    }

    function handleCloseModal() {
        isModalOpen = false;
    }

    function handleCardClick() {
        onFlip();
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter") {
            onFlip();
        }
    }

    function fadeScale(_node: Element, { duration = 200, out = false }) {
        return {
            duration,
            easing: cubicOut,
            css: (t: number) => {
                const scale = out ? 1 - 0.02 * (1 - t) : 0.98 + 0.02 * t;
                return `
                    opacity: ${t};
                    transform: scale(${scale});
                `;
            },
        };
    }
</script>

<div class="flashcard-wrapper">
    {#key cardKey}
        <div
            class="flashcard-container"
            in:fadeScale={{ duration: 200 }}
            out:fadeScale={{ duration: 150, out: true }}
            onclick={handleCardClick}
            onkeydown={handleKeydown}
            role="button"
            tabindex="0"
        >
            <div class="flashcard-inner" class:flipped={isFlipped}>
                <!-- Front -->
                <div class="flashcard-face flashcard-front">
                    <div class="card-content">
                        <h2 class="word-main">{card.lemma}</h2>

                        {#if currentExample}
                            <p class="example-context">{currentExample}</p>
                        {/if}
                    </div>

                    <div class="card-actions">
                        <AudioButton text={card.lemma} size="md" />
                    </div>
                </div>

                <!-- Back -->
                <div class="flashcard-face flashcard-back">
                    {#if isLoading}
                        <div class="loading-state">載入中...</div>
                    {:else if currentSense}
                        <div class="card-content">
                            <div class="word-meta">
                                <h2 class="word-main">{card.lemma}</h2>
                                <span class="pos-tag">{currentSense.pos}</span>
                                {#if totalSenses > 1}
                                    <span class="sense-count">{senseIndex + 1}/{totalSenses}</span>
                                {/if}
                            </div>

                            <p class="definition">{currentSense.zh_def}</p>

                            {#if memoryTip}
                                <p class="memory-tip">{memoryTip}</p>
                            {/if}

                            {#if currentExample}
                                <!-- svelte-ignore a11y_click_events_have_key_events -->
                                <p
                                    class="example-sentence"
                                    onclick={(e) => e.stopPropagation()}
                                    role="presentation"
                                >
                                    <HighlightedText
                                        text={currentExample}
                                        highlightLemma={card.lemma}
                                        {isPhrase}
                                    />
                                </p>
                            {/if}
                        </div>

                        <div class="card-actions">
                            <AudioButton text={card.lemma} size="md" />
                            {#if currentExample}
                                <AudioButton text={currentExample} size="md" icon="sentence" />
                            {/if}
                            <button
                                type="button"
                                class="detail-btn"
                                onclick={handleOpenModal}
                                title="查看完整詞條"
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke-width="1.5"
                                    stroke="currentColor"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
                                    />
                                </svg>
                            </button>
                        </div>
                    {:else}
                        <div class="loading-state">暫無釋義</div>
                    {/if}
                </div>
            </div>
        </div>
    {/key}
</div>

{#if vocabEntry}
    <WordDetailModal
        entry={vocabEntry}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
    />
{/if}

<style>
    .flashcard-wrapper {
        display: grid;
    }

    .flashcard-container {
        grid-area: 1 / 1;
        cursor: pointer;
    }

    .flashcard-inner {
        display: grid;
    }

    .flashcard-face {
        grid-area: 1 / 1;
        min-height: 280px;
        padding: 1.5rem 1.25rem;
        display: flex;
        flex-direction: column;
        background: var(--color-surface-primary);
        border-radius: 16px;
        box-shadow:
            0 1px 2px rgba(0, 0, 0, 0.03),
            0 4px 12px rgba(0, 0, 0, 0.03);
        transition:
            opacity 0.2s ease-out,
            transform 0.2s ease-out;
    }

    @media (min-width: 640px) {
        .flashcard-face {
            min-height: 320px;
            padding: 2.5rem 2rem;
            border-radius: 20px;
            box-shadow:
                0 1px 3px rgba(0, 0, 0, 0.04),
                0 8px 24px rgba(0, 0, 0, 0.05);
        }
    }

    .flashcard-front {
        opacity: 1;
        transform: scale(1);
    }

    .flashcard-back {
        opacity: 0;
        transform: scale(0.98);
        pointer-events: none;
    }

    .flashcard-inner.flipped .flashcard-front {
        opacity: 0;
        transform: scale(0.98);
        pointer-events: none;
    }

    .flashcard-inner.flipped .flashcard-back {
        opacity: 1;
        transform: scale(1);
        pointer-events: auto;
    }

    /* Content area */
    .card-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 1rem;
    }

    @media (min-width: 640px) {
        .card-content {
            gap: 1.25rem;
        }
    }

    .card-actions {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.375rem;
        margin-top: 1rem;
        padding-top: 0.75rem;
    }

    @media (min-width: 640px) {
        .card-actions {
            gap: 0.5rem;
            margin-top: 1.5rem;
            padding-top: 1rem;
        }
    }

    /* Word styling */
    .word-main {
        font-family: var(--font-sans);
        font-size: 1.75rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        color: var(--color-content-primary);
        line-height: 1.2;
    }

    @media (min-width: 640px) {
        .word-main {
            font-size: 2.25rem;
        }
    }

    .word-meta {
        display: flex;
        align-items: baseline;
        justify-content: center;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .pos-tag {
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
        text-transform: lowercase;
    }

    @media (min-width: 640px) {
        .pos-tag {
            font-size: 0.875rem;
        }
    }

    .sense-count {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
        opacity: 0.7;
    }

    /* Front: example as context hint */
    .example-context {
        font-family: var(--font-sans);
        font-size: 0.875rem;
        line-height: 1.7;
        color: var(--color-content-tertiary);
        max-width: 100%;
        padding: 0 0.25rem;
    }

    @media (min-width: 640px) {
        .example-context {
            font-size: 0.9375rem;
            max-width: 26rem;
            padding: 0;
        }
    }

    /* Back: definition */
    .definition {
        font-size: 1.0625rem;
        line-height: 1.5;
        color: var(--color-content-primary);
    }

    @media (min-width: 640px) {
        .definition {
            font-size: 1.125rem;
        }
    }

    .memory-tip {
        font-size: 0.8125rem;
        line-height: 1.5;
        color: var(--color-content-secondary);
        padding: 0.375rem 0.625rem;
        background: var(--color-surface-secondary);
        border-radius: 6px;
    }

    @media (min-width: 640px) {
        .memory-tip {
            font-size: 0.875rem;
            padding: 0.5rem 0.75rem;
            border-radius: 8px;
        }
    }

    /* Back: example with highlight */
    .example-sentence {
        font-family: var(--font-sans);
        font-size: 0.875rem;
        line-height: 1.7;
        color: var(--color-content-secondary);
        max-width: 100%;
        padding: 0 0.25rem;
    }

    @media (min-width: 640px) {
        .example-sentence {
            font-size: 0.9375rem;
            max-width: 26rem;
            padding: 0;
        }
    }

    .detail-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 1.75rem;
        height: 1.75rem;
        border-radius: 6px;
        color: var(--color-content-tertiary);
        transition: all 0.15s ease;
    }

    @media (min-width: 640px) {
        .detail-btn {
            width: 2rem;
            height: 2rem;
            border-radius: 8px;
        }
    }

    .detail-btn svg {
        width: 0.875rem;
        height: 0.875rem;
    }

    @media (min-width: 640px) {
        .detail-btn svg {
            width: 1rem;
            height: 1rem;
        }
    }

    .detail-btn:hover {
        background: var(--color-surface-hover);
        color: var(--color-accent);
    }

    .loading-state {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--color-content-tertiary);
    }
</style>
