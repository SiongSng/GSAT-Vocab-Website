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
    let examplePage = $state(0);
    const EXAMPLES_PER_PAGE = 5;

    $effect(() => {
        lemma;
        activeSenseIndex = 0;
        examplePage = 0;
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
    {#if showTabs}
        <div class="flex gap-1 mb-4 overflow-x-auto pb-1 -mx-1 px-1">
            {#each senses.slice(0, maxVisibleTabs) as sense, i}
                <button
                    type="button"
                    class="flex-shrink-0 px-3 py-1.5 text-sm font-medium rounded-md transition-all {activeSenseIndex ===
                    i
                        ? 'bg-accent-soft text-accent'
                        : 'bg-surface-page text-content-secondary hover:bg-surface-hover hover:text-content-primary'}"
                    onclick={() => selectSense(i)}
                >
                    <span class="text-xs opacity-70">{sense.pos}</span>
                    <span class="ml-1">{truncateDef(sense.zh_def)}</span>
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
    {:else if activeSense}
        <!-- Single sense: larger display -->
        <div class="single-sense mb-4">
            <div class="flex items-center gap-2 mb-2">
                <span
                    class="text-xs font-medium px-2 py-0.5 bg-accent-soft text-accent rounded"
                >
                    {activeSense.pos}
                </span>
                {#if activeSense.tested_in_exam}
                    <span
                        class="text-xs font-medium px-1.5 py-0.5 bg-srs-good-soft text-srs-good rounded"
                    >
                        曾考
                    </span>
                {/if}
            </div>
            <p class="text-lg text-content-primary leading-relaxed">
                {activeSense.zh_def}
            </p>
            {#if activeSense.en_def}
                <p class="text-sm text-content-secondary mt-1 leading-relaxed">
                    {activeSense.en_def}
                </p>
            {/if}
        </div>
    {/if}

    {#if activeSense}
        <div class="sense-content space-y-4">
            {#if showTabs && (activeSense.tested_in_exam || activeSense.en_def)}
                <div class="definition-block flex items-start gap-2">
                    {#if activeSense.tested_in_exam}
                        <span
                            class="text-xs font-medium px-1.5 py-0.5 bg-srs-good-soft text-srs-good rounded flex-shrink-0"
                            >曾考</span
                        >
                    {/if}
                    {#if activeSense.en_def}
                        <p
                            class="text-sm text-content-secondary leading-relaxed"
                        >
                            {activeSense.en_def}
                        </p>
                    {/if}
                </div>
            {/if}

            {#if activeSense.examples?.length > 0}
                <div class="examples-block">
                    <div class="flex items-center justify-between mb-3">
                        <h4
                            class="text-xs font-medium text-content-tertiary uppercase tracking-wider"
                        >
                            真實考題例句
                            {#if totalExamples > EXAMPLES_PER_PAGE}
                                <span class="normal-case"
                                    >({totalExamples})</span
                                >
                            {/if}
                        </h4>
                        {#if totalPages > 1}
                            <div class="flex items-center gap-1">
                                <button
                                    type="button"
                                    class="p-1 rounded hover:bg-surface-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                    disabled={examplePage === 0}
                                    onclick={() => goToPage(examplePage - 1)}
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
                                    class="text-xs text-content-tertiary px-1"
                                >
                                    {examplePage + 1} / {totalPages}
                                </span>
                                <button
                                    type="button"
                                    class="p-1 rounded hover:bg-surface-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                    disabled={examplePage >= totalPages - 1}
                                    onclick={() => goToPage(examplePage + 1)}
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
                    <div class="space-y-3">
                        {#each paginatedExamples as example, i (examplePage * EXAMPLES_PER_PAGE + i)}
                            <div
                                class="example-item bg-surface-primary rounded-lg p-4 border border-border shadow-card"
                            >
                                <p class="text-content-primary leading-relaxed">
                                    <ClickableWord
                                        text={example.text}
                                        highlightWord={lemma}
                                    />
                                </p>
                                <div
                                    class="flex items-center justify-between mt-3"
                                >
                                    <span
                                        class="text-xs text-content-tertiary bg-surface-page px-2 py-1 rounded"
                                    >
                                        {formatSource(example.source)}
                                    </span>
                                    <button
                                        type="button"
                                        class="p-1.5 rounded-md hover:bg-surface-hover transition-colors"
                                        class:animate-pulse={playingSentenceIndex ===
                                            examplePage * EXAMPLES_PER_PAGE + i}
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

            {#if activeSense.generated_example}
                <div class="generated-example-block">
                    <h4
                        class="text-xs font-medium text-content-tertiary uppercase tracking-wider mb-2"
                    >
                        學習例句
                    </h4>
                    <p
                        class="text-sm text-content-secondary italic leading-relaxed"
                    >
                        <ClickableWord
                            text={activeSense.generated_example}
                            highlightWord={lemma}
                        />
                    </p>
                </div>
            {/if}
        </div>
    {/if}
</div>
