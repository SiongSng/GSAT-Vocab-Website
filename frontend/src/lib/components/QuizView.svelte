<script lang="ts">
    import {
        getQuizStore,
        startQuiz,
        submitAnswer,
        nextQuestion,
        exitQuiz,
        retryIncorrect,
        isAnswerCorrect,
        didMatchInflected,
        type QuizConfig,
        type QuizQuestionType,
    } from "$lib/stores/quiz.svelte";

    import QuizStart from "./quiz/QuizStart.svelte";
    import QuizChoiceQuestion from "./quiz/QuizChoiceQuestion.svelte";
    import QuizSpellingQuestion from "./quiz/QuizSpellingQuestion.svelte";
    import QuizResult from "./quiz/QuizResult.svelte";
    import WordDetailModal from "./srs/WordDetailModal.svelte";
    import { lookupEntry } from "$lib/stores/vocab-db";
    import type { VocabEntry } from "$lib/types/vocab";
    import { isWordEntry, isPhraseEntry } from "$lib/types/vocab";

    const quiz = getQuizStore();

    let showFeedback = $state(false);
    let audioContext: AudioContext | null = null;

    function getAudioContext(): AudioContext {
        if (!audioContext) {
            audioContext = new AudioContext();
        }
        return audioContext;
    }

    function playCorrectSound() {
        const ctx = getAudioContext();
        const now = ctx.currentTime;

        const frequencies = [523.25, 659.25];
        const duration = 0.12;

        frequencies.forEach((freq, i) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.type = "sine";
            osc.frequency.value = freq;

            gain.gain.setValueAtTime(0, now + i * duration);
            gain.gain.linearRampToValueAtTime(0.25, now + i * duration + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.01, now + (i + 1) * duration);

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.start(now + i * duration);
            osc.stop(now + (i + 1) * duration + 0.05);
        });
    }
    let detailEntry = $state<VocabEntry | null>(null);
    let isDetailOpen = $state(false);

    async function handleShowDetail(lemma: string, entryType?: "word" | "phrase") {
        try {
            const entry = await lookupEntry(lemma, entryType);
            if (entry && (isWordEntry(entry) || isPhraseEntry(entry))) {
                detailEntry = entry;
                isDetailOpen = true;
            }
        } catch (e) {
            console.error("Failed to load word detail:", e);
        }
    }

    function resetQuestionState() {
        showFeedback = false;
    }

    async function handleStartQuiz(config: {
        count: number;
        entry_type?: "word" | "phrase";
        force_type?: QuizQuestionType;
    }) {
        const quizConfig: QuizConfig = {
            count: config.count,
            entry_type: config.entry_type,
            force_type: config.force_type,
        };

        await startQuiz(quizConfig);
        resetQuestionState();
    }

    function handleSelect(value: string) {
        if (showFeedback) return;
        submitAnswer(value);
        showFeedback = true;

        if (isAnswerCorrect(quiz.currentIndex)) {
            playCorrectSound();
        }
    }

    function handleContinue() {
        nextQuestion();
        resetQuestionState();
    }

    function handleExit() {
        exitQuiz();
        resetQuestionState();
    }

    async function handleRetryWrong() {
        await retryIncorrect();
        resetQuestionState();
    }

    function getWrongWords() {
        return quiz.incorrectQuestions.map((q) => ({
            lemma: q.lemma,
            definition: q.explanation?.correct_usage || q.correct,
        }));
    }

    function isChoiceQuestion(
        type: QuizQuestionType | "adaptive" | null,
    ): boolean {
        return (
            type === "recognition" ||
            type === "reverse" ||
            type === "fill_blank" ||
            type === "distinction"
        );
    }
</script>

<div class="quiz-view">
    {#if quiz.isLoading}
        <div class="state-container">
            <div class="loading-content">
                <div class="spinner"></div>
                <p class="state-text">準備測驗中...</p>
            </div>
        </div>
    {:else if quiz.error}
        <div class="state-container">
            <div class="error-card">
                <div class="error-icon">
                    <svg
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="8" x2="12" y2="12" />
                        <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                </div>
                <h3>發生錯誤</h3>
                <p class="error-message">{quiz.error}</p>
                <button type="button" class="btn-primary" onclick={handleExit}>
                    返回首頁
                </button>
            </div>
        </div>
    {:else if quiz.isComplete}
        <QuizResult
            score={quiz.score}
            total={quiz.questions.length}
            wrongWords={getWrongWords()}
            onRetryWrong={handleRetryWrong}
            onContinue={handleExit}
        />
    {:else if quiz.isActive && quiz.currentQuestion}
        {#if isChoiceQuestion(quiz.currentQuestion.type)}
            <QuizChoiceQuestion
                question={quiz.currentQuestion}
                questionIndex={quiz.currentIndex}
                totalQuestions={quiz.questions.length}
                {showFeedback}
                isCorrect={showFeedback
                    ? isAnswerCorrect(quiz.currentIndex)
                    : null}
                onSelect={handleSelect}
                onContinue={handleContinue}
                onExit={handleExit}
                onShowDetail={(lemma) => handleShowDetail(lemma, quiz.currentQuestion?.entry_type)}
                disableKeyboard={isDetailOpen}
            />
        {:else}
            <QuizSpellingQuestion
                question={quiz.currentQuestion}
                questionIndex={quiz.currentIndex}
                totalQuestions={quiz.questions.length}
                {showFeedback}
                isCorrect={showFeedback
                    ? isAnswerCorrect(quiz.currentIndex)
                    : null}
                matchedInflected={showFeedback
                    ? didMatchInflected(quiz.currentIndex)
                    : false}
                onSubmit={handleSelect}
                onContinue={handleContinue}
                onExit={handleExit}
                onShowDetail={(lemma) => handleShowDetail(lemma, quiz.currentQuestion?.entry_type)}
            />
        {/if}
    {:else}
        <QuizStart onStart={handleStartQuiz} />
    {/if}

    {#if detailEntry}
        <WordDetailModal
            entry={detailEntry}
            isOpen={isDetailOpen}
            onClose={() => (isDetailOpen = false)}
        />
    {/if}
</div>

<style>
    .quiz-view {
        height: 100%;
        width: 100%;
        overflow-y: auto;
        background-color: var(--color-surface-page);
        padding-bottom: var(--bottom-nav-height);
    }

    .state-container {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100%;
        padding: 1.5rem;
    }

    /* Loading State */
    .loading-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
    }

    .spinner {
        width: 32px;
        height: 32px;
        border: 3px solid var(--color-surface-hover);
        border-top-color: var(--color-accent);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    .state-text {
        color: var(--color-content-secondary);
        font-size: 0.9375rem;
    }

    /* Error State */
    .error-card {
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 12px;
        padding: 2rem;
        width: 100%;
        max-width: 400px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }

    .error-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background-color: rgba(239, 68, 68, 0.1);
        color: #ef4444;
        margin-bottom: 1rem;
    }

    .error-card h3 {
        margin: 0 0 0.5rem 0;
        color: var(--color-content-primary);
        font-size: 1.125rem;
    }

    .error-message {
        color: var(--color-content-secondary);
        font-size: 0.9375rem;
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }

    .btn-primary {
        width: 100%;
        padding: 0.75rem;
        background-color: var(--color-content-primary);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 0.9375rem;
        font-weight: 500;
        cursor: pointer;
        transition: opacity 0.2s;
    }

    .btn-primary:hover {
        opacity: 0.9;
    }
</style>
