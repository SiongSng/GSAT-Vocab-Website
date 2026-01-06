<script lang="ts">
    import type { QuizQuestion } from "$lib/stores/quiz-generator";
    import HighlightedText from "$lib/components/ui/HighlightedText.svelte";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";
    import { createAudioController } from "$lib/tts";
    import { STORAGE_KEYS } from "$lib/storage-keys";
    import { formatExamSource } from "$lib/utils/quiz";
    import QuizShell from "./QuizShell.svelte";
    import QuizFeedback from "./QuizFeedback.svelte";

    interface Props {
        question: QuizQuestion;
        questionIndex: number;
        totalQuestions: number;
        showFeedback: boolean;
        isCorrect: boolean | null;
        onSelect: (answer: string) => void;
        onContinue: () => void;
        onExit: () => void;
        onShowDetail: (lemma: string) => void;
    }

    let {
        question,
        questionIndex,
        totalQuestions,
        showFeedback,
        isCorrect,
        onSelect,
        onContinue,
        onExit,
        onShowDetail,
    }: Props = $props();

    let selectedAnswer = $state<string | null>(null);

    const progress = $derived({
        current: questionIndex + 1,
        total: totalQuestions,
    });

    const isFillType = $derived(
        question.type === "fill_blank" || question.type === "distinction",
    );

    const audioController = createAudioController(() => question.lemma);

    function getAutoSpeak() {
        if (typeof window === "undefined") return false;
        const saved = localStorage.getItem(STORAGE_KEYS.STUDY_SETTINGS);
        if (!saved) return false;
        const settings = JSON.parse(saved);
        return settings.autoSpeak ?? true;
    }

    $effect(() => {
        question.lemma;
        selectedAnswer = null;

        // Auto-play audio for recognition type
        if (
            question.type === "recognition" &&
            !showFeedback &&
            getAutoSpeak()
        ) {
            audioController.play();
        }
    });

    function handleSelect(value: string) {
        if (showFeedback) return;
        selectedAnswer = value;
        onSelect(value);
    }

    function handleKeydown(e: KeyboardEvent) {
        if (showFeedback) {
            if (e.key === "Enter") {
                e.preventDefault();
                onContinue();
            }
            return;
        }

        const key = parseInt(e.key);
        if (!isNaN(key) && key >= 1 && key <= 4 && question.options) {
            const idx = key - 1;
            if (idx < question.options.length) {
                handleSelect(question.options[idx].value);
            }
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<QuizShell {progress} {onExit}>
    <div class="card">
        <!-- Question Prompt Area -->
        <div class="prompt-area">
            {#if isFillType}
                <div class="sentence-box">
                    <div class="sentence-header">
                        <p class="sentence">
                            <HighlightedText
                                text={question.sentence_context?.replace(
                                    /_+/g,
                                    question.lemma,
                                ) ?? ""}
                                highlightLemma={question.lemma}
                                isPhrase={question.entry_type === "phrase"}
                                blankMode={!showFeedback}
                            />
                        </p>
                        {#if showFeedback && question.explanation?.correct_usage}
                            <AudioButton
                                text={question.explanation.correct_usage}
                                size="sm"
                                variant="subtle"
                                class="sentence-audio"
                            />
                        {/if}
                    </div>
                    {#if question.exam_source}
                        <div class="source-info">
                            <svg
                                width="12"
                                height="12"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="2.5"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            >
                                <path
                                    d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"
                                ></path>
                                <path d="M8 7h6"></path>
                                <path d="M8 11h8"></path>
                            </svg>
                            <span class="source-text">
                                {formatExamSource(question.exam_source)}
                            </span>
                        </div>
                    {/if}
                </div>
                {#if showFeedback && question.hint}
                    <p class="hint-text">{question.hint}</p>
                {:else if question.type === "recognition"}
                    <div class="word-display">
                        <div class="ghost-spacer"></div>
                        <span class="word">{question.lemma}</span>
                        <div class="audio-wrapper">
                            <AudioButton text={question.lemma} size="lg" />
                        </div>
                    </div>
                    <p class="instruction">選擇正確的中文意思</p>
                {:else if question.type === "reverse"}
                    <div class="def-display">
                        <p class="definition">{question.prompt}</p>
                        {#if showFeedback && question.hint}
                            <p class="pos-hint">{question.hint}</p>
                        {/if}
                    </div>
                    <p class="instruction">選擇對應的單字</p>
                {/if}
            {:else if question.type === "recognition"}
                <div class="word-display">
                    <span class="word">{question.lemma}</span>
                    <AudioButton text={question.lemma} size="lg" />
                </div>
                <p class="instruction">選擇正確的中文意思</p>
            {:else if question.type === "reverse"}
                <div class="def-display">
                    <p class="definition">{question.prompt}</p>
                    {#if showFeedback && question.hint}
                        <p class="pos-hint">{question.hint}</p>
                    {/if}
                </div>
                <p class="instruction">選擇對應的英文單字</p>
            {/if}
        </div>

        <!-- Options Area -->
        <div class="options-list">
            {#each question.options || [] as option, i}
                {@const isCorrectOpt =
                    option.value.toLowerCase() ===
                    question.correct.toLowerCase()}
                {@const isSelectedOpt =
                    selectedAnswer?.toLowerCase() ===
                    option.value.toLowerCase()}

                <svelte:element
                    this={showFeedback ? "div" : "button"}
                    class="option-btn"
                    class:correct={showFeedback && isCorrectOpt}
                    class:wrong={showFeedback && isSelectedOpt && !isCorrectOpt}
                    class:faded={showFeedback &&
                        !isCorrectOpt &&
                        !isSelectedOpt}
                    onclick={() => handleSelect(option.value)}
                    disabled={showFeedback ? undefined : showFeedback}
                    role={showFeedback ? "group" : undefined}
                >
                    <span class="key-indicator">{i + 1}</span>
                    <span class="option-label">
                        {#if showFeedback && question.type !== "recognition"}
                            <HighlightedText text={option.label} />
                        {:else}
                            {option.label}
                        {/if}
                    </span>

                    {#if showFeedback && isCorrectOpt}
                        <span class="status-icon">
                            <svg
                                width="20"
                                height="20"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="3"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            >
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </span>
                    {/if}
                    {#if showFeedback && isSelectedOpt && !isCorrectOpt}
                        <span class="status-icon">
                            <svg
                                width="20"
                                height="20"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="3"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            >
                                <line x1="18" y1="6" x2="6" y2="18"></line>
                                <line x1="6" y1="6" x2="18" y2="18"></line>
                            </svg>
                        </span>
                    {/if}
                </svelte:element>
            {/each}
        </div>
    </div>

    {#if showFeedback && isCorrect !== null}
        <QuizFeedback
            {isCorrect}
            {question}
            {onContinue}
            onShowDetail={() => onShowDetail(question.lemma)}
            isSentenceDisplayed={isFillType}
        />
    {/if}
</QuizShell>

<style>
    .card {
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }

    /* Prompt Styles */
    .prompt-area {
        margin-bottom: 2rem;
        text-align: center;
    }

    /* Sentence / Fill Blank */
    .sentence-box {
        position: relative;
        padding: 1.5rem;
        background-color: var(--color-surface-page);
        border: 1px solid var(--color-border);
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: left;
    }

    .sentence-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
    }

    .sentence {
        font-size: 1.125rem;
        line-height: 1.7;
        color: var(--color-content-primary);
        margin: 0;
        font-family: var(--font-serif, serif);
        flex: 1;
    }

    :global(.sentence-audio) {
        margin-top: 0.25rem;
        background: var(--color-surface-primary) !important;
        border: 1px solid var(--color-border);
    }

    .source-info {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        margin-top: 0.75rem;
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
        background-color: var(--color-surface-hover);
        padding: 0.25rem 0.625rem;
        border-radius: 6px;
        font-weight: 500;
        border: 1px solid var(--color-border);
    }

    .source-text {
        opacity: 0.85;
    }

    /* Word Recognition */
    .word-display {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center;
        margin-bottom: 0.5rem;
    }

    .ghost-spacer {
        grid-column: 1;
    }

    .word {
        grid-column: 2;
        font-size: 2rem;
        font-weight: 700;
        color: var(--color-content-primary);
        line-height: 1.2;
    }

    .audio-wrapper {
        grid-column: 3;
        justify-self: start;
        padding-left: 0.75rem;
    }

    /* Definition / Reverse */
    .def-display {
        margin-bottom: 0.5rem;
    }

    .definition {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--color-content-primary);
        line-height: 1.4;
        margin: 0;
    }

    .instruction {
        font-size: 0.8125rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--color-content-tertiary);
        margin: 0;
        opacity: 0.8;
    }

    .hint-text,
    .pos-hint {
        font-size: 0.875rem;
        color: var(--color-accent);
        margin-top: 0.5rem;
    }

    /* Options List */
    .options-list {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .option-btn {
        display: flex;
        align-items: center;
        width: 100%;
        padding: 1.125rem 1rem;
        background: var(--color-surface-page);
        border: 1px solid var(--color-border);
        border-radius: 10px;
        cursor: default;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        text-align: left;
        position: relative;
    }

    .option-btn:is(button) {
        cursor: pointer;
    }

    .option-btn:is(button):hover:not(:disabled) {
        background-color: var(--color-surface-hover);
        transform: translateY(-1px);
    }

    .key-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--color-content-tertiary);
        background: rgba(0, 0, 0, 0.05);
        border-radius: 6px;
        margin-right: 1rem;
        flex-shrink: 0;
    }

    .option-label {
        flex: 1;
        font-size: 1rem;
        color: var(--color-content-primary);
        font-weight: 500;
    }

    /* States */
    .option-btn.correct {
        background-color: rgba(76, 175, 80, 0.1);
        border-color: #4caf50;
        color: #2e7d32;
    }

    .option-btn.correct .key-indicator {
        background-color: #4caf50;
        color: white;
    }

    .option-btn.wrong {
        background-color: rgba(239, 68, 68, 0.1);
        border-color: #ef4444;
        color: #c62828;
    }

    .option-btn.wrong .key-indicator {
        background-color: #ef4444;
        color: white;
    }

    .option-btn.faded {
        opacity: 0.4;
    }

    .status-icon {
        margin-left: 0.5rem;
    }

    .correct .status-icon {
        color: #4caf50;
    }
    .wrong .status-icon {
        color: #ef4444;
    }

    @media (max-width: 640px) {
        .card {
            padding: 1.5rem;
            background: transparent;
            border: none;
            box-shadow: none;
            padding: 0;
        }

        .sentence-box {
            padding: 1rem;
        }

        .option-btn {
            background-color: var(--color-surface-primary);
            border: 1px solid var(--color-border);
        }
    }
</style>
