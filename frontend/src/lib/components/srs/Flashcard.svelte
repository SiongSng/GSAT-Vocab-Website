<script lang="ts">
    import type { SRSCard } from "$lib/types/srs";
    import type { VocabEntry } from "$lib/types/vocab";
    import StateBadge from "./StateBadge.svelte";
    import WordDetailModal from "./WordDetailModal.svelte";
    import { findSenseForCard, getSenseIndex } from "$lib/stores/srs.svelte";
    import ClickableWord from "$lib/components/ui/ClickableWord.svelte";
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

    const currentSense = $derived.by(() => {
        return findSenseForCard(card, vocabEntry);
    });

    const senseIndex = $derived.by(() => {
        return getSenseIndex(vocabEntry, card.sense_id);
    });

    const totalSenses = $derived(vocabEntry?.senses?.length ?? 0);

    const memoryTip = $derived(vocabEntry?.root_info?.memory_strategy ?? null);

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

    function handleOpenModal(e: MouseEvent) {
        e.stopPropagation();
        isModalOpen = true;
    }

    function handleCloseModal() {
        isModalOpen = false;
    }
</script>

<div
    class="flashcard-container"
    onclick={onFlip}
    onkeydown={(e) => e.key === "Enter" && onFlip()}
    role="button"
    tabindex="0"
>
    <div class="flashcard-inner" class:flipped={isFlipped}>
        <!-- Front -->
        <div class="flashcard-face flashcard-front">
            <div class="flex items-center justify-between">
                <StateBadge state={card.state} />
                <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
                <div onclick={(e) => e.stopPropagation()}>
                    <AudioButton text={card.lemma} size="lg" />
                </div>
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
        <div class="flashcard-face flashcard-back">
            <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2">
                    <StateBadge state={card.state} />
                    {#if totalSenses > 1}
                        <span
                            class="text-xs text-content-tertiary bg-surface-page px-2 py-0.5 rounded"
                        >
                            涵義 {senseIndex + 1}/{totalSenses}
                        </span>
                    {/if}
                </div>
                <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
                <div
                    class="flex items-center gap-1"
                    onclick={(e) => e.stopPropagation()}
                >
                    <AudioButton text={card.lemma} size="md" />
                    <button
                        type="button"
                        class="nav-detail-btn"
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

            <div class="text-center mb-3">
                <h2
                    class="text-xl font-semibold tracking-tight text-content-primary"
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
                    <div class="space-y-3">
                        <!-- Definition -->
                        <div class="definition-block">
                            <p
                                class="text-base text-content-primary leading-relaxed"
                            >
                                {currentSense.zh_def}
                            </p>
                            {#if currentSense.en_def}
                                <p
                                    class="text-sm text-content-tertiary mt-1 leading-relaxed"
                                >
                                    {currentSense.en_def}
                                </p>
                            {/if}
                        </div>

                        <!-- Memory Tip -->
                        {#if memoryTip}
                            <div class="memory-tip-block">
                                <div class="flex items-start gap-2">
                                    <svg
                                        class="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5"
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke-width="1.5"
                                        stroke="currentColor"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
                                        />
                                    </svg>
                                    <p
                                        class="text-sm text-content-secondary leading-relaxed"
                                    >
                                        {memoryTip}
                                    </p>
                                </div>
                            </div>
                        {/if}

                        <!-- Example -->
                        {#if currentExample}
                            <div class="example-block">
                                <div
                                    class="flex items-center justify-between mb-2"
                                >
                                    <span
                                        class="text-xs font-medium text-content-tertiary"
                                    >
                                        {currentExample.source
                                            ? "真實考題"
                                            : "學習例句"}
                                    </span>
                                    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
                                    <div onclick={(e) => e.stopPropagation()}>
                                        <AudioButton
                                            text={currentExample.text}
                                            size="sm"
                                        />
                                    </div>
                                </div>
                                <p
                                    class="text-sm text-content-secondary leading-relaxed"
                                >
                                    <ClickableWord
                                        text={currentExample.text}
                                        highlightWord={card.lemma}
                                    />
                                </p>
                                {#if currentExample.source}
                                    <div
                                        class="inline-flex items-center gap-1.5 px-2 py-1 bg-surface-page rounded text-xs text-content-tertiary mt-2"
                                    >
                                        <svg
                                            class="w-3 h-3"
                                            fill="none"
                                            stroke="currentColor"
                                            viewBox="0 0 24 24"
                                            stroke-width="1.5"
                                        >
                                            <path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
                                            />
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

{#if vocabEntry}
    <WordDetailModal
        entry={vocabEntry}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
    />
{/if}

<style>
    .flashcard-container {
        cursor: pointer;
    }

    .flashcard-inner {
        display: grid;
        transition: opacity 0.2s ease-out;
    }

    .flashcard-face {
        grid-area: 1 / 1;
        min-height: 360px;
        max-height: 520px;
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        background: var(--color-surface-primary);
        border-radius: 8px;
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-card);
        transition:
            opacity 0.2s ease-out,
            transform 0.2s ease-out;
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

    .definition-block {
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--color-border);
    }

    .memory-tip-block {
        padding: 0.75rem;
        background: rgba(251, 191, 36, 0.08);
        border-radius: 6px;
        border: 1px solid rgba(251, 191, 36, 0.2);
    }

    .example-block {
        padding: 0.75rem;
        background: var(--color-surface-secondary);
        border-radius: 6px;
    }

    .nav-detail-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 2rem;
        height: 2rem;
        border-radius: 6px;
        color: var(--color-content-tertiary);
        transition: all 0.15s ease;
    }

    .nav-detail-btn:hover {
        background: var(--color-surface-hover);
        color: var(--color-accent);
    }

    .custom-scrollbar {
        scrollbar-width: thin;
        scrollbar-color: var(--color-border-hover) transparent;
    }

    .custom-scrollbar::-webkit-scrollbar {
        width: 4px;
    }

    .custom-scrollbar::-webkit-scrollbar-track {
        background: transparent;
    }

    .custom-scrollbar::-webkit-scrollbar-thumb {
        background-color: var(--color-border-hover);
        border-radius: 2px;
    }
</style>
