<script lang="ts">
    import type { QuizQuestion } from "$lib/stores/quiz-generator";
    import HighlightedText from "$lib/components/ui/HighlightedText.svelte";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";
    import { createAudioController } from "$lib/tts";
    import { STORAGE_KEYS } from "$lib/storage-keys";
    import { formatExamSource } from "$lib/utils/quiz";
    import { getAppStore } from "$lib/stores/app.svelte";
    import QuizShell from "./QuizShell.svelte";
    import QuizFeedback from "./QuizFeedback.svelte";

    interface Props {
        question: QuizQuestion;
        questionIndex: number;
        totalQuestions: number;
        showFeedback: boolean;
        isCorrect: boolean | null;
        onSubmit: (answer: string) => void;
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
        onSubmit,
        onContinue,
        onExit,
        onShowDetail,
    }: Props = $props();

    const app = getAppStore();
    let shuffledLetters: string[] = $state([]);
    let answerSlots: (string | null)[] = $state([]);
    let usedIndices: Set<number> = $state(new Set());
    let typedInput = $state("");
    let inputRef: HTMLInputElement | undefined = $state();

    const progress = $derived({
        current: questionIndex + 1,
        total: totalQuestions,
    });
    const audioController = createAudioController(() => question.lemma);

    function getAutoSpeak(): boolean {
        if (typeof window === "undefined") return false;
        const saved = localStorage.getItem(STORAGE_KEYS.STUDY_SETTINGS);
        if (!saved) return false;
        const settings = JSON.parse(saved);
        return settings.autoSpeak ?? true;
    }

    function initQuestion() {
        const word = question.lemma.toLowerCase();
        // Filter out spaces/special chars for slots, but keep length correct relative to letters
        const letters = word
            .split("")
            .filter((c) => c.match(/[a-z0-9]/i) || c === " ");

        // Simple shuffle
        const letterPool = letters
            .filter((c) => c !== " ")
            .sort(() => Math.random() - 0.5);

        shuffledLetters = letterPool;
        // Initialize slots with null, but respect spaces in the original phrase if needed
        // For simplicity, we just make slots for the length of non-space chars
        answerSlots = new Array(letterPool.length).fill(null);
        usedIndices = new Set();
        typedInput = "";

        // Focus input on desktop
        if (window.matchMedia("(min-width: 768px)").matches) {
            setTimeout(() => inputRef?.focus(), 50);
        }

        if (getAutoSpeak() && !showFeedback) {
            playAudio();
        }
    }

    $effect(() => {
        void question.lemma;
        initQuestion();
    });

    function selectLetter(letter: string, index: number) {
        if (showFeedback || usedIndices.has(index)) return;

        const emptySlotIdx = answerSlots.findIndex((s) => s === null);
        if (emptySlotIdx !== -1) {
            answerSlots[emptySlotIdx] = letter;
            usedIndices.add(index);
            // trigger reactivity
            usedIndices = new Set(usedIndices);
        }
    }

    function removeLetterAt(slotIndex: number) {
        if (showFeedback) return;
        const letter = answerSlots[slotIndex];
        if (!letter) return;

        // Find which tile index this letter came from (the last one added ideally, but simple first match of used is fine for UI logic)
        // To be precise we need to track mapping. But for this simple UI:
        // We find the first index in usedIndices that corresponds to this letter in shuffledLetters
        // AND isn't "claimed" by another slot. This is complex to track perfectly without an ID.
        // Simplified: Just remove from slot and find *an* available index to free up.

        // Actually, better approach: track mapping. But let's stick to the previous logic if it worked, or improve.
        // Improvement: We just need to free *one* instance of this letter index.
        let indexToFree = -1;

        // Reconstruct used indices from current slots to find what's missing? No.
        // Let's iterate shuffledLetters to find a match that is currently in usedIndices.
        for (const i of usedIndices) {
            if (shuffledLetters[i] === letter) {
                // Check if this specific index is needed by OTHER slots?
                // This is the tricky part. Let's just remove the first match.
                // It doesn't matter visually which tile flies back as long as it's the same letter.
                indexToFree = i;
                // We need to ensure we don't free an index that other slots are relying on?
                // Since slots don't hold IDs, it's ambiguous.
                // But for "remove last added", we usually act on the last slot.
                // If user clicks middle slot, it's ambiguous.
                break;
            }
        }

        if (indexToFree !== -1) {
            usedIndices.delete(indexToFree);
            usedIndices = new Set(usedIndices);
            answerSlots[slotIndex] = null;
        }
    }

    function isComplete() {
        if (typedInput.length > 0) return typedInput.length > 0;
        return answerSlots.every((s) => s !== null);
    }

    function getAnswer() {
        if (typedInput.length > 0) return typedInput;
        return answerSlots.join("");
    }

    function handleSubmit() {
        if (!isComplete() || showFeedback) return;
        onSubmit(getAnswer());
    }

    function handleInputChange(e: Event) {
        const input = e.target as HTMLInputElement;
        typedInput = input.value;
    }

    function handleKeydown(e: KeyboardEvent) {
        if (showFeedback) {
            if (e.key === "Enter") {
                e.preventDefault();
                onContinue();
            }
            return;
        }

        // If user is typing in the input box, let them.
        if (document.activeElement === inputRef) {
            if (e.key === "Enter") {
                e.preventDefault();
                handleSubmit();
            }
            return;
        }

        // Backspace support for tiles
        if (e.key === "Backspace" && typedInput.length === 0) {
            // Remove last filled slot
            const lastFilledIdx = answerSlots
                .map((s, i) => (s !== null ? i : -1))
                .filter((i) => i !== -1)
                .pop();

            if (lastFilledIdx !== undefined) {
                removeLetterAt(lastFilledIdx);
            }
        }
    }

    function playAudio() {
        audioController.play();
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<QuizShell {progress} {onExit}>
    <div class="card">
        <!-- Prompt / Definition -->
        <div class="prompt-area">
            <div class="audio-header">
                <button
                    type="button"
                    class="audio-btn"
                    onclick={playAudio}
                    aria-label="播放發音"
                >
                    <svg
                        width="32"
                        height="32"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                    >
                        <path
                            d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"
                        />
                    </svg>
                </button>
            </div>

            {#if question.sentence_context}
                <div class="sentence-box">
                    <div class="sentence-header">
                        <p class="sentence">
                            <HighlightedText
                                text={question.sentence_context.replace(
                                    /_+/g,
                                    question.lemma,
                                )}
                                highlightLemma={question.lemma}
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
                </div>
            {/if}

            <p class="definition">{question.prompt}</p>
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
            {#if showFeedback && question.hint}
                <p class="hint">{question.hint}</p>
            {/if}
        </div>

        <!-- Input Area -->
        <div class="interaction-area">
            <!-- Text Input (Primary) -->
            <div class="input-wrapper">
                <input
                    bind:this={inputRef}
                    type="text"
                    class="text-input"
                    class:input-correct={showFeedback && isCorrect}
                    class:input-wrong={showFeedback && !isCorrect}
                    value={typedInput}
                    oninput={handleInputChange}
                    placeholder="輸入單字..."
                    autocomplete="off"
                    autocorrect="off"
                    spellcheck="false"
                    disabled={showFeedback}
                />
            </div>

            <!-- Tiles (Alternative/Helper) -->
            {#if !typedInput && !showFeedback}
                <div class="tiles-container">
                    <!-- Answer Slots -->
                    <div class="slots-row">
                        {#each answerSlots as letter, i}
                            <button
                                class="slot"
                                class:slot-filled={letter !== null}
                                onclick={() => removeLetterAt(i)}
                                disabled={letter === null}
                            >
                                {letter || ""}
                            </button>
                        {/each}
                    </div>

                    <!-- Available Letters -->
                    <div class="letters-grid">
                        {#each shuffledLetters as letter, i}
                            <button
                                class="tile"
                                class:tile-used={usedIndices.has(i)}
                                onclick={() => selectLetter(letter, i)}
                                disabled={usedIndices.has(i)}
                            >
                                {letter}
                            </button>
                        {/each}
                    </div>
                </div>
            {/if}

            {#if !showFeedback}
                <div class="actions">
                    <button
                        class="submit-btn"
                        onclick={handleSubmit}
                        disabled={!isComplete()}
                    >
                        送出答案
                        {#if !app.isMobile}
                            <span class="kbd-hint">Enter</span>
                        {/if}
                    </button>
                </div>
            {/if}
        </div>
    </div>

    {#if showFeedback && isCorrect !== null}
        <QuizFeedback
            {isCorrect}
            {question}
            {onContinue}
            onShowDetail={() => onShowDetail(question.lemma)}
            isSentenceDisplayed={!!question.sentence_context}
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

    /* Prompt */
    .prompt-area {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        margin-bottom: 2rem;
    }

    .audio-header {
        margin-bottom: 1rem;
    }

    .audio-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 64px;
        height: 64px;
        border-radius: 50%;
        background-color: var(--color-accent);
        color: white;
        border: none;
        cursor: pointer;
        transition: transform 0.1s;
        box-shadow: 0 4px 12px rgba(var(--color-accent-rgb), 0.3);
    }

    .audio-btn:hover {
        transform: scale(1.05);
    }

    .audio-btn:active {
        transform: scale(0.95);
    }

    .definition {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--color-content-primary);
        line-height: 1.3;
        margin: 0.5rem 0 0 0;
        letter-spacing: -0.01em;
    }

    .sentence-box {
        padding: 1.25rem;
        background-color: var(--color-surface-page);
        border: 1px solid var(--color-border);
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: left;
        width: 100%;
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

    .hint {
        font-size: 0.875rem;
        color: var(--color-accent);
        margin-top: 0.5rem;
    }

    /* Input */
    .interaction-area {
        width: 100%;
        max-width: 400px;
        margin: 0 auto;
    }

    .input-wrapper {
        margin-bottom: 1.5rem;
        display: none;
    }

    @media (min-width: 768px) {
        .input-wrapper {
            display: block;
        }
    }

    .text-input {
        width: 100%;
        padding: 0.875rem 1rem;
        font-size: 1.25rem;
        font-family: var(--font-mono, monospace);
        text-align: center;
        background-color: var(--color-surface-page);
        border: 2px solid var(--color-border);
        border-radius: 8px;
        color: var(--color-content-primary);
        transition: all 0.2s;
    }

    .text-input:focus {
        outline: none;
        border-color: var(--color-accent);
        box-shadow: 0 0 0 3px rgba(var(--color-accent-rgb), 0.1);
    }

    .text-input:disabled {
        opacity: 0.7;
        background-color: var(--color-surface-hover);
    }

    .input-correct {
        border-color: #4caf50;
        background-color: rgba(76, 175, 80, 0.05);
        color: #2e7d32;
    }

    .input-wrong {
        border-color: #ef4444;
        background-color: rgba(239, 68, 68, 0.05);
        color: #c62828;
    }

    /* Tiles */
    .tiles-container {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        margin-bottom: 1.5rem;
    }

    @media (min-width: 768px) {
        .tiles-container {
            display: none;
        }
    }

    .slots-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 0.5rem;
        min-height: 3rem;
    }

    .slot {
        width: 2.5rem;
        height: 3rem;
        border: 1px dashed var(--color-border);
        border-radius: 6px;
        background: transparent;
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--color-content-primary);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: default;
        transition: all 0.2s;
    }

    .slot-filled {
        border-style: solid;
        border-color: var(--color-accent);
        background-color: var(--color-surface-page);
        cursor: pointer;
    }

    .letters-grid {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 0.5rem;
    }

    .tile {
        width: 2.5rem;
        height: 2.5rem;
        background-color: var(--color-surface-page);
        border: 1px solid var(--color-border);
        border-radius: 6px;
        font-size: 1.125rem;
        font-weight: 500;
        color: var(--color-content-primary);
        cursor: pointer;
        transition: all 0.1s;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }

    .tile:hover:not(:disabled) {
        transform: translateY(-2px);
        background-color: var(--color-surface-hover);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .tile:active:not(:disabled) {
        transform: translateY(0);
    }

    .tile-used {
        opacity: 0.2;
        cursor: default;
        transform: none !important;
        box-shadow: none !important;
    }

    /* Actions */
    .submit-btn {
        width: 100%;
        padding: 0.875rem;
        background-color: var(--color-accent);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }

    .submit-btn:hover:not(:disabled) {
        opacity: 0.9;
    }

    .submit-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .kbd-hint {
        font-size: 0.75rem;
        background: rgba(255, 255, 255, 0.2);
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
    }

    @media (max-width: 640px) {
        .card {
            padding: 0;
            background: transparent;
            border: none;
            box-shadow: none;
        }

        .definition {
            font-size: 1.25rem;
        }

        .audio-btn {
            width: 56px;
            height: 56px;
        }

        .slot,
        .tile {
            width: 2.25rem;
            height: 2.75rem;
            font-size: 1.125rem;
        }
        .tile {
            height: 2.25rem;
        }
    }
</style>
