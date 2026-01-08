<script lang="ts">
    import {
        getAvailableCount,
        getQuizStats,
        type QuizQuestionType,
    } from "$lib/stores/quiz-generator";
    import { loadVocabData, getVocabStore } from "$lib/stores/vocab.svelte";
    import { navigate } from "$lib/stores/router.svelte";
    import { getAppStore } from "$lib/stores/app.svelte";
    import { onMount } from "svelte";
    import { onDataChange } from "$lib/stores/srs-storage";

    interface Props {
        onStart: (config: {
            count: number;
            entry_type?: "word" | "phrase";
            force_type?: QuizQuestionType;
        }) => void;
    }

    let { onStart }: Props = $props();

    const vocab = getVocabStore();
    const app = getAppStore();

    let questionCount = $state(20);
    let entryType = $state<"word" | "phrase" | "all">("all");
    let isInitializing = $state(true);
    let dataVersion = $state(0);

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
        if (stats.breakdown.words > 0) parts.push(`${stats.breakdown.words} 單字`);
        if (stats.breakdown.phrases > 0) parts.push(`${stats.breakdown.phrases} 片語`);

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
        if (availableCount === 0) return;

        onStart({
            count: questionCount,
            entry_type: entryType === "all" ? undefined : entryType,
        });
    }

    function handleBrowse() {
        navigate({ name: "browse" });
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter" && !isInitializing) {
            if (availableCount > 0) {
                e.preventDefault();
                handleStart();
            } else {
                e.preventDefault();
                handleBrowse();
            }
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="start-container">
    <div class="dashboard-card">
        {#if isInitializing || vocab.isLoading}
            <div class="state-loading">
                <div class="spinner"></div>
                <p>正在同步學習進度...</p>
            </div>
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
                            {#each [{ value: "all", label: "全部" }, { value: "word", label: "單字" }, { value: "phrase", label: "片語" }] as type}
                                <button
                                    class:active={entryType === type.value}
                                    onclick={() =>
                                        (entryType = type.value as any)}
                                >
                                    {type.label}
                                </button>
                            {/each}
                        </div>
                    </div>
                </div>

                <div class="main-actions">
                    <button class="btn-start" onclick={handleStart}>
                        開始測驗
                        <span class="arrow">→</span>
                    </button>
                    {#if !app.isMobile}
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
                <h1>尚無待複習卡片</h1>
                <p class="subtitle">
                    目前沒有需要複習的單字。去探索新的單字並加入學習計畫吧！
                </p>

                <div class="main-actions">
                    <button class="btn-primary" onclick={handleBrowse}>
                        <span>瀏覽單字庫</span>
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

    .btn-start .arrow {
        font-size: 1.125rem;
        transition: transform 0.15s ease;
    }

    .btn-start:hover .arrow {
        transform: translateX(2px);
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
    .state-loading {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
        padding: 3rem 0;
        color: var(--color-content-secondary);
    }

    .spinner {
        width: 28px;
        height: 28px;
        border: 2.5px solid var(--color-surface-secondary);
        border-top-color: var(--color-content-primary);
        border-radius: 50%;
        animation: spin 0.7s linear infinite;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

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
