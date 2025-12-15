<script lang="ts">
    import type { SRSCard } from "$lib/types/srs";
    import type { VocabEntry } from "$lib/types/vocab";
    import StateBadge from "./StateBadge.svelte";
    import { playCurrentCardAudio, findSenseForCard, getSenseIndex } from "$lib/stores/srs.svelte";
    import ClickableWord from "$lib/components/ui/ClickableWord.svelte";

    interface Props {
        card: SRSCard;
        vocabEntry: VocabEntry | null;
        isFlipped: boolean;
        isLoading: boolean;
        onFlip: () => void;
    }

    let { card, vocabEntry, isFlipped, isLoading, onFlip }: Props = $props();

    const currentSense = $derived.by(() => {
        return findSenseForCard(card, vocabEntry);
    });

    const senseIndex = $derived.by(() => {
        return getSenseIndex(vocabEntry, card.sense_id);
    });

    const totalSenses = $derived(vocabEntry?.senses?.length ?? 0);

    const currentExample = $derived.by(() => {
        if (!currentSense) return null;
        const examples = currentSense.examples ?? [];
        if (examples.length > 0) {
            const randomIdx = Math.floor(Math.random() * examples.length);
            return {
                text: examples[randomIdx].text,
                source: examples[randomIdx].source,
            };
        }
        if (currentSense.generated_example?.trim()) {
            return {
                text: currentSense.generated_example.trim(),
                source: null,
            };
        }
        return null;
    });

    function formatSource(source: { year: number; exam_type: string; section_type: string; question_number?: number } | null): string {
        if (!source) return "AI 生成例句";
        const examTypeMap: Record<string, string> = {
            gsat: "學測",
            gsat_makeup: "學測補考",
            ast: "指考",
            ast_makeup: "指考補考",
            gsat_trial: "學測試辦",
            gsat_ref: "參考試卷",
        };
        const sectionMap: Record<string, string> = {
            vocabulary: "詞彙題",
            cloze: "克漏字",
            discourse: "文意選填",
            structure: "句型",
            reading: "閱讀測驗",
            translation: "翻譯",
            mixed: "綜合",
        };
        const examType = examTypeMap[source.exam_type] || source.exam_type;
        const section = sectionMap[source.section_type] || source.section_type;
        return `${source.year} ${examType}・${section}`;
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
                {#if currentSense}
                    <p class="text-base text-content-tertiary lowercase">
                        {currentSense.pos}
                    </p>
                {/if}
            </div>

            <div class="text-center">
                <p class="text-sm text-content-tertiary/60">點擊翻牌</p>
            </div>
        </div>

        <!-- Back -->
        <div
            class="flashcard-face flashcard-back backface-hidden rotate-y-180 bg-surface-primary rounded-lg border border-border shadow-card p-8 flex flex-col overflow-hidden"
        >
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                    <StateBadge state={card.state} />
                    {#if totalSenses > 1}
                        <span class="text-xs text-content-tertiary bg-surface-page px-2 py-0.5 rounded">
                            涵義 {senseIndex + 1}/{totalSenses}
                        </span>
                    {/if}
                </div>
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

            <div class="text-center mb-4">
                <h2
                    class="text-2xl font-semibold tracking-tight text-content-primary"
                >
                    {card.lemma}
                </h2>
                {#if currentSense}
                    <span
                        class="inline-block px-2 py-0.5 text-xs font-medium rounded bg-surface-page text-content-tertiary mt-1 lowercase"
                    >
                        {currentSense.pos}
                    </span>
                {/if}
            </div>

            <div class="flex-1 overflow-y-auto custom-scrollbar -mx-2 px-2">
                {#if isLoading}
                    <div class="flex items-center justify-center py-8">
                        <div class="text-base text-content-tertiary">
                            載入中...
                        </div>
                    </div>
                {:else if currentSense}
                    <div class="space-y-4">
                        <div class="border-b border-border/60 pb-4">
                            <p class="text-base text-content-primary leading-relaxed">
                                {currentSense.zh_def}
                            </p>
                            {#if currentSense.en_def}
                                <p class="text-sm text-content-tertiary mt-1 leading-relaxed">
                                    {currentSense.en_def}
                                </p>
                            {/if}
                        </div>

                        {#if currentExample}
                            <div class="space-y-2">
                                <div class="flex items-center gap-2">
                                    <span class="text-xs font-medium text-content-tertiary uppercase tracking-wider">
                                        {currentExample.source ? "真實考題" : "學習例句"}
                                    </span>
                                </div>
                                <p class="text-sm text-content-secondary leading-relaxed">
                                    <ClickableWord text={currentExample.text} highlightWord={card.lemma} />
                                </p>
                                {#if currentExample.source}
                                    <div class="inline-flex items-center gap-1.5 px-2 py-1 bg-surface-page rounded text-xs text-content-tertiary">
                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
                                        </svg>
                                        {formatSource(currentExample.source)}
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    </div>
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
        min-height: 320px;
        max-height: 480px;
    }

    .flashcard-inner:not(.rotate-y-180) .flashcard-back {
        pointer-events: none;
    }

    .flashcard-inner.rotate-y-180 .flashcard-front {
        pointer-events: none;
    }
</style>
