<script lang="ts">
    import type { VocabSense } from "$lib/types/vocab";
    import { speakText } from "$lib/tts";
    import ClickableWord from "$lib/components/ui/ClickableWord.svelte";

    interface Props {
        senses: VocabSense[];
        lemma: string;
    }

    let { senses, lemma }: Props = $props();
    let activeSenseIndex = $state(0);
    let playingSentenceIndex = $state<number | null>(null);
    let audioPlayer: HTMLAudioElement | null = null;
    let showExamExamples = $state(true);
    let examplePage = $state(0);
    const EXAMPLES_PER_PAGE = 5;

    $effect(() => {
        lemma;
        activeSenseIndex = 0;
        examplePage = 0;
        showExamExamples = true;
    });

    const activeSense = $derived(senses[activeSenseIndex]);
    const showTabs = $derived(senses.length > 1);
    const maxVisibleTabs = 4;
    const hasMoreTabs = $derived(senses.length > maxVisibleTabs);

    const totalExamples = $derived(activeSense?.examples?.length ?? 0);
    const totalPages = $derived(Math.ceil(totalExamples / EXAMPLES_PER_PAGE));
    const paginatedExamples = $derived(
        activeSense?.examples?.slice(
            examplePage * EXAMPLES_PER_PAGE,
            (examplePage + 1) * EXAMPLES_PER_PAGE,
        ) ?? [],
    );

    function selectSense(index: number) {
        activeSenseIndex = index;
        examplePage = 0;
        showExamExamples = true;
    }

    function goToPage(page: number) {
        examplePage = page;
    }

    function truncateDef(def: string, maxLen: number = 8): string {
        if (def.length <= maxLen) return def;
        return def.slice(0, maxLen) + "…";
    }

    async function playSentenceAudio(text: string, index: number) {
        if (playingSentenceIndex === index) return;
        playingSentenceIndex = index;
        try {
            const url = await speakText(text);
            if (!audioPlayer) audioPlayer = new Audio();
            audioPlayer.src = url;
            audioPlayer.onended = () => (playingSentenceIndex = null);
            audioPlayer.onerror = () => (playingSentenceIndex = null);
            await audioPlayer.play();
        } catch {
            playingSentenceIndex = null;
        }
    }

    function formatSource(source: {
        year: number;
        exam_type: string;
        section_type: string;
        question_number?: number;
    }): string {
        const examTypeMap: Record<string, string> = {
            gsat: "學測",
            gsat_makeup: "學測補考",
            ast: "指考",
            ast_makeup: "指考補考",
            gsat_trial: "學測試辦",
            gsat_ref: "學測參考試卷",
        };
        const sectionMap: Record<string, string> = {
            vocabulary: "詞彙",
            cloze: "克漏字",
            discourse: "篇章結構",
            structure: "句型",
            reading: "閱讀",
            translation: "翻譯",
            mixed: "綜合",
        };
        const examType = examTypeMap[source.exam_type] ?? source.exam_type;
        const section = sectionMap[source.section_type] ?? source.section_type;
        return `${source.year} ${examType} · ${section}`;
    }
</script>

<div class="sense-tabs-container">
    <!-- Tabs for multiple senses -->
    {#if showTabs}
        <div class="flex gap-1 mb-4 overflow-x-auto pb-1 -mx-1 px-1">
            {#each senses.slice(0, maxVisibleTabs) as sense, i}
                <button
                    type="button"
                    class="sense-tab"
                    class:active={activeSenseIndex === i}
                    onclick={() => selectSense(i)}
                >
                    <span class="tab-pos">{sense.pos}</span>
                    <span class="tab-def">{truncateDef(sense.zh_def)}</span>
                    {#if sense.tested_in_exam}
                        <span class="tab-tested-dot"></span>
                    {/if}
                </button>
            {/each}
            {#if hasMoreTabs}
                <span
                    class="flex-shrink-0 px-2 py-1.5 text-sm text-content-tertiary"
                >
                    +{senses.length - maxVisibleTabs}
                </span>
            {/if}
        </div>
    {/if}

    {#if activeSense}
        <div class="sense-content">
            <!-- Definition Block - Primary focus -->
            <div class="definition-block mb-4">
                {#if !showTabs}
                    <div class="flex items-center gap-2 mb-2">
                        <span class="pos-tag">{activeSense.pos}</span>
                        {#if activeSense.tested_in_exam}
                            <span class="tested-tag">曾考</span>
                        {/if}
                    </div>
                {/if}
                <p class="zh-def">{activeSense.zh_def}</p>
                {#if activeSense.en_def}
                    <p class="en-def">{activeSense.en_def}</p>
                {/if}
            </div>

            <!-- Learning Example - LLM generated, prioritized -->
            {#if activeSense.generated_example}
                <div class="learning-example mb-4">
                    <p class="example-text">
                        <ClickableWord
                            text={activeSense.generated_example}
                            highlightWord={lemma}
                        />
                    </p>
                </div>
            {/if}

            <!-- Exam Examples - Secondary, collapsible -->
            {#if totalExamples > 0}
                <div class="exam-examples-section">
                    <button
                        type="button"
                        class="exam-toggle"
                        onclick={() => (showExamExamples = !showExamExamples)}
                    >
                        <span>歷屆考題 ({totalExamples})</span>
                        <svg
                            class="w-4 h-4 transition-transform {showExamExamples
                                ? 'rotate-180'
                                : ''}"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="m19.5 8.25-7.5 7.5-7.5-7.5"
                            />
                        </svg>
                    </button>

                    {#if showExamExamples}
                        <div class="exam-examples-list">
                            <div class="exam-list-header">
                                {#if totalPages > 1}
                                    <div class="pagination-controls">
                                        <button
                                            type="button"
                                            class="p-1 rounded hover:bg-surface-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                            disabled={examplePage === 0}
                                            onclick={() =>
                                                goToPage(examplePage - 1)}
                                            aria-label="上一頁"
                                        >
                                            <svg
                                                class="w-4 h-4 text-content-tertiary"
                                                xmlns="http://www.w3.org/2000/svg"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke-width="1.5"
                                                stroke="currentColor"
                                            >
                                                <path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    d="M15.75 19.5 8.25 12l7.5-7.5"
                                                />
                                            </svg>
                                        </button>
                                        <span
                                            class="text-xs text-content-tertiary"
                                        >
                                            {examplePage + 1}/{totalPages}
                                        </span>
                                        <button
                                            type="button"
                                            class="p-1 rounded hover:bg-surface-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                            disabled={examplePage >=
                                                totalPages - 1}
                                            onclick={() =>
                                                goToPage(examplePage + 1)}
                                            aria-label="下一頁"
                                        >
                                            <svg
                                                class="w-4 h-4 text-content-tertiary"
                                                xmlns="http://www.w3.org/2000/svg"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke-width="1.5"
                                                stroke="currentColor"
                                            >
                                                <path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    d="m8.25 4.5 7.5 7.5-7.5 7.5"
                                                />
                                            </svg>
                                        </button>
                                    </div>
                                {/if}
                            </div>
                            <div class="exam-items">
                                {#each paginatedExamples as example, i (examplePage * EXAMPLES_PER_PAGE + i)}
                                    <div class="exam-item">
                                        <p class="exam-text">
                                            <ClickableWord
                                                text={example.text}
                                                highlightWord={lemma}
                                            />
                                        </p>
                                        <div class="exam-meta">
                                            <span class="exam-source">
                                                {formatSource(example.source)}
                                            </span>
                                            <button
                                                type="button"
                                                class="p-1 rounded hover:bg-surface-hover transition-colors"
                                                class:animate-pulse={playingSentenceIndex ===
                                                    examplePage *
                                                        EXAMPLES_PER_PAGE +
                                                        i}
                                                onclick={() =>
                                                    playSentenceAudio(
                                                        example.text,
                                                        examplePage *
                                                            EXAMPLES_PER_PAGE +
                                                            i,
                                                    )}
                                                title="播放例句"
                                            >
                                                <svg
                                                    class="w-3.5 h-3.5 text-content-tertiary"
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    fill="none"
                                                    viewBox="0 0 24 24"
                                                    stroke-width="1.5"
                                                    stroke="currentColor"
                                                >
                                                    <path
                                                        stroke-linecap="round"
                                                        stroke-linejoin="round"
                                                        d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"
                                                    />
                                                </svg>
                                            </button>
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    {/if}
</div>

<style>
    /* Sense Tabs */
    .sense-tab {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        flex-shrink: 0;
        padding: 0.375rem 0.75rem;
        font-size: 0.875rem;
        font-weight: 500;
        border-radius: 6px;
        background: var(--color-surface-page);
        color: var(--color-content-secondary);
        transition: all 0.15s ease;
        position: relative;
    }

    .sense-tab:hover {
        background: var(--color-surface-hover);
        color: var(--color-content-primary);
    }

    .sense-tab.active {
        background: var(--color-accent-soft);
        color: var(--color-accent);
    }

    .tab-pos {
        font-size: 0.75rem;
        opacity: 0.7;
    }

    .tab-tested-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--color-srs-good);
        margin-left: 0.25rem;
    }

    /* Definition Block */
    .pos-tag {
        font-size: 0.75rem;
        font-weight: 500;
        padding: 0.125rem 0.5rem;
        background: var(--color-accent-soft);
        color: var(--color-accent);
        border-radius: 4px;
    }

    .tested-tag {
        font-size: 0.6875rem;
        font-weight: 500;
        padding: 0.125rem 0.375rem;
        background: var(--color-srs-good-soft);
        color: var(--color-srs-good);
        border-radius: 4px;
    }

    .zh-def {
        font-size: 1.125rem;
        font-weight: 500;
        color: var(--color-content-primary);
        line-height: 1.5;
        margin-bottom: 0.25rem;
    }

    .en-def {
        font-size: 0.875rem;
        color: var(--color-content-secondary);
        line-height: 1.5;
    }

    /* Learning Example */
    .learning-example {
        padding: 0.75rem;
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 8px;
    }

    .example-text {
        font-size: 0.9375rem;
        color: var(--color-content-primary);
        line-height: 1.6;
    }

    /* Exam Examples */
    .exam-examples-section {
        margin-top: 0.5rem;
    }

    .exam-toggle {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.375rem 0;
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--color-content-tertiary);
        transition: color 0.15s ease;
    }

    .exam-toggle:hover {
        color: var(--color-content-secondary);
    }

    .exam-examples-list {
        animation: fadeIn 0.15s ease-out;
    }

    .exam-list-header {
        display: flex;
        justify-content: flex-end;
        min-height: 0;
    }

    .pagination-controls {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .exam-items {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        margin-top: 0.375rem;
    }

    .exam-item {
        padding: 0.75rem;
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 6px;
    }

    .exam-text {
        font-size: 0.875rem;
        color: var(--color-content-primary);
        line-height: 1.5;
        margin-bottom: 0.5rem;
    }

    .exam-meta {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .exam-source {
        font-size: 0.6875rem;
        color: var(--color-content-tertiary);
        background: var(--color-surface-page);
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-4px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
</style>
