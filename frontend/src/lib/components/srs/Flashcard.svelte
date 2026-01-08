<script lang="ts">
    import { cubicOut } from "svelte/easing";
    import type { SRSCard } from "$lib/types/srs";
    import { getPrioritizedSenses } from "$lib/types/srs";
    import type { VocabEntry } from "$lib/types/vocab";
    import { isWordEntry, isPhraseEntry } from "$lib/types/vocab";
    import HighlightedText from "$lib/components/ui/HighlightedText.svelte";
    import StateBadge from "./StateBadge.svelte";
    import WordDetailModal from "./WordDetailModal.svelte";
    import { findSenseForCard, getSenseIndex } from "$lib/stores/srs.svelte";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";
    import { formatExamSource } from "$lib/constants/exam-types";

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

    let exampleSeed = $state(Math.random());

    $effect(() => {
        void cardKey;
        exampleSeed = Math.random();
    });

    const currentExample = $derived.by(() => {
        if (!currentSense) return null;
        const examples = currentSense.examples ?? [];
        if (examples.length > 0) {
            const idx = Math.floor(exampleSeed * examples.length);
            return {
                text: examples[idx].text,
                source: examples[idx].source,
            };
        }
        const generated = currentSense.generated_example?.trim();
        if (generated) {
            return {
                text: generated,
                source: null,
            };
        }
        return null;
    });

    function formatSource(
        source: {
            year: number;
            exam_type: string;
            section_type: string;
            question_number?: number;
        } | null,
    ): string {
        if (!source) return "AI 生成例句";
        return formatExamSource(source);
    }

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
                    <div class="flex items-center justify-between">
                        <StateBadge state={card.state} />
                        <AudioButton text={card.lemma} size="lg" />
                    </div>

                    <div
                        class="flex-1 flex flex-col items-center justify-center text-center py-12"
                    >
                        <h2
                            class="text-3xl lg:text-4xl font-semibold tracking-tight text-content-primary mb-2"
                        >
                            {card.lemma}
                        </h2>
                        {#if currentSense}
                            <p
                                class="text-base text-content-tertiary lowercase"
                            >
                                {currentSense.pos}
                            </p>
                        {/if}
                    </div>

                    <div class="text-center">
                        <p class="text-sm text-content-tertiary/60">點擊翻牌</p>
                    </div>
                </div>

                <!-- Back -->
                <div class="flashcard-face flashcard-back">
                    <div class="back-header">
                        <StateBadge state={card.state} />
                        <div class="back-actions">
                            <AudioButton text={card.lemma} size="md" />
                            <button
                                type="button"
                                class="detail-btn"
                                onclick={handleOpenModal}
                                title="查看完整詞條"
                            >
                                <svg
                                    class="w-4 h-4"
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
                    </div>

                    <div class="back-content">
                        {#if isLoading}
                            <div class="loading-state">載入中...</div>
                        {:else if currentSense}
                            <div class="word-header">
                                <h2 class="word-title">{card.lemma}</h2>
                                <span class="word-pos">{currentSense.pos}</span>
                                {#if totalSenses > 1}
                                    <span class="sense-indicator">
                                        {senseIndex + 1}/{totalSenses}
                                    </span>
                                {/if}
                            </div>

                            <p class="definition-zh">{currentSense.zh_def}</p>
                            {#if currentSense.en_def}
                                <p class="definition-en">
                                    {currentSense.en_def}
                                </p>
                            {/if}

                            {#if memoryTip}
                                <p class="memory-tip">
                                    <svg
                                        class="tip-icon"
                                        xmlns="http://www.w3.org/2000/svg"
                                        viewBox="0 0 24 24"
                                        fill="currentColor"
                                    >
                                        <path
                                            d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z"
                                        />
                                    </svg>
                                    {memoryTip}
                                </p>
                            {/if}

                            {#if currentExample}
                                <!-- svelte-ignore a11y_click_events_have_key_events -->
                                <div
                                    class="example-section"
                                    onclick={(e) => e.stopPropagation()}
                                    role="presentation"
                                >
                                    <p class="example-text">
                                        <HighlightedText
                                            text={currentExample.text}
                                            highlightLemma={card.lemma}
                                            {isPhrase}
                                        />
                                    </p>
                                    <div class="example-footer">
                                        <span class="example-source">
                                            {formatSource(currentExample.source)}
                                        </span>
                                        <AudioButton
                                            text={currentExample.text}
                                            size="sm"
                                        />
                                    </div>
                                </div>
                            {/if}
                        {:else}
                            <div class="loading-state">暫無釋義</div>
                        {/if}
                    </div>
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
        max-height: calc(100vh - 16rem);
        padding: 1.25rem;
        display: flex;
        flex-direction: column;
        background: var(--color-surface-primary);
        border-radius: 16px;
        box-shadow:
            0 1px 3px rgba(0, 0, 0, 0.04),
            0 4px 12px rgba(0, 0, 0, 0.03);
        transition:
            opacity 0.2s ease-out,
            transform 0.2s ease-out;
        overflow-y: auto;
    }

    @media (min-width: 640px) {
        .flashcard-face {
            min-height: 360px;
            max-height: none;
            padding: 1.5rem;
            overflow-y: visible;
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

    /* Back face styles */
    .back-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .back-actions {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .detail-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 2rem;
        height: 2rem;
        border-radius: 8px;
        color: var(--color-content-tertiary);
        transition: all 0.15s ease;
    }

    .detail-btn:hover {
        background: var(--color-surface-hover);
        color: var(--color-accent);
    }

    .back-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.875rem;
    }

    .loading-state {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--color-content-tertiary);
    }

    .word-header {
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .word-title {
        font-size: 1.375rem;
        font-weight: 700;
        color: var(--color-content-primary);
        letter-spacing: -0.01em;
    }

    .word-pos {
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
        text-transform: lowercase;
    }

    .sense-indicator {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
        opacity: 0.7;
    }

    .definition-zh {
        font-size: 1.0625rem;
        line-height: 1.6;
        color: var(--color-content-primary);
    }

    .definition-en {
        font-size: 0.875rem;
        line-height: 1.5;
        color: var(--color-content-tertiary);
        margin-top: -0.25rem;
    }

    .memory-tip {
        display: flex;
        align-items: flex-start;
        gap: 0.375rem;
        font-size: 0.875rem;
        line-height: 1.5;
        color: var(--color-content-secondary);
    }

    .tip-icon {
        width: 1rem;
        height: 1rem;
        flex-shrink: 0;
        margin-top: 0.125rem;
        color: #f59e0b;
    }

    .example-section {
        margin-top: 0.25rem;
        padding-top: 0.875rem;
        border-top: 1px solid var(--color-border);
    }

    .example-text {
        font-size: 0.9375rem;
        line-height: 1.7;
        color: var(--color-content-secondary);
    }

    .example-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 0.5rem;
    }

    .example-source {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
        opacity: 0.8;
    }
</style>
