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
    type QuizConfig
  } from '$lib/stores/quiz.svelte';
  import { getVocabStore, getFilters } from '$lib/stores/vocab.svelte';
  import { getAudioUrl } from '$lib/api';

  const quiz = getQuizStore();
  const vocab = getVocabStore();
  const filters = getFilters();

  let quizCount = $state(10);
  let selectedPos = $state<Set<string>>(new Set());
  let excludePropn = $state(true);
  let freqMin = $state(1);
  let freqMax = $state(20);
  let choiceDirection = $state<'word_to_def' | 'def_to_word'>('word_to_def');
  let spellingInput = $state('');
  let showFeedback = $state(false);
  let audioPlayer: HTMLAudioElement | null = null;

  const posOptions = ['NOUN', 'VERB', 'ADJ', 'ADV'];

  function togglePos(pos: string) {
    const newSet = new Set(selectedPos);
    if (newSet.has(pos)) {
      newSet.delete(pos);
    } else {
      newSet.add(pos);
    }
    selectedPos = newSet;
  }

  async function handleStartQuiz(type: 'choice' | 'spelling' | 'fill') {
    const config: QuizConfig = {
      type,
      count: quizCount,
      freqMin,
      freqMax,
      excludePropn
    };

    if (selectedPos.size > 0) {
      config.pos = Array.from(selectedPos);
    }

    if (type === 'choice') {
      config.choiceDirection = choiceDirection;
    }

    await startQuiz(config);
    spellingInput = '';
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
    spellingInput = '';
    showFeedback = false;
  }

  function handleRestart() {
    resetQuiz();
    showFeedback = false;
    spellingInput = '';
  }

  async function handleRetryIncorrect() {
    await retryIncorrect();
    showFeedback = false;
    spellingInput = '';
  }

  function playAudio(lemma: string) {
    if (!audioPlayer) {
      audioPlayer = new Audio();
    }
    audioPlayer.src = getAudioUrl(lemma);
    audioPlayer.play().catch(() => {});
  }

  function getOptionClass(option: { value: string }, currentAnswer: string | null): string {
    if (!showFeedback) return '';

    const q = quiz.currentQuestion;
    if (!q) return '';

    if (option.value.toLowerCase() === q.correct.toLowerCase()) {
      return 'correct';
    }
    if (currentAnswer && option.value.toLowerCase() === currentAnswer.toLowerCase()) {
      return 'incorrect';
    }
    return '';
  }

  $effect(() => {
    freqMin = filters.freqMin;
    freqMax = filters.freqMax;
  });
</script>

<div class="quiz-view h-full overflow-y-auto bg-slate-50 p-4 sm:p-8">
  {#if quiz.isLoading}
    <div class="flex items-center justify-center h-full">
      <div class="text-center">
        <svg class="w-12 h-12 animate-spin text-indigo-600 mx-auto mb-4" viewBox="0 0 24 24" fill="none">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="text-slate-600">正在生成測驗...</p>
      </div>
    </div>

  {:else if quiz.error}
    <div class="max-w-2xl mx-auto bg-red-50 border border-red-200 rounded-lg p-6 text-center">
      <p class="text-red-600 mb-4">{quiz.error}</p>
      <button
        type="button"
        class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        onclick={handleRestart}
      >
        返回
      </button>
    </div>

  {:else if quiz.isComplete}
    <div class="max-w-2xl mx-auto bg-white rounded-xl shadow-lg p-6">
      <h2 class="text-2xl font-bold text-slate-800 mb-6 text-center">測驗結果</h2>

      <div class="text-center mb-8">
        <div class="text-6xl font-bold text-indigo-600 mb-2">
          {Math.round((quiz.score / quiz.questions.length) * 100)}%
        </div>
        <p class="text-slate-600">
          {quiz.score} / {quiz.questions.length} 題正確
        </p>
      </div>

      {#if quiz.incorrectQuestions.length > 0}
        <div class="mb-8">
          <h3 class="text-lg font-semibold text-slate-800 mb-4">需要複習的單字</h3>
          <div class="space-y-2">
            {#each quiz.incorrectQuestions as q, i}
              <div class="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                <span class="font-medium text-slate-800">{q.lemma || q.correct}</span>
                <span class="text-sm text-slate-500">{q.correct}</span>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <div class="flex flex-wrap gap-3 justify-center">
        <button
          type="button"
          class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          onclick={handleRestart}
        >
          重新測驗
        </button>
        {#if quiz.incorrectQuestions.length > 0}
          <button
            type="button"
            class="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
            onclick={handleRetryIncorrect}
          >
            只測錯誤題
          </button>
        {/if}
      </div>
    </div>

  {:else if quiz.isActive && quiz.currentQuestion}
    <div class="max-w-2xl mx-auto">
      <div class="flex items-center justify-between mb-6">
        <span class="text-sm text-slate-500">
          題目 {quiz.progress.current} / {quiz.progress.total}
        </span>
        <button
          type="button"
          class="text-sm text-slate-500 hover:text-slate-700"
          onclick={handleRestart}
        >
          退出測驗
        </button>
      </div>

      <div class="bg-white rounded-xl shadow-lg p-6">
        <div class="mb-6">
          {#if quiz.currentQuestion.lemma && (quiz.type === 'spelling' || quiz.type === 'fill')}
            <button
              type="button"
              class="mb-4 p-2 rounded-full hover:bg-slate-100 transition-colors"
              onclick={() => playAudio(quiz.currentQuestion!.lemma!)}
              title="播放發音"
            >
              <svg class="w-8 h-8 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" />
              </svg>
            </button>
          {/if}
          <p class="text-xl text-slate-800">{quiz.currentQuestion.prompt}</p>
        </div>

        {#if quiz.type === 'choice' && quiz.currentQuestion.options}
          <div class="space-y-3">
            {#each quiz.currentQuestion.options as option, i}
              {@const currentAnswer = getCurrentAnswer()}
              <button
                type="button"
                class="quiz-option w-full p-4 text-left rounded-lg border-2 transition-colors {getOptionClass(option, currentAnswer)}"
                class:selected={currentAnswer === option.value && !showFeedback}
                onclick={() => handleChoiceSelect(option.value)}
                disabled={showFeedback}
              >
                <span class="font-medium mr-2">{String.fromCharCode(65 + i)}.</span>
                {option.label}
              </button>
            {/each}
          </div>

        {:else if quiz.type === 'spelling' || quiz.type === 'fill'}
          <div class="space-y-4">
            <input
              type="text"
              bind:value={spellingInput}
              placeholder="輸入答案..."
              class="w-full px-4 py-3 border-2 border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:outline-none text-lg"
              disabled={showFeedback}
              onkeydown={(e) => e.key === 'Enter' && handleSpellingSubmit()}
            />

            {#if !showFeedback}
              <button
                type="button"
                class="w-full px-4 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
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
          <div class="mt-6 p-4 rounded-lg {isCorrect ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}">
            <p class="font-semibold {isCorrect ? 'text-green-700' : 'text-red-700'}">
              {isCorrect ? '✓ 正確！' : '✗ 錯誤'}
            </p>
            {#if !isCorrect}
              <p class="mt-1 text-slate-700">
                正確答案：<span class="font-semibold">{quiz.currentQuestion.correct}</span>
              </p>
            {/if}
          </div>

          <button
            type="button"
            class="mt-4 w-full px-4 py-3 bg-slate-200 text-slate-700 font-semibold rounded-lg hover:bg-slate-300 transition-colors"
            onclick={handleNextQuestion}
          >
            {quiz.currentIndex < quiz.questions.length - 1 ? '下一題' : '查看結果'}
          </button>
        {/if}
      </div>
    </div>

  {:else}
    <div class="max-w-4xl mx-auto">
      <h2 class="text-3xl font-bold text-slate-800 mb-8">選擇測驗模式</h2>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <button
          type="button"
          class="quiz-type-btn p-6 bg-white rounded-lg border-2 border-slate-200 hover:border-indigo-500 transition text-left"
          onclick={() => handleStartQuiz('choice')}
        >
          <h3 class="text-xl font-semibold mb-2">選擇題測驗</h3>
          <p class="text-slate-600">給定義選單詞，或給單詞選定義</p>
        </button>

        <button
          type="button"
          class="quiz-type-btn p-6 bg-white rounded-lg border-2 border-slate-200 hover:border-indigo-500 transition text-left"
          onclick={() => handleStartQuiz('spelling')}
        >
          <h3 class="text-xl font-semibold mb-2">拼寫測驗</h3>
          <p class="text-slate-600">看定義後拼寫單詞</p>
        </button>

        <button
          type="button"
          class="quiz-type-btn p-6 bg-white rounded-lg border-2 border-slate-200 hover:border-indigo-500 transition text-left"
          onclick={() => handleStartQuiz('fill')}
        >
          <h3 class="text-xl font-semibold mb-2">填空測驗</h3>
          <p class="text-slate-600">從例句中填入正確的單詞</p>
        </button>
      </div>

      <div class="bg-white rounded-xl shadow-lg p-6 space-y-6">
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">題目數量</label>
          <input
            type="number"
            min="1"
            max="50"
            bind:value={quizCount}
            class="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">選擇題方向</label>
          <div class="flex flex-wrap gap-4">
            <label class="inline-flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="choice-direction"
                value="word_to_def"
                bind:group={choiceDirection}
                class="w-4 h-4 text-indigo-600"
              />
              <span class="text-sm text-slate-700">單字考定義</span>
            </label>
            <label class="inline-flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="choice-direction"
                value="def_to_word"
                bind:group={choiceDirection}
                class="w-4 h-4 text-indigo-600"
              />
              <span class="text-sm text-slate-700">定義考單字</span>
            </label>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">詞性篩選</label>
          <div class="flex flex-wrap gap-2">
            {#each posOptions as pos}
              <button
                type="button"
                class="pos-chip px-3 py-1.5 rounded-full text-sm font-medium transition-colors"
                class:active={selectedPos.has(pos)}
                onclick={() => togglePos(pos)}
              >
                {pos}
              </button>
            {/each}
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">頻率範圍</label>
          <div class="flex gap-4">
            <input
              type="number"
              min={vocab.freqRange.min}
              max={vocab.freqRange.max}
              bind:value={freqMin}
              class="flex-1 px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              placeholder="最小"
            />
            <input
              type="number"
              min={vocab.freqRange.min}
              max={vocab.freqRange.max}
              bind:value={freqMax}
              class="flex-1 px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              placeholder="最大"
            />
          </div>
        </div>

        <div>
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              bind:checked={excludePropn}
              class="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
            />
            <span class="text-sm text-slate-700">排除專有名詞</span>
          </label>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .quiz-option {
    border-color: rgb(226 232 240);
    background-color: white;
  }

  .quiz-option:hover:not(:disabled) {
    border-color: rgb(165 180 252);
    background-color: rgb(248 250 252);
  }

  .quiz-option.selected {
    border-color: rgb(99 102 241);
    background-color: rgb(238 242 255);
  }

  .quiz-option.correct {
    border-color: rgb(34 197 94);
    background-color: rgb(240 253 244);
  }

  .quiz-option.incorrect {
    border-color: rgb(239 68 68);
    background-color: rgb(254 242 242);
  }

  .quiz-option:disabled {
    cursor: default;
  }

  .pos-chip {
    background-color: rgb(241 245 249);
    color: rgb(71 85 105);
    border: 1px solid transparent;
  }

  .pos-chip:hover {
    background-color: rgb(226 232 240);
  }

  .pos-chip.active {
    background-color: rgb(238 242 255);
    color: rgb(79 70 229);
    border-color: rgb(165 180 252);
  }
</style>
