<script lang="ts">
    import type { VocabSense } from "$lib/types/vocab";
    import { sortSensesByExamFrequency } from "$lib/types/vocab";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";
    import HighlightedText from "$lib/components/ui/HighlightedText.svelte";
    import { formatExamSource } from "$lib/constants/exam-types";

    interface Props {
        senses: VocabSense[];
        lemma: string;
        isPhrase?: boolean;
    }

    let { senses, lemma, isPhrase = false }: Props = $props();
    let activeSenseIndex = $state(0);
    let showExamExamples = $state(true);
    let examplePage = $state(0);
    const EXAMPLES_PER_PAGE = 5;

    const sortedSenses = $derived(sortSensesByExamFrequency(senses));

    $effect(() => {
        lemma;
        activeSenseIndex = 0;
        examplePage = 0;
        showExamExamples = true;
    });

    const activeSense = $derived(sortedSenses[activeSenseIndex]);
    const showTabs = $derived(sortedSenses.length > 1);
    const maxVisibleTabs = 4;
    const hasMoreTabs = $derived(sortedSenses.length > maxVisibleTabs);

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
        // Remove parenthetical content: 角色（故事、戲劇） -> 角色
        let cleaned = def.replace(/[（(][^）)]*[）)]/g, "").trim();

        // Keep only first part before semicolon: 零錢；找錢 -> 零錢
        const semicolonIndex = cleaned.search(/[；;]/);
        if (semicolonIndex > 0) {
            cleaned = cleaned.slice(0, semicolonIndex).trim();
        }

        if (cleaned.length <= maxLen) return cleaned;
        return cleaned.slice(0, maxLen) + "…";
    }

    function formatPosAbbrev(pos: string | null): string {
        if (!pos) return "";

        // Handle compound POS like "ADJ/ADV"
        const parts = pos.split("/");
        const abbrevParts = parts.map((p) => {
            const upper = p.toUpperCase().trim();
            switch (upper) {
                case "NOUN":
                case "N":
                    return "N.";
                case "VERB":
                case "V":
                    return "V.";
                case "ADJ":
                case "ADJECTIVE":
                case "A":
                    return "A.";
                case "ADV":
                case "ADVERB":
                    return "AD.";
                case "PREP":
                case "PREPOSITION":
                    return "P.";
                case "CONJ":
                case "CONJUNCTION":
                    return "C.";
                case "PRON":
                case "PRONOUN":
                    return "PN.";
                case "INT":
                case "INTERJECTION":
                    return "I.";
                case "DET":
                case "DETERMINER":
                    return "D.";
                default:
                    // Return first letter + dot for unknown
                    return upper.charAt(0) + ".";
            }
        });

        return abbrevParts.join("/");
    }

    function formatSource(source: {
        year: number;
        exam_type: string;
        section_type: string;
        question_number?: number;
    }): string {
        return formatExamSource(source);
    }
</script>

<div class="sense-tabs-container">
    <!-- Tabs for multiple senses -->
    {#if showTabs}
        <div class="flex gap-2 mb-4 overflow-x-auto pb-1 -mx-1 px-1">
            {#each sortedSenses.slice(0, maxVisibleTabs) as sense, i}
                {@const posAbbrev = formatPosAbbrev(sense.pos)}
                <button
                    type="button"
                    class="sense-tab"
                    class:active={activeSenseIndex === i}
                    onclick={() => selectSense(i)}
                >
                    {#if posAbbrev}
                        <span class="tab-pos">{posAbbrev}</span>
                    {/if}
                    <span class="tab-def">{truncateDef(sense.zh_def)}</span>
                    {#if sense.examples && sense.examples.length > 0}
                        <span class="tab-tested-dot"></span>
                    {/if}
                </button>
            {/each}
            {#if hasMoreTabs}
                <span
                    class="flex-shrink-0 px-2 py-1.5 text-sm text-content-tertiary"
                >
                    +{sortedSenses.length - maxVisibleTabs}
                </span>
            {/if}
        </div>
    {/if}

    {#if activeSense}
        {@const posAbbrev = formatPosAbbrev(activeSense.pos)}
        <div class="sense-content">
            <!-- Definition Block - Primary focus -->
            <div class="definition-block mb-4">
                {#if !showTabs && (posAbbrev || (activeSense.examples && activeSense.examples.length > 0))}
                    <div class="flex items-center gap-2 mb-2">
                        {#if posAbbrev}
                            <span class="pos-tag">{posAbbrev}</span>
                        {/if}
                        {#if activeSense.examples && activeSense.examples.length > 0}
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
                        <HighlightedText
                            text={activeSense.generated_example}
                            highlightLemma={lemma}
                            {isPhrase}
                        />
                    </p>
                    <AudioButton
                        text={activeSense.generated_example}
                        size="sm"
                    />
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
                                {#each paginatedExamples as example, idx (example.text + example.source.year + example.source.exam_type + idx)}
                                    <div class="exam-item">
                                        <p class="exam-text">
                                            <HighlightedText
                                                text={example.text}
                                                highlightLemma={lemma}
                                                {isPhrase}
                                            />
                                        </p>
                                        <div class="exam-meta">
                                            <span class="exam-source">
                                                {formatSource(example.source)}
                                            </span>
                                            <AudioButton
                                                text={example.text}
                                                size="sm"
                                            />
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
        gap: 0.375rem;
        flex-shrink: 0;
        padding: 0.5rem 0.875rem;
        font-size: 0.8125rem;
        font-weight: 500;
        border-radius: 8px;
        background: transparent;
        color: var(--color-content-tertiary);
        position: relative;
    }

    .sense-tab:hover {
        background: var(--color-surface-hover);
        color: var(--color-content-primary);
    }

    .sense-tab.active {
        background: var(--color-content-primary);
        color: var(--color-surface-primary);
    }

    .sense-tab.active .tab-pos {
        opacity: 0.7;
    }

    .sense-tab.active .tab-tested-dot {
        background: var(--color-surface-primary);
    }

    .tab-pos {
        font-size: 0.6875rem;
        opacity: 0.6;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    .tab-tested-dot {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: var(--color-srs-good);
        margin-left: 0.125rem;
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
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
        padding: 0.75rem;
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 8px;
    }

    .example-text {
        flex: 1;
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
