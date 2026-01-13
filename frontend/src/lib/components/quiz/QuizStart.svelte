<script lang="ts">
    import {
        getAvailableCount,
        getQuizStats,
        type QuizQuestionType,
    } from "$lib/stores/quiz-generator";
    import { loadVocabData, getVocabStore } from "$lib/stores/vocab.svelte";
    import { getQuizStore } from "$lib/stores/quiz.svelte";
    import { goto } from "$app/navigation";
    import { base } from "$app/paths";
    import { getAppStore } from "$lib/stores/app.svelte";
    import { onMount } from "svelte";
    import { onDataChange } from "$lib/stores/srs-storage";
    import SyncIndicator from "$lib/components/ui/SyncIndicator.svelte";

    interface Props {
        onStart: (config: {
            count: number;
            entry_type?: "word" | "phrase";
            force_types?: QuizQuestionType[];
        }) => void;
    }

    let { onStart }: Props = $props();

    const vocab = getVocabStore();
    const app = getAppStore();
    const quiz = getQuizStore();

    let questionCount = $state(20);
    let entryType = $state<"word" | "phrase" | "all">("all");
    let selectedTypes = $state<Set<string>>(new Set());
    let isInitializing = $state(true);
    let dataVersion = $state(0);

    const isGenerating = $derived(quiz.isLoading);

    const quizTypeOptions: Array<{
        value: string;
        types: QuizQuestionType[];
        label: string;
    }> = [
        {
            value: "meaning",
            types: ["recognition", "reverse"],
            label: "字義題",
        },
        { value: "fill_blank", types: ["fill_blank"], label: "克漏字" },
        { value: "spelling", types: ["spelling"], label: "拼寫題" },
        { value: "distinction", types: ["distinction"], label: "易混淆" },
    ];

    function toggleType(value: string) {
        const newSet = new Set(selectedTypes);
        if (newSet.has(value)) {
            newSet.delete(value);
        } else {
            newSet.add(value);
        }
        selectedTypes = newSet;
    }

    function getSelectedQuizTypes(): QuizQuestionType[] {
        if (selectedTypes.size === 0) return [];
        const types: QuizQuestionType[] = [];
        for (const opt of quizTypeOptions) {
            if (selectedTypes.has(opt.value)) {
                types.push(...opt.types);
            }
        }
        return types;
    }

    const availableCount = $derived.by(() => {
        dataVersion;
        return getAvailableCount();
    });
    const stats = $derived.by(() => {
        dataVersion;
        return getQuizStats();
    });
    const totalReviewCount = $derived(
        stats.dueSkillCount + stats.newSkillCount + stats.reviewCount,
    );

    const detailText = $derived.by(() => {
        const parts: string[] = [];
        if (stats.breakdown.words > 0)
            parts.push(`${stats.breakdown.words} 單字`);
        if (stats.breakdown.phrases > 0)
            parts.push(`${stats.breakdown.phrases} 片語`);

        const hasAdvanced = stats.dueSkillCount + stats.newSkillCount > 0;
        if (hasAdvanced) {
            parts.push("含拼寫填空");
        }
        return parts.join(" · ");
    });

    const greeting = $derived.by(() => {
        if (totalReviewCount > 30) return { emoji: "🔥", text: "挑戰時刻！" };
        if (totalReviewCount > 10) return { emoji: "💪", text: "準備好了！" };
        return { emoji: "✨", text: "快完成了！" };
    });

    onMount(() => {
        (async () => {
            if (vocab.index.length === 0) {
                await loadVocabData();
            }
            setTimeout(() => {
                isInitializing = false;
            }, 300);
        })();

        const unsubscribe = onDataChange(() => {
            dataVersion++;
        });
        return unsubscribe;
    });

    function handleStart() {
        if (availableCount === 0 || isGenerating) return;

        const forceTypes = getSelectedQuizTypes();
        onStart({
            count: questionCount,
            entry_type: entryType === "all" ? undefined : entryType,
            force_types: forceTypes.length > 0 ? forceTypes : undefined,
        });
    }

    function handleFlashcard() {
        goto(`${base}/flashcard`);
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter" && !isInitializing && !isGenerating) {
            if (availableCount > 0) {
                e.preventDefault();
                handleStart();
            } else {
                e.preventDefault();
                handleFlashcard();
            }
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="start-container">
    <div class="dashboard-card">
        {#if isInitializing || vocab.isLoading}
            <SyncIndicator />
        {:else if availableCount > 0}
            <div class="state-ready">
                <div class="quiz-prompt">
                    <p class="greeting">{greeting.emoji} {greeting.text}</p>

                    <div class="focus-stat">
                        <span class="number">{totalReviewCount}</span>
                        <span class="unit">個待複習項目</span>
                    </div>

                    <p class="detail">
                        {detailText}
                    </p>
                </div>

                <div class="compact-settings">
                    <div class="setting-group">
                        <span class="setting-label">題數</span>
                        <div class="pill-selector">
                            {#each [10, 20, 30] as count}
                                <button
                                    class:active={questionCount === count}
                                    onclick={() => (questionCount = count)}
                                >
                                    {count}
                                </button>
                            {/each}
                        </div>
                    </div>

                    <div class="setting-group">
                        <span class="setting-label">範圍</span>
                        <div class="pill-selector">
                            {#each [{ value: "all", label: "全部" }, { value: "word", label: "單字" }, { value: "phrase", label: "片語" }] as type (type.value)}
                                <button
                                    class:active={entryType === type.value}
                                    onclick={() =>
                                        (entryType = type.value as
                                            | "word"
                                            | "phrase"
                                            | "all")}
                                >
                                    {type.label}
                                </button>
                            {/each}
                        </div>
                    </div>

                    <div class="setting-group full-width">
                        <span class="setting-label">題型</span>
                        <div class="pill-selector type-selector">
                            {#each quizTypeOptions as opt}
                                <button
                                    class:active={selectedTypes.has(opt.value)}
                                    onclick={() => toggleType(opt.value)}
                                >
                                    {opt.label}
                                </button>
                            {/each}
                        </div>
                    </div>
                </div>

                <div class="main-actions">
                    <button
                        class="btn-start"
                        onclick={handleStart}
                        disabled={isGenerating}
                    >
                        {#if isGenerating}
                            <span class="btn-spinner"></span>
                            正在出題...
                        {:else}
                            開始測驗
                        {/if}
                    </button>
                    {#if !app.isMobile && !isGenerating}
                        <p class="kbd-hint"><kbd>Enter</kbd> 快速開始</p>
                    {/if}
                </div>
            </div>
        {:else}
            <div class="state-empty">
                <div class="empty-icon">
                    <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="1.5"
                    >
                        <path
                            d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        />
                    </svg>
                </div>
                <h1>開始學習單字</h1>
                <p class="subtitle">
                    先用字卡學習單字，測驗會自動從已學習的內容出題。
                </p>

                <div class="main-actions">
                    <button class="btn-primary" onclick={handleFlashcard}>
                        <span>前往字卡學習</span>
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>

<style>
    .start-container {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: calc(100vh - 120px);
        padding: 1.5rem;
    }

    .dashboard-card {
        width: 100%;
        max-width: 420px;
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
    }

    /* Quiz Prompt - Single Focus */
    .quiz-prompt {
        text-align: center;
        margin-bottom: 1.5rem;
    }

    .greeting {
        font-size: 1rem;
        font-weight: 600;
        color: var(--color-content-secondary);
        margin: 0 0 1rem;
    }

    .focus-stat {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.25rem;
        margin-bottom: 0.75rem;
    }

    .focus-stat .number {
        font-size: 4rem;
        font-weight: 800;
        color: var(--color-content-primary);
        line-height: 1;
        letter-spacing: -0.03em;
    }

    .focus-stat .unit {
        font-size: 0.9375rem;
        font-weight: 500;
        color: var(--color-content-tertiary);
    }

    .detail {
        font-size: 0.875rem;
        color: var(--color-content-tertiary);
        margin: 0;
    }

    /* Compact Settings */
    .compact-settings {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        padding: 1rem 0;
        border-top: 1px solid var(--color-border);
        border-bottom: 1px solid var(--color-border);
        margin-bottom: 1.5rem;
    }

    .setting-group {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .setting-group.full-width {
        flex: none;
        width: 100%;
    }

    .setting-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--color-content-tertiary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .pill-selector {
        display: flex;
        background: var(--color-surface-secondary);
        padding: 3px;
        border-radius: 8px;
        gap: 2px;
    }

    .pill-selector button {
        flex: 1;
        background: transparent;
        border: none;
        padding: 0.5rem 0.5rem;
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--color-content-secondary);
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.15s ease;
    }

    .pill-selector button:hover {
        color: var(--color-content-primary);
    }

    .pill-selector button.active {
        background: var(--color-surface-primary);
        color: var(--color-content-primary);
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
        font-weight: 600;
    }

    .type-selector {
        display: flex;
        gap: 4px;
    }

    .type-selector button {
        flex: 1;
        min-width: 0;
    }

    /* Main Actions */
    .main-actions {
        text-align: center;
    }

    .btn-start {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        width: 100%;
        padding: 0.875rem 1.25rem;
        background: var(--color-content-primary);
        color: var(--color-surface-primary);
        border: none;
        border-radius: 10px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s ease;
    }

    .btn-start:hover {
        opacity: 0.9;
    }

    .btn-start:active {
        transform: scale(0.98);
    }

    .btn-start:disabled {
        opacity: 0.7;
        cursor: wait;
    }

    .btn-spinner {
        width: 1rem;
        height: 1rem;
        border: 2px solid transparent;
        border-top-color: currentColor;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    .kbd-hint {
        margin-top: 0.75rem;
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
    }

    .kbd-hint kbd {
        background: var(--color-surface-secondary);
        border: 1px solid var(--color-border);
        border-bottom-width: 2px;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: inherit;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* States */
    .state-empty {
        text-align: center;
        padding: 1rem 0;
    }

    .state-empty h1 {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--color-content-primary);
        margin: 0 0 0.5rem;
    }

    .empty-icon {
        color: var(--color-content-tertiary);
        margin-bottom: 1rem;
    }

    .empty-icon svg {
        width: 48px;
        height: 48px;
        margin: 0 auto;
    }

    .subtitle {
        font-size: 0.9375rem;
        color: var(--color-content-secondary);
        line-height: 1.5;
        margin: 0 0 1.5rem;
    }

    @media (max-width: 640px) {
        .dashboard-card {
            padding: 1.5rem;
            border: none;
            box-shadow: none;
            background: transparent;
        }

        .focus-stat .number {
            font-size: 3.5rem;
        }

        .compact-settings {
            flex-direction: column;
            gap: 0.75rem;
            border: none;
            padding: 1rem 0;
        }

        .pill-selector {
            background: var(--color-surface-primary);
            border: 1px solid var(--color-border);
        }

        .pill-selector button.active {
            background: var(--color-content-primary);
            color: var(--color-surface-primary);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
        }
    }
</style>
