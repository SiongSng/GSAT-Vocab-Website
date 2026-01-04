<script lang="ts">
    import {
        getQuizStore,
        startQuiz,
        submitAnswer,
        nextQuestion,
        resetQuiz,
        retryIncorrect,
        isAnswerCorrect,
        markHintUsed,
        type QuizConfig,
        type QuizQuestionType,
    } from "$lib/stores/quiz.svelte";
    import {
        getDueCount,
        getWeakCount,
        getAvailableCount,
        getTodayStudiedCount,
    } from "$lib/stores/quiz-generator";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";

    const quiz = getQuizStore();

    let questionCount = $state(10);
    let entryType = $state<"word" | "phrase" | "all">("all");
    let quizSource = $state<"srs_due" | "srs_weak" | "today_studied">("srs_due");
    let showSettings = $state(false);
    let showFeedback = $state(false);
    let selectedAnswer = $state<string | null>(null);
    let showHint = $state(false);

    let spellingInput = $state("");
    let shuffledLetters = $state<string[]>([]);
    let answerSlots = $state<string[]>([]);
    let usedIndices = $state<Set<number>>(new Set());

    let dueCount = $state(0);
    let weakCount = $state(0);
    let todayStudiedCount = $state(0);
    let availableCount = $state(0);

    $effect(() => {
        loadCounts();
    });

    async function loadCounts() {
        dueCount = await getDueCount();
        weakCount = await getWeakCount();
        todayStudiedCount = await getTodayStudiedCount();
        availableCount = await getAvailableCount();
    }

    function getProgressPercent(): number {
        if (quiz.questions.length === 0) return 0;
        return (quiz.currentIndex / quiz.questions.length) * 100;
    }

    async function handleStartQuiz() {
        const config: QuizConfig = {
            source: quizSource,
            count: questionCount,
            entry_type: entryType === "all" ? undefined : entryType,
        };

        await startQuiz(config);
        resetQuestionState();
    }

    function resetQuestionState() {
        showFeedback = false;
        selectedAnswer = null;
        showHint = false;
        spellingInput = "";
        shuffledLetters = [];
        answerSlots = [];
        usedIndices = new Set();
    }

    $effect(() => {
        if (quiz.currentQuestion?.type === "spelling" && quiz.isActive) {
            initSpellingQuestion();
        }
    });

    function initSpellingQuestion() {
        if (!quiz.currentQuestion) return;
        const word = quiz.currentQuestion.correct;
        const letters = word.split("");
        shuffledLetters = [...letters].sort(() => Math.random() - 0.5);
        answerSlots = new Array(word.length).fill("");
        usedIndices = new Set();
    }

    function selectLetter(idx: number) {
        if (usedIndices.has(idx)) return;

        const emptySlotIdx = answerSlots.findIndex((s) => s === "");
        if (emptySlotIdx === -1) return;

        answerSlots[emptySlotIdx] = shuffledLetters[idx];
        usedIndices = new Set([...usedIndices, idx]);
    }

    function removeLetterAt(slotIdx: number) {
        if (!answerSlots[slotIdx]) return;

        const letter = answerSlots[slotIdx];
        const letterIdx = shuffledLetters.findIndex(
            (l, i) => l === letter && usedIndices.has(i),
        );

        if (letterIdx !== -1) {
            const newUsed = new Set(usedIndices);
            newUsed.delete(letterIdx);
            usedIndices = newUsed;
        }

        answerSlots[slotIdx] = "";
    }

    function isSpellingComplete(): boolean {
        return answerSlots.every((s) => s !== "");
    }

    function getSpellingAnswer(): string {
        return answerSlots.join("");
    }

    function handleChoiceSelect(value: string) {
        if (showFeedback) return;
        selectedAnswer = value;
        submitAnswer(value);
        showFeedback = true;
    }

    function handleSpellingSubmit() {
        if (showFeedback) return;

        const answer =
            quiz.currentQuestion?.type === "spelling"
                ? getSpellingAnswer()
                : spellingInput.trim();

        if (!answer) return;
        selectedAnswer = answer;
        submitAnswer(answer);
        showFeedback = true;
    }

    function handleShowHint() {
        showHint = true;
        markHintUsed();
    }

    function handleNextQuestion() {
        nextQuestion();
        resetQuestionState();
        if (quiz.currentQuestion?.type === "spelling") {
            initSpellingQuestion();
        }
    }

    function handleRestart() {
        resetQuiz();
        resetQuestionState();
    }

    async function handleRetryIncorrect() {
        await retryIncorrect();
        resetQuestionState();
    }

    function getScorePercent(): number {
        if (quiz.questions.length === 0) return 0;
        return Math.round((quiz.score / quiz.questions.length) * 100);
    }

    function getWrongWords() {
        return quiz.incorrectQuestions.map((q) => ({
            lemma: q.lemma,
            definition: q.explanation?.correct_usage || q.correct,
        }));
    }

    function isChoiceQuestion(type: QuizQuestionType | "adaptive" | null): boolean {
        return (
            type === "recognition" ||
            type === "reverse" ||
            type === "fill_blank" ||
            type === "distinction"
        );
    }

    function isTypingQuestion(type: QuizQuestionType | "adaptive" | null): boolean {
        return type === "spelling";
    }

    function handleKeydown(e: KeyboardEvent) {
        if (!quiz.isActive || !quiz.currentQuestion) return;

        if (e.key === "Enter" && showFeedback) {
            e.preventDefault();
            handleNextQuestion();
            return;
        }

        if (showFeedback) return;

        if (quiz.currentQuestion.options && e.key >= "1" && e.key <= "4") {
            const idx = parseInt(e.key) - 1;
            if (idx < quiz.currentQuestion.options.length) {
                handleChoiceSelect(quiz.currentQuestion.options[idx].value);
            }
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="quiz-view h-full overflow-y-auto bg-surface-page">
    {#if quiz.isLoading}
        <div class="flex items-center justify-center h-full">
            <div class="text-center">
                <svg
                    class="w-10 h-10 animate-spin text-accent mx-auto mb-4"
                    viewBox="0 0 24 24"
                    fill="none"
                >
                    <circle
                        class="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="4"
                    ></circle>
                    <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                </svg>
                <p class="text-content-secondary text-sm">正在生成測驗...</p>
            </div>
        </div>
    {:else if quiz.error}
        <div class="flex items-center justify-center h-full p-5">
            <div
                class="max-w-md w-full bg-surface-primary border border-srs-again/30 rounded-lg p-6 text-center"
            >
                <p class="text-srs-again mb-4">{quiz.error}</p>
                <button
                    type="button"
                    class="px-4 py-2 bg-srs-again text-white rounded-md hover:opacity-90 transition-opacity text-sm font-medium"
                    onclick={handleRestart}
                >
                    返回
                </button>
            </div>
        </div>
    {:else if quiz.isComplete}
        <div class="results-page flex flex-col items-center justify-center min-h-full p-5">
            <div class="max-w-md w-full">
                <div class="results-hero text-center mb-8">
                    {#if getScorePercent() >= 80}
                        <span class="results-emoji text-6xl mb-4 block">🎉</span>
                        <h1 class="text-2xl font-semibold text-content-primary">
                            太棒了！
                        </h1>
                    {:else if getScorePercent() >= 60}
                        <span class="results-emoji text-6xl mb-4 block">👍</span>
                        <h1 class="text-2xl font-semibold text-content-primary">
                            不錯喔！
                        </h1>
                    {:else}
                        <span class="results-emoji text-6xl mb-4 block">💪</span>
                        <h1 class="text-2xl font-semibold text-content-primary">
                            繼續加油！
                        </h1>
                    {/if}
                </div>

                <div class="results-score text-center mb-8">
                    <span class="text-5xl font-semibold text-accent"
                        >{quiz.score}</span
                    >
                    <span class="text-3xl font-light text-content-tertiary mx-2"
                        >/</span
                    >
                    <span class="text-3xl font-light text-content-tertiary"
                        >{quiz.questions.length}</span
                    >
                </div>

                {#if getWrongWords().length > 0}
                    <div class="wrong-words-section mb-8">
                        <h2
                            class="text-base font-medium text-content-primary mb-3"
                        >
                            這些要多練習
                        </h2>
                        <div class="space-y-2">
                            {#each getWrongWords() as word}
                                <div
                                    class="wrong-word-item flex items-center justify-between p-3 bg-srs-again/10 rounded-md border border-srs-again/20"
                                >
                                    <span
                                        class="font-medium text-content-primary"
                                        >{word.lemma}</span
                                    >
                                    <span
                                        class="text-sm text-content-secondary truncate ml-3 max-w-[60%]"
                                        >{word.definition}</span
                                    >
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}

                <div class="results-actions flex flex-col gap-3">
                    {#if getWrongWords().length > 0}
                        <button
                            type="button"
                            class="action-btn px-5 py-3 border border-srs-hard text-srs-hard font-medium rounded-md hover:bg-srs-hard/10 transition-colors"
                            onclick={handleRetryIncorrect}
                        >
                            再練一次答錯的
                        </button>
                    {/if}
                    <button
                        type="button"
                        class="action-btn px-5 py-3 bg-accent text-white font-medium rounded-md hover:opacity-90 transition-opacity"
                        onclick={handleRestart}
                    >
                        繼續練習
                    </button>
                </div>
            </div>
        </div>
    {:else if quiz.isActive && quiz.currentQuestion}
        <div class="quiz-session flex flex-col h-full">
            <div class="progress-bar h-1 bg-surface-secondary">
                <div
                    class="progress-fill h-full bg-accent transition-all duration-300"
                    style="width: {getProgressPercent()}%"
                ></div>
            </div>

            <div class="flex-1 flex flex-col max-w-2xl mx-auto w-full p-5">
                <div class="flex items-center justify-between mb-4">
                    <span class="text-sm text-content-tertiary hidden sm:block">
                        {quiz.progress.current} / {quiz.progress.total}
                    </span>
                    <button
                        type="button"
                        class="text-sm text-content-tertiary hover:text-content-secondary transition-colors"
                        onclick={handleRestart}
                    >
                        退出
                    </button>
                </div>

                <div class="question-card flex-1 flex flex-col">
                    {#if isChoiceQuestion(quiz.currentQuestion.type)}
                        {#if quiz.currentQuestion.type === "fill_blank" || quiz.currentQuestion.type === "distinction"}
                            <div
                                class="sentence-box bg-surface-secondary rounded-lg p-4 mb-4"
                            >
                                <p
                                    class="text-base text-content-primary leading-relaxed"
                                >
                                    {quiz.currentQuestion.sentence_context ||
                                        quiz.currentQuestion.prompt}
                                </p>
                                {#if quiz.currentQuestion.exam_source}
                                    <p
                                        class="text-xs text-content-tertiary mt-2"
                                    >
                                        {quiz.currentQuestion.exam_source.year}{quiz
                                            .currentQuestion.exam_source
                                            .exam_type}
                                    </p>
                                {/if}
                            </div>

                            {#if quiz.currentQuestion.hint}
                                <button
                                    type="button"
                                    class="hint-btn text-sm text-accent mb-4 self-start"
                                    onclick={handleShowHint}
                                >
                                    {showHint ? "提示：" : "看提示"}
                                </button>
                                {#if showHint}
                                    <p
                                        class="hint text-sm text-content-secondary mb-4 -mt-2"
                                    >
                                        {quiz.currentQuestion.hint}
                                    </p>
                                {/if}
                            {/if}
                        {:else}
                            <div class="word-display text-center mb-6">
                                {#if quiz.currentQuestion.type === "recognition"}
                                    <span
                                        class="word-text text-3xl font-semibold text-content-primary"
                                    >
                                        {quiz.currentQuestion.prompt}
                                    </span>
                                    <AudioButton
                                        text={quiz.currentQuestion.lemma}
                                        size="lg"
                                        class="ml-3"
                                    />
                                {:else}
                                    <p
                                        class="text-lg text-content-primary mb-2"
                                    >
                                        {quiz.currentQuestion.prompt}
                                    </p>
                                    {#if quiz.currentQuestion.hint}
                                        <p
                                            class="text-sm text-content-tertiary"
                                        >
                                            {quiz.currentQuestion.hint}
                                        </p>
                                    {/if}
                                {/if}
                            </div>

                            <p class="instruction text-sm text-content-tertiary mb-4 text-center">
                                {quiz.currentQuestion.type === "recognition"
                                    ? "選出正確的意思"
                                    : "選出正確的單字"}
                            </p>
                        {/if}

                        <div class="options flex-1 flex flex-col gap-3">
                            {#each quiz.currentQuestion.options || [] as option, i}
                                {@const isCorrectOption =
                                    option.value.toLowerCase() ===
                                    quiz.currentQuestion.correct.toLowerCase()}
                                {@const isSelectedOption =
                                    selectedAnswer?.toLowerCase() ===
                                    option.value.toLowerCase()}
                                <button
                                    type="button"
                                    class="option p-4 text-left rounded-lg border transition-all min-h-[52px]"
                                    class:option-correct={showFeedback &&
                                        isCorrectOption}
                                    class:option-incorrect={showFeedback &&
                                        isSelectedOption &&
                                        !isCorrectOption}
                                    class:option-selected={!showFeedback &&
                                        isSelectedOption}
                                    onclick={() =>
                                        handleChoiceSelect(option.value)}
                                    disabled={showFeedback}
                                >
                                    <span
                                        class="hidden sm:inline-block text-xs text-content-tertiary mr-2"
                                    >
                                        按 {i + 1}
                                    </span>
                                    <span class="text-content-primary"
                                        >{option.label}</span
                                    >
                                </button>
                            {/each}
                        </div>
                    {:else if isTypingQuestion(quiz.currentQuestion.type)}
                        <div class="spelling-prompt text-center mb-6">
                            <AudioButton
                                text={quiz.currentQuestion.lemma}
                                size="lg"
                                class="mb-4"
                            />
                            <p class="text-lg text-content-primary">
                                {quiz.currentQuestion.prompt}
                            </p>
                            {#if quiz.currentQuestion.hint}
                                <p class="text-sm text-content-tertiary mt-1">
                                    {quiz.currentQuestion.hint}
                                </p>
                            {/if}
                        </div>

                        <div class="answer-area flex justify-center gap-2 mb-6">
                            {#each answerSlots as letter, i}
                                <button
                                    type="button"
                                    class="answer-slot w-10 h-12 border-2 rounded-md flex items-center justify-center text-lg font-medium transition-all"
                                    class:answer-slot-filled={letter}
                                    onclick={() => removeLetterAt(i)}
                                    disabled={showFeedback}
                                >
                                    {letter || ""}
                                </button>
                            {/each}
                        </div>

                        <div
                            class="letter-tiles flex flex-wrap justify-center gap-2 mb-6"
                        >
                            {#each shuffledLetters as letter, i}
                                <button
                                    type="button"
                                    class="letter-tile w-10 h-10 rounded-md flex items-center justify-center text-lg font-medium transition-all"
                                    class:letter-tile-used={usedIndices.has(i)}
                                    onclick={() => selectLetter(i)}
                                    disabled={usedIndices.has(i) || showFeedback}
                                >
                                    {letter}
                                </button>
                            {/each}
                        </div>

                        {#if !showFeedback}
                            <button
                                type="button"
                                class="check-btn w-full px-4 py-3 bg-accent text-white font-medium rounded-md hover:opacity-90 transition-opacity disabled:opacity-50"
                                onclick={handleSpellingSubmit}
                                disabled={!isSpellingComplete()}
                            >
                                確認
                            </button>
                        {/if}
                    {/if}
                </div>

                {#if showFeedback}
                    {@const isCorrect = isAnswerCorrect(quiz.currentIndex)}
                    <div
                        class="feedback-sheet mt-4 p-4 rounded-lg"
                        class:feedback-correct={isCorrect}
                        class:feedback-incorrect={!isCorrect}
                    >
                        <div class="feedback-content flex items-center gap-3 mb-3">
                            <span class="feedback-icon text-2xl">
                                {isCorrect ? "✓" : "✗"}
                            </span>
                            {#if isCorrect}
                                <span class="feedback-text font-medium"
                                    >正確！</span
                                >
                            {:else}
                                <div class="feedback-detail">
                                    <span
                                        class="feedback-text text-sm text-content-secondary"
                                        >正確答案</span
                                    >
                                    <span
                                        class="feedback-answer block font-semibold text-lg"
                                    >
                                        {quiz.currentQuestion.correct}
                                    </span>
                                </div>
                            {/if}
                        </div>

                        {#if !isCorrect && quiz.currentQuestion.explanation?.memory_tip}
                            <p class="feedback-tip text-sm mb-3">
                                💡 {quiz.currentQuestion.explanation.memory_tip}
                            </p>
                        {/if}

                        <button
                            type="button"
                            class="continue-btn w-full px-4 py-3 font-medium rounded-md transition-opacity"
                            onclick={handleNextQuestion}
                        >
                            繼續
                        </button>
                    </div>
                {/if}
            </div>
        </div>
    {:else}
        <div class="quiz-start-page flex flex-col items-center justify-center min-h-full p-5">
            <div class="max-w-md w-full">
                <div class="quiz-hero text-center mb-8">
                    <div class="quiz-hero-icon text-5xl mb-4">📝</div>
                    <h1
                        class="quiz-hero-title text-2xl font-semibold text-content-primary mb-2"
                    >
                        單字練習
                    </h1>
                    <p class="quiz-hero-subtitle text-content-secondary">
                        {availableCount} 個單字等你挑戰
                    </p>
                </div>

                <div class="quiz-quick-stats flex justify-center gap-8 mb-8">
                    <div class="quick-stat text-center">
                        <span
                            class="quick-stat-number text-2xl font-semibold text-accent block"
                            >{dueCount}</span
                        >
                        <span class="quick-stat-label text-sm text-content-secondary"
                            >該複習了</span
                        >
                    </div>
                    <div class="quick-stat text-center">
                        <span
                            class="quick-stat-number text-2xl font-semibold text-srs-hard block"
                            >{weakCount}</span
                        >
                        <span class="quick-stat-label text-sm text-content-secondary"
                            >需要加強</span
                        >
                    </div>
                </div>

                <button
                    type="button"
                    class="quiz-start-btn w-full px-6 py-4 bg-accent text-white text-lg font-semibold rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 mb-6"
                    onclick={handleStartQuiz}
                    disabled={availableCount === 0}
                >
                    開始練習
                </button>

                <button
                    type="button"
                    class="quiz-settings-toggle w-full flex items-center justify-center gap-2 text-content-tertiary hover:text-content-secondary transition-colors py-2"
                    onclick={() => (showSettings = !showSettings)}
                >
                    <span>進階設定</span>
                    <svg
                        class="w-4 h-4 transition-transform"
                        class:rotate-180={showSettings}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M19 9l-7 7-7-7"
                        />
                    </svg>
                </button>

                {#if showSettings}
                    <div
                        class="quiz-settings bg-surface-primary rounded-lg border border-border p-5 mt-4 space-y-5"
                    >
                        <div class="setting-section">
                            <span
                                class="setting-label text-sm font-medium text-content-secondary block mb-3"
                                >題目來源</span
                            >
                            <div class="space-y-2">
                                <label class="source-option flex items-start gap-3 p-3 rounded-md border transition-colors cursor-pointer"
                                    class:source-option-selected={quizSource === "srs_due"}
                                >
                                    <input
                                        type="radio"
                                        name="quiz-source"
                                        value="srs_due"
                                        bind:group={quizSource}
                                        class="mt-0.5"
                                    />
                                    <div class="flex-1">
                                        <div class="font-medium text-content-primary text-sm">智慧推薦</div>
                                        <div class="text-xs text-content-tertiary mt-0.5">根據遺忘曲線自動選擇需要複習的單字</div>
                                    </div>
                                </label>
                                <label class="source-option flex items-start gap-3 p-3 rounded-md border transition-colors cursor-pointer"
                                    class:source-option-selected={quizSource === "today_studied"}
                                >
                                    <input
                                        type="radio"
                                        name="quiz-source"
                                        value="today_studied"
                                        bind:group={quizSource}
                                        class="mt-0.5"
                                    />
                                    <div class="flex-1">
                                        <div class="font-medium text-content-primary text-sm">今日學習</div>
                                        <div class="text-xs text-content-tertiary mt-0.5">複習今天在 Flashcard 學過的單字</div>
                                    </div>
                                </label>
                                <label class="source-option flex items-start gap-3 p-3 rounded-md border transition-colors cursor-pointer"
                                    class:source-option-selected={quizSource === "srs_weak"}
                                >
                                    <input
                                        type="radio"
                                        name="quiz-source"
                                        value="srs_weak"
                                        bind:group={quizSource}
                                        class="mt-0.5"
                                    />
                                    <div class="flex-1">
                                        <div class="font-medium text-content-primary text-sm">困難單字</div>
                                        <div class="text-xs text-content-tertiary mt-0.5">按錯次數較多或標記為困難的單字</div>
                                    </div>
                                </label>
                            </div>
                        </div>

                        <div class="setting-section">
                            <span
                                class="setting-label text-sm font-medium text-content-secondary block mb-2"
                                >題數</span
                            >
                            <div class="pill-group flex gap-2">
                                {#each [10, 20, 30] as count}
                                    <button
                                        type="button"
                                        class="pill px-4 py-2 rounded-md text-sm font-medium transition-all"
                                        class:pill-active={questionCount ===
                                            count}
                                        onclick={() => (questionCount = count)}
                                    >
                                        {count}
                                    </button>
                                {/each}
                            </div>
                        </div>

                        <div class="setting-section">
                            <span
                                class="setting-label text-sm font-medium text-content-secondary block mb-2"
                                >範圍</span
                            >
                            <div class="pill-group flex gap-2">
                                <button
                                    type="button"
                                    class="pill px-4 py-2 rounded-md text-sm font-medium transition-all"
                                    class:pill-active={entryType === "all"}
                                    onclick={() => (entryType = "all")}
                                >
                                    全部
                                </button>
                                <button
                                    type="button"
                                    class="pill px-4 py-2 rounded-md text-sm font-medium transition-all"
                                    class:pill-active={entryType === "word"}
                                    onclick={() => (entryType = "word")}
                                >
                                    單字
                                </button>
                                <button
                                    type="button"
                                    class="pill px-4 py-2 rounded-md text-sm font-medium transition-all"
                                    class:pill-active={entryType === "phrase"}
                                    onclick={() => (entryType = "phrase")}
                                >
                                    片語
                                </button>
                            </div>
                        </div>
                    </div>
                {/if}
            </div>
        </div>
    {/if}
</div>

<style>
    .option {
        border-color: var(--color-border);
        background-color: var(--color-surface-primary);
    }

    .option:hover:not(:disabled) {
        border-color: var(--color-border-hover);
        background-color: var(--color-surface-hover);
    }

    .option-selected {
        border-color: var(--color-accent);
        background-color: var(--color-accent-soft);
    }

    .option-correct {
        border-color: var(--color-srs-good);
        background-color: var(--color-srs-good-soft);
    }

    .option-incorrect {
        border-color: var(--color-srs-again);
        background-color: var(--color-srs-again-soft);
    }

    .option:disabled {
        cursor: default;
    }

    .pill {
        background-color: var(--color-surface-page);
        color: var(--color-content-secondary);
        border: 1px solid var(--color-border);
    }

    .pill:hover {
        background-color: var(--color-surface-hover);
    }

    .pill-active {
        background-color: var(--color-accent-soft);
        color: var(--color-accent);
        border-color: transparent;
    }

    .source-option {
        border-color: var(--color-border);
        background-color: var(--color-surface-page);
    }

    .source-option:hover {
        border-color: var(--color-border-hover);
        background-color: var(--color-surface-hover);
    }

    .source-option-selected {
        border-color: var(--color-accent);
        background-color: var(--color-accent-soft);
    }

    .source-option input[type="radio"] {
        accent-color: var(--color-accent);
    }

    .answer-slot {
        border-color: var(--color-border);
        background-color: var(--color-surface-primary);
    }

    .answer-slot-filled {
        border-color: var(--color-accent);
        background-color: var(--color-accent-soft);
        color: var(--color-accent);
    }

    .letter-tile {
        background-color: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        color: var(--color-content-primary);
    }

    .letter-tile:hover:not(:disabled) {
        background-color: var(--color-surface-hover);
        border-color: var(--color-border-hover);
    }

    .letter-tile-used {
        opacity: 0.3;
    }

    .feedback-correct {
        background-color: var(--color-srs-good-soft);
    }

    .feedback-correct .feedback-icon,
    .feedback-correct .feedback-text {
        color: var(--color-srs-good);
    }

    .feedback-correct .continue-btn {
        background-color: var(--color-srs-good);
        color: white;
    }

    .feedback-correct .continue-btn:hover {
        opacity: 0.9;
    }

    .feedback-incorrect {
        background-color: var(--color-srs-again-soft);
    }

    .feedback-incorrect .feedback-icon {
        color: var(--color-srs-again);
    }

    .feedback-incorrect .feedback-answer {
        color: var(--color-srs-again);
    }

    .feedback-incorrect .continue-btn {
        background-color: var(--color-srs-again);
        color: white;
    }

    .feedback-incorrect .continue-btn:hover {
        opacity: 0.9;
    }

    .feedback-tip {
        color: var(--color-content-secondary);
    }

    @media (prefers-reduced-motion: reduce) {
        .progress-fill {
            transition: none;
        }
    }
</style>
