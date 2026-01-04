<script lang="ts">
    import type { PatternEntry } from "$lib/types/vocab";
    import {
        formatExamType,
        formatSectionType,
    } from "$lib/constants/exam-types";

    interface Props {
        entry: PatternEntry;
    }

    let { entry }: Props = $props();

    let expandedSubtypes = $state<Set<string>>(new Set());

    function toggleSubtype(subtype: string) {
        const next = new Set(expandedSubtypes);
        if (next.has(subtype)) {
            next.delete(subtype);
        } else {
            next.add(subtype);
        }
        expandedSubtypes = next;
    }

    function getCategoryDisplayName(category: string): string {
        const names: Record<string, string> = {
            subjunctive: "假設語氣",
            inversion: "倒裝句",
            participle: "分詞構句",
            cleft_sentence: "分裂句",
            comparison_adv: "比較級進階",
            concession_adv: "讓步子句",
            result_purpose: "結果與目的",
        };
        return names[category] ?? category;
    }

    function formatYear(year: number): string {
        if (year >= 100) {
            return `${year}年`;
        }
        return `${year}年`;
    }
</script>

<div class="pattern-detail">
    <header class="pattern-header">
        <div class="flex items-start justify-between gap-4">
            <h1 class="text-2xl font-bold text-content-primary">
                {entry.lemma}
            </h1>
            <span class="category-badge">
                {getCategoryDisplayName(entry.pattern_category)}
            </span>
        </div>
    </header>

    <section class="teaching-section">
        <h2 class="section-title">
            <svg
                class="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342M6.75 15a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm0 0v-3.675A55.378 55.378 0 0 1 12 8.443m-7.007 11.55A5.981 5.981 0 0 0 6.75 15.75v-1.5"
                />
            </svg>
            教學說明
        </h2>
        <div class="teaching-content">
            {#each entry.teaching_explanation.split("\n\n") as paragraph}
                <p>{paragraph}</p>
            {/each}
        </div>
    </section>

    <section class="subtypes-section">
        <h2 class="section-title">
            <svg
                class="w-5 h-5"
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
            句型變體
            <span class="count-badge">{entry.subtypes.length}</span>
        </h2>

        <div class="subtypes-list">
            {#each entry.subtypes as subtype}
                {@const isExpanded = expandedSubtypes.has(subtype.subtype)}
                <div class="subtype-card" class:expanded={isExpanded}>
                    <button
                        class="subtype-header"
                        onclick={() => toggleSubtype(subtype.subtype)}
                        type="button"
                    >
                        <div class="subtype-info">
                            <span class="subtype-name"
                                >{subtype.display_name}</span
                            >
                            <code class="subtype-structure"
                                >{subtype.structure}</code
                            >
                        </div>
                        <svg
                            class="chevron"
                            class:rotated={isExpanded}
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

                    {#if isExpanded}
                        <div class="subtype-content">
                            {#if subtype.generated_example}
                                <div class="example-block generated">
                                    <span class="example-label">學習例句</span>
                                    <p class="example-text">
                                        {subtype.generated_example}
                                    </p>
                                </div>
                            {/if}

                            {#if subtype.examples && subtype.examples.length > 0}
                                <div class="example-block exam">
                                    <span class="example-label"
                                        >歷屆考題（{subtype.examples
                                            .length}題）</span
                                    >
                                    {#each subtype.examples as example}
                                        <div class="exam-example">
                                            <p class="example-text">
                                                "{example.text}"
                                            </p>
                                            <div class="example-source">
                                                <span
                                                    >{formatYear(
                                                        example.source.year,
                                                    )}</span
                                                >
                                                <span class="dot">·</span>
                                                <span
                                                    >{formatExamType(
                                                        example.source
                                                            .exam_type,
                                                    )}</span
                                                >
                                                <span class="dot">·</span>
                                                <span
                                                    >{formatSectionType(
                                                        example.source
                                                            .section_type,
                                                    )}</span
                                                >
                                                {#if example.source.question_number}
                                                    <span class="dot">·</span>
                                                    <span
                                                        >第{example.source
                                                            .question_number}題</span
                                                    >
                                                {/if}
                                            </div>
                                        </div>
                                    {/each}
                                </div>
                            {/if}
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    </section>
</div>

<style>
    .pattern-detail {
        padding: 1.5rem;
        max-width: 100%;
        overflow-y: auto;
    }

    .pattern-header {
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--color-border);
    }

    .category-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.375rem 0.75rem;
        background-color: #f3e8ff;
        color: #7c3aed;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 9999px;
        white-space: nowrap;
    }

    .section-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1rem;
        font-weight: 600;
        color: var(--color-content-primary);
        margin-bottom: 1rem;
    }

    .section-title svg {
        color: var(--color-content-tertiary);
    }

    .count-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 1.25rem;
        height: 1.25rem;
        padding: 0 0.375rem;
        background-color: var(--color-surface-secondary);
        color: var(--color-content-secondary);
        font-size: 0.75rem;
        font-weight: 500;
        border-radius: 9999px;
    }

    .teaching-section {
        margin-bottom: 2rem;
    }

    .teaching-content {
        background-color: var(--color-surface-secondary);
        border-radius: 0.75rem;
        padding: 1.25rem;
        font-size: 0.9375rem;
        line-height: 1.75;
        color: var(--color-content-secondary);
    }

    .teaching-content p {
        margin-bottom: 1rem;
    }

    .teaching-content p:last-child {
        margin-bottom: 0;
    }

    .subtypes-list {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .subtype-card {
        border: 1px solid var(--color-border);
        border-radius: 0.75rem;
        overflow: hidden;
        transition: border-color 0.15s ease;
    }

    .subtype-card:hover {
        border-color: var(--color-border-hover);
    }

    .subtype-card.expanded {
        border-color: #a78bfa;
    }

    .subtype-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: 1rem;
        background: none;
        border: none;
        cursor: pointer;
        text-align: left;
        transition: background-color 0.15s ease;
    }

    .subtype-header:hover {
        background-color: var(--color-surface-hover);
    }

    .subtype-info {
        display: flex;
        flex-direction: column;
        gap: 0.375rem;
    }

    .subtype-name {
        font-weight: 600;
        color: var(--color-content-primary);
        font-size: 0.9375rem;
    }

    .subtype-structure {
        font-family:
            ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
            "Liberation Mono", monospace;
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
        background-color: var(--color-surface-secondary);
        padding: 0.125rem 0.375rem;
        border-radius: 0.25rem;
    }

    .chevron {
        width: 1.25rem;
        height: 1.25rem;
        color: var(--color-content-tertiary);
        transition: transform 0.2s ease;
        flex-shrink: 0;
    }

    .chevron.rotated {
        transform: rotate(180deg);
    }

    .subtype-content {
        padding: 0 1rem 1rem;
        border-top: 1px solid var(--color-border);
        margin-top: 0;
        padding-top: 1rem;
    }

    .example-block {
        margin-bottom: 1rem;
    }

    .example-block:last-child {
        margin-bottom: 0;
    }

    .example-label {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.025em;
        margin-bottom: 0.5rem;
    }

    .example-block.generated .example-label {
        color: #0891b2;
    }

    .example-block.exam .example-label {
        color: #7c3aed;
    }

    .example-text {
        font-size: 0.9375rem;
        line-height: 1.6;
        color: var(--color-content-primary);
        font-style: italic;
    }

    .exam-example {
        background-color: var(--color-surface-page);
        border-radius: 0.5rem;
        padding: 0.875rem;
        margin-bottom: 0.75rem;
        border-left: 3px solid #a78bfa;
    }

    .exam-example:last-child {
        margin-bottom: 0;
    }

    .example-source {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.25rem;
        margin-top: 0.5rem;
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
    }

    .example-source .dot {
        color: var(--color-border-hover);
    }
</style>
