<script lang="ts">
    import {
        getQuizStore,
        startQuiz,
        submitAnswer,
        nextQuestion,
        resetQuiz,
        retryIncorrect,
        isAnswerCorrect,
        getCurrentAnswer,
        type QuizConfig,
    } from "$lib/stores/quiz.svelte";
    import { getVocabStore, getFilters } from "$lib/stores/vocab.svelte";
    import { speakText } from "$lib/tts";

    const quiz = getQuizStore();
    const vocab = getVocabStore();
    const filters = getFilters();

    let quizCount = $state(10);
    let selectedPos = $state<Set<string>>(new Set());
    let excludePropn = $state(true);
    let freqMin = $state(1);
    let freqMax = $state(20);
    let choiceDirection = $state<"word_to_def" | "def_to_word">("word_to_def");
    let spellingInput = $state("");
    let showFeedback = $state(false);
    let audioPlayer: HTMLAudioElement | null = null;

    const posOptions = ["NOUN", "VERB", "ADJ", "ADV"];
    const posLabels: Record<string, string> = {
        NOUN: "名詞",
        VERB: "動詞",
        ADJ: "形容詞",
        ADV: "副詞",
    };

    function togglePos(pos: string) {
        const newSet = new Set(selectedPos);
        if (newSet.has(pos)) {
            newSet.delete(pos);
        } else {
            newSet.add(pos);
        }
        selectedPos = newSet;
    }

    async function handleStartQuiz(type: "choice" | "spelling" | "fill") {
        const config: QuizConfig = {
            type,
            count: quizCount,
            freqMin,
            freqMax,
            excludePropn,
        };

        if (selectedPos.size > 0) {
            config.pos = Array.from(selectedPos);
        }

        if (type === "choice") {
            config.choiceDirection = choiceDirection;
        }

        await startQuiz(config);
        spellingInput = "";
        showFeedback = false;
    }

    function handleChoiceSelect(value: string) {
        if (showFeedback) return;
        submitAnswer(value);
        showFeedback = true;
    }

    function handleSpellingSubmit() {
        if (showFeedback || !spellingInput.trim()) return;
        submitAnswer(spellingInput.trim());
        showFeedback = true;
    }

    function handleNextQuestion() {
        nextQuestion();
        spellingInput = "";
        showFeedback = false;
    }

    function handleRestart() {
        resetQuiz();
        showFeedback = false;
        spellingInput = "";
    }

    async function handleRetryIncorrect() {
        await retryIncorrect();
        showFeedback = false;
        spellingInput = "";
    }

    async function playAudio(lemma: string) {
        try {
            const url = await speakText(lemma);
            if (!audioPlayer) {
                audioPlayer = new Audio();
            }
            audioPlayer.src = url;
            await audioPlayer.play();
        } catch {
            // ignore audio playback errors
        }
    }

    function getOptionClass(
        option: { value: string },
        currentAnswer: string | null,
    ): string {
        if (!showFeedback) return "";

        const q = quiz.currentQuestion;
        if (!q) return "";

        if (option.value.toLowerCase() === q.correct.toLowerCase()) {
            return "correct";
        }
        if (
            currentAnswer &&
            option.value.toLowerCase() === currentAnswer.toLowerCase()
        ) {
            return "incorrect";
        }
        return "";
    }

    $effect(() => {
        freqMin = filters.freqMin;
        freqMax = filters.freqMax;
    });
</script>

<div class="quiz-view h-full overflow-y-auto bg-surface-page p-5 sm:p-8">
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
        <div
            class="max-w-2xl mx-auto bg-surface-primary border border-srs-again/30 rounded-lg p-6 text-center"
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
    {:else if quiz.isComplete}
        <div
            class="max-w-2xl mx-auto bg-surface-primary rounded-lg border border-border p-6 lg:p-8"
        >
            <h2
                class="text-xl lg:text-2xl font-semibold tracking-tight text-content-primary mb-6 text-center"
            >
                測驗結果
            </h2>

            <div class="text-center mb-8">
                <div
                    class="text-5xl lg:text-6xl font-semibold text-accent mb-2 tracking-tight"
                >
                    {Math.round((quiz.score / quiz.questions.length) * 100)}%
                </div>
                <p class="text-content-secondary text-sm">
                    {quiz.score} / {quiz.questions.length} 題正確
                </p>
            </div>

            {#if quiz.incorrectQuestions.length > 0}
                <div class="mb-8">
                    <h3 class="text-base font-medium text-content-primary mb-3">
                        需要複習的單字
                    </h3>
                    <div class="space-y-2">
                        {#each quiz.incorrectQuestions as q}
                            <div
                                class="flex items-center justify-between p-3 bg-srs-again/10 rounded-md border border-srs-again/20"
                            >
                                <span class="font-medium text-content-primary"
                                    >{q.lemma || q.correct}</span
                                >
                                <span class="text-sm text-content-secondary"
                                    >{q.correct}</span
                                >
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}

            <div class="flex flex-wrap gap-3 justify-center">
                <button
                    type="button"
                    class="px-5 py-2.5 bg-content-primary text-white rounded-md hover:opacity-90 transition-opacity text-sm font-medium"
                    onclick={handleRestart}
                >
                    重新測驗
                </button>
                {#if quiz.incorrectQuestions.length > 0}
                    <button
                        type="button"
                        class="px-5 py-2.5 bg-srs-hard text-white rounded-md hover:opacity-90 transition-opacity text-sm font-medium"
                        onclick={handleRetryIncorrect}
                    >
                        只測錯誤題
                    </button>
                {/if}
            </div>
        </div>
    {:else if quiz.isActive && quiz.currentQuestion}
        <div class="max-w-2xl mx-auto">
            <div class="flex items-center justify-between mb-5">
                <span class="text-sm text-content-tertiary">
                    題目 {quiz.progress.current} / {quiz.progress.total}
                </span>
                <button
                    type="button"
                    class="text-sm text-content-tertiary hover:text-content-secondary transition-colors"
                    onclick={handleRestart}
                >
                    退出測驗
                </button>
            </div>

            <div class="bg-surface-primary rounded-lg border border-border p-6">
                <div class="mb-6">
                    {#if quiz.currentQuestion.lemma && (quiz.type === "spelling" || quiz.type === "fill")}
                        <button
                            type="button"
                            class="mb-4 p-2.5 rounded-md hover:bg-surface-hover transition-colors"
                            onclick={() =>
                                playAudio(quiz.currentQuestion!.lemma!)}
                            title="播放發音"
                        >
                            <svg
                                class="w-7 h-7 text-accent"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="1.5"
                                stroke="currentColor"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1
 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
                                />
                            </svg>
                        </button>
                    {/if}
                    <p class="text-lg text-content-primary">
                        {quiz.currentQuestion.prompt}
                    </p>
                </div>

                {#if quiz.type === "choice" && quiz.currentQuestion.options}
                    <div class="space-y-2.5">
                        {#each quiz.currentQuestion.options as option, i}
                            {@const currentAnswer = getCurrentAnswer()}
                            <button
                                type="button"
                                class="quiz-option w-full p-4 text-left rounded-md border transition-all {getOptionClass(
                                    option,
                                    currentAnswer,
                                )}"
                                class:selected={currentAnswer ===
                                    option.value && !showFeedback}
                                onclick={() => handleChoiceSelect(option.value)}
                                disabled={showFeedback}
                            >
                                <span
                                    class="font-medium text-content-tertiary mr-2"
                                    >{String.fromCharCode(65 + i)}.</span
                                >
                                <span class="text-content-primary"
                                    >{option.label}</span
                                >
                            </button>
                        {/each}
                    </div>
                {:else if quiz.type === "spelling" || quiz.type === "fill"}
                    <div class="space-y-4">
                        <input
                            type="text"
                            bind:value={spellingInput}
                            placeholder="輸入答案..."
                            class="w-full px-4 py-3 text-base"
                            disabled={showFeedback}
                            onkeydown={(e) =>
                                e.key === "Enter" && handleSpellingSubmit()}
                        />

                        {#if !showFeedback}
                            <button
                                type="button"
                                class="w-full px-4 py-3 bg-content-primary text-white font-medium rounded-md hover:opacity-90 transition-opacity disabled:opacity-50"
                                onclick={handleSpellingSubmit}
                                disabled={!spellingInput.trim()}
                            >
                                提交答案
                            </button>
                        {/if}
                    </div>
                {/if}

                {#if showFeedback}
                    {@const isCorrect = isAnswerCorrect(quiz.currentIndex)}
                    <div
                        class="mt-6 p-4 rounded-md {isCorrect
                            ? 'bg-srs-good/10 border border-srs-good/30'
                            : 'bg-srs-again/10 border border-srs-again/30'}"
                    >
                        <p
                            class="font-medium {isCorrect
                                ? 'text-srs-good'
                                : 'text-srs-again'}"
                        >
                            {isCorrect ? "✓ 正確！" : "✗ 錯誤"}
                        </p>
                        {#if !isCorrect}
                            <p class="mt-1 text-content-secondary text-sm">
                                正確答案：<span
                                    class="font-medium text-content-primary"
                                    >{quiz.currentQuestion.correct}</span
                                >
                            </p>
                        {/if}
                    </div>

                    <button
                        type="button"
                        class="mt-4 w-full px-4 py-3 bg-surface-page text-content-primary font-medium rounded-md hover:bg-surface-hover border border-border transition-colors"
                        onclick={handleNextQuestion}
                    >
                        {quiz.currentIndex < quiz.questions.length - 1
                            ? "下一題"
                            : "查看結果"}
                    </button>
                {/if}
            </div>
        </div>
    {:else}
        <div class="max-w-4xl mx-auto">
            <h2
                class="text-2xl lg:text-3xl font-semibold tracking-tight text-content-primary mb-6"
            >
                選擇測驗模式
            </h2>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <button
                    type="button"
                    class="quiz-type-card group"
                    onclick={() => handleStartQuiz("choice")}
                >
                    <div
                        class="w-10 h-10 rounded-md bg-accent-soft flex items-center justify-center mb-3"
                    >
                        <svg
                            class="w-5 h-5 text-accent"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
                            />
                        </svg>
                    </div>
                    <h3
                        class="text-base font-semibold text-content-primary mb-1.5"
                    >
                        選擇題測驗
                    </h3>
                    <p class="text-sm text-content-secondary">
                        給定義選單詞，或給單詞選定義
                    </p>
                </button>

                <button
                    type="button"
                    class="quiz-type-card group"
                    onclick={() => handleStartQuiz("spelling")}
                >
                    <div
                        class="w-10 h-10 rounded-md bg-accent-soft flex items-center justify-center mb-3"
                    >
                        <svg
                            class="w-5 h-5 text-accent"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
                            />
                        </svg>
                    </div>
                    <h3
                        class="text-base font-semibold text-content-primary mb-1.5"
                    >
                        拼寫測驗
                    </h3>
                    <p class="text-sm text-content-secondary">
                        看定義後拼寫單詞
                    </p>
                </button>

                <button
                    type="button"
                    class="quiz-type-card group"
                    onclick={() => handleStartQuiz("fill")}
                >
                    <div
                        class="w-10 h-10 rounded-md bg-accent-soft flex items-center justify-center mb-3"
                    >
                        <svg
                            class="w-5 h-5 text-accent"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
                            />
                        </svg>
                    </div>
                    <h3
                        class="text-base font-semibold text-content-primary mb-1.5"
                    >
                        填空測驗
                    </h3>
                    <p class="text-sm text-content-secondary">
                        從例句中填入正確的單詞
                    </p>
                </button>
            </div>

            <div
                class="bg-surface-primary rounded-lg border border-border p-6 space-y-5"
            >
                <div>
                    <label
                        for="quiz-count"
                        class="block text-sm font-medium text-content-secondary mb-2"
                        >題目數量</label
                    >
                    <input
                        id="quiz-count"
                        type="number"
                        min="1"
                        max="50"
                        bind:value={quizCount}
                        class="w-full px-3.5 py-2.5 text-sm"
                    />
                </div>

                <div>
                    <span
                        class="block text-sm font-medium text-content-secondary mb-2.5"
                        >選擇題方向</span
                    >
                    <div class="flex flex-wrap gap-4">
                        <label
                            class="inline-flex items-center gap-2.5 cursor-pointer"
                        >
                            <input
                                type="radio"
                                name="choice-direction"
                                value="word_to_def"
                                bind:group={choiceDirection}
                            />
                            <span class="text-sm text-content-primary"
                                >單字考定義</span
                            >
                        </label>
                        <label
                            class="inline-flex items-center gap-2.5 cursor-pointer"
                        >
                            <input
                                type="radio"
                                name="choice-direction"
                                value="def_to_word"
                                bind:group={choiceDirection}
                            />
                            <span class="text-sm text-content-primary"
                                >定義考單字</span
                            >
                        </label>
                    </div>
                </div>

                <div>
                    <span
                        class="block text-sm font-medium text-content-secondary mb-2.5"
                        >詞性篩選</span
                    >
                    <div class="flex flex-wrap gap-2">
                        <button
                            type="button"
                            class="pos-chip"
                            class:active={selectedPos.size === 0}
                            onclick={() => (selectedPos = new Set())}
                        >
                            全部
                        </button>
                        {#each posOptions as pos}
                            <button
                                type="button"
                                class="pos-chip"
                                class:active={selectedPos.has(pos)}
                                onclick={() => togglePos(pos)}
                            >
                                {posLabels[pos] || pos}
                            </button>
                        {/each}
                    </div>
                </div>

                <div>
                    <span
                        class="block text-sm font-medium text-content-secondary mb-2"
                        >頻率範圍</span
                    >
                    <div class="flex gap-3 items-center">
                        <input
                            type="number"
                            min={vocab.freqRange.min}
                            max={vocab.freqRange.max}
                            bind:value={freqMin}
                            class="flex-1 px-3 py-2 text-sm"
                            placeholder="最小"
                        />
                        <span class="text-content-tertiary text-sm">至</span>
                        <input
                            type="number"
                            min={vocab.freqRange.min}
                            max={vocab.freqRange.max}
                            bind:value={freqMax}
                            class="flex-1 px-3 py-2 text-sm"
                            placeholder="最大"
                        />
                    </div>
                </div>

                <div>
                    <label
                        class="flex items-center gap-2.5 cursor-pointer group"
                    >
                        <input type="checkbox" bind:checked={excludePropn} />
                        <span
                            class="text-sm text-content-secondary group-hover:text-content-primary transition-colors"
                            >排除專有名詞</span
                        >
                    </label>
                </div>
            </div>
        </div>
    {/if}
</div>

<style>
    .quiz-option {
        border-color: var(--color-border);
        background-color: var(--color-surface-primary);
    }

    .quiz-option:hover:not(:disabled) {
        border-color: var(--color-border-hover);
        background-color: var(--color-surface-hover);
    }

    .quiz-option.selected {
        border-color: var(--color-accent);
        background-color: var(--color-accent-soft);
    }

    .quiz-option.correct {
        border-color: var(--color-srs-good);
        background-color: var(--color-srs-good-soft);
    }

    .quiz-option.incorrect {
        border-color: var(--color-srs-again);
        background-color: var(--color-srs-again-soft);
    }

    .quiz-option:disabled {
        cursor: default;
    }

    .pos-chip {
        padding: 0.375rem 0.75rem;
        background-color: var(--color-surface-page);
        border-radius: 6px;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--color-content-secondary);
        transition: all 0.15s ease;
        cursor: pointer;
        border: 1px solid transparent;
    }

    .pos-chip:hover {
        background-color: var(--color-surface-hover);
        border-color: var(--color-border);
    }

    .pos-chip.active {
        background-color: var(--color-accent-soft);
        color: var(--color-accent);
        border-color: transparent;
    }

    .quiz-type-card {
        padding: 1.25rem;
        background-color: var(--color-surface-primary);
        border-radius: 8px;
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-card);
        text-align: left;
        transition: all 0.15s ease;
        cursor: pointer;
    }

    .quiz-type-card:hover {
        border-color: var(--color-border-hover);
        background-color: var(--color-surface-secondary);
        box-shadow: var(--shadow-card-hover);
    }

    .quiz-type-card:focus-visible {
        outline: none;
        box-shadow: 0 0 0 2px var(--color-surface-primary), 0 0 0 4px var(--color-accent);
    }
</style>
