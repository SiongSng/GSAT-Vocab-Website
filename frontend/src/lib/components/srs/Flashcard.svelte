<script lang="ts">
    import type { SRSCard } from "$lib/types/srs";
    import type { VocabDetail } from "$lib/types";
    import StateBadge from "./StateBadge.svelte";
    import { playCurrentCardAudio } from "$lib/stores/srs.svelte";

    interface Props {
        card: SRSCard;
        wordDetail: VocabDetail | null;
        isFlipped: boolean;
        isLoading: boolean;
        onFlip: () => void;
    }

    let { card, wordDetail, isFlipped, isLoading, onFlip }: Props = $props();

    const primaryPos = $derived.by(() => {
        if (wordDetail?.meanings?.[0]?.pos) {
            return wordDetail.meanings[0].pos;
        }
        if (wordDetail?.pos_distribution) {
            const keys = Object.keys(wordDetail.pos_distribution);
            if (keys.length > 0) {
                return keys[0];
            }
        }
        return "word";
    });

    function highlightWord(text: string, lemma: string): string {
        const variants = getInflectionVariants(lemma);
        const pattern = variants
            .map((v) => v.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
            .join("|");
        const regex = new RegExp(`\\b(${pattern})\\b`, "gi");
        return text.replace(regex, '<mark class="highlight">$1</mark>');
    }

    function getInflectionVariants(lemma: string): string[] {
        const lower = lemma.toLowerCase();
        const variants = [lemma, lower];

        variants.push(lower + "s");
        variants.push(lower + "es");
        variants.push(lower + "ed");
        variants.push(lower + "ing");
        variants.push(lower + "er");
        variants.push(lower + "est");
        variants.push(lower + "ly");

        if (lower.endsWith("e")) {
            variants.push(lower.slice(0, -1) + "ing");
            variants.push(lower + "d");
        }
        if (lower.endsWith("y")) {
            variants.push(lower.slice(0, -1) + "ies");
            variants.push(lower.slice(0, -1) + "ied");
        }

        return variants;
    }
</script>

<div
    class="flashcard-container perspective-1000 cursor-pointer"
    onclick={onFlip}
    onkeydown={(e) => e.key === "Enter" && onFlip()}
    role="button"
    tabindex="0"
>
    <div
        class="flashcard-inner transform-style-preserve-3d transition-transform duration-500 {isFlipped
            ? 'rotate-y-180'
            : ''}"
    >
        <!-- Front -->
        <div
            class="flashcard-face flashcard-front backface-hidden bg-surface-primary rounded-lg border border-border shadow-card p-8 flex flex-col"
        >
            <div class="flex items-center justify-between">
                <StateBadge state={card.state} />
                <button
                    onclick={(e) => {
                        e.stopPropagation();
                        playCurrentCardAudio();
                    }}
                    class="p-2 rounded-md hover:bg-surface-hover transition-colors"
                    aria-label="播放發音"
                >
                    <svg
                        class="w-6 h-6 text-content-tertiary"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        stroke-width="1.5"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
                        />
                    </svg>
                </button>
            </div>

            <div
                class="flex-1 flex flex-col items-center justify-center text-center py-12"
            >
                <h2
                    class="text-3xl lg:text-4xl font-semibold tracking-tight text-content-primary mb-2"
                >
                    {card.lemma}
                </h2>
                <p class="text-base text-content-tertiary lowercase">
                    {primaryPos}
                </p>
            </div>

            <div class="text-center">
                <p class="text-sm text-content-tertiary/60">點擊翻牌</p>
            </div>
        </div>

        <!-- Back -->
        <div
            class="flashcard-face flashcard-back backface-hidden rotate-y-180 bg-surface-primary rounded-lg border border-border shadow-card p-8 flex flex-col"
        >
            <div class="flex items-center justify-between mb-5">
                <StateBadge state={card.state} />
                <button
                    onclick={(e) => {
                        e.stopPropagation();
                        playCurrentCardAudio();
                    }}
                    class="p-2 rounded-md hover:bg-surface-hover transition-colors"
                    aria-label="播放發音"
                >
                    <svg
                        class="w-6 h-6 text-content-tertiary"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        stroke-width="1.5"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
                        />
                    </svg>
                </button>
            </div>

            <div class="text-center mb-5">
                <h2
                    class="text-2xl font-semibold tracking-tight text-content-primary"
                >
                    {card.lemma}
                </h2>
            </div>

            <div class="space-y-4 px-1">
                {#if isLoading}
                    <div class="flex items-center justify-center py-8">
                        <div class="text-base text-content-tertiary">
                            載入中...
                        </div>
                    </div>
                {:else if wordDetail?.meanings && wordDetail.meanings.length > 0}
                    {#each wordDetail.meanings.slice(0, 3) as meaning, i}
                        <div
                            class={i <
                            Math.min(wordDetail.meanings.length, 3) - 1
                                ? "pb-4 border-b border-border/60"
                                : ""}
                        >
                            <span
                                class="inline-block px-2 py-0.5 text-xs font-medium rounded bg-surface-page text-content-tertiary mb-2 lowercase"
                            >
                                {meaning.pos}
                            </span>
                            <p
                                class="text-base text-content-primary leading-relaxed"
                            >
                                {meaning.zh_def}
                            </p>
                            {#if meaning.en_def}
                                <p
                                    class="text-sm text-content-tertiary mt-1 leading-relaxed"
                                >
                                    {meaning.en_def}
                                </p>
                            {/if}
                        </div>
                    {/each}

                    {#if wordDetail.sentences?.preview && wordDetail.sentences.preview.length > 0}
                        <div class="pt-3 mt-3 border-t border-border/50">
                            {#each wordDetail.sentences.preview.slice(0, 1) as sentence}
                                <p class="text-sm text-content-secondary leading-relaxed">
                                    {@html highlightWord(sentence.text, card.lemma)}
                                </p>
                            {/each}
                        </div>
                    {/if}
                {:else}
                    <div class="flex items-center justify-center py-8">
                        <div class="text-base text-content-tertiary">
                            暫無釋義
                        </div>
                    </div>
                {/if}
            </div>
        </div>
    </div>
</div>

<style>
    .perspective-1000 {
        perspective: 1000px;
    }

    .transform-style-preserve-3d {
        transform-style: preserve-3d;
    }

    .backface-hidden {
        backface-visibility: hidden;
    }

    .rotate-y-180 {
        transform: rotateY(180deg);
    }

    .flashcard-inner {
        display: grid;
    }

    .flashcard-face {
        grid-area: 1 / 1;
        min-height: 280px;
    }

    .flashcard-inner:not(.rotate-y-180) .flashcard-back {
        pointer-events: none;
    }

    .flashcard-inner.rotate-y-180 .flashcard-front {
        pointer-events: none;
    }

    :global(.highlight) {
        background: linear-gradient(
            to top,
            var(--color-highlight) 0%,
            var(--color-highlight) 60%,
            transparent 60%
        );
        padding: 0 2px;
        margin: 0 -2px;
        border-radius: 2px;
        font-weight: 500;
        color: var(--color-content-primary);
    }
</style>
