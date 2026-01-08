<script lang="ts">
    import type { Snippet } from "svelte";
    import { getAppStore } from "$lib/stores/app.svelte";

    interface Props {
        showFeedback: boolean;
        question: Snippet;
        feedback?: Snippet;
    }

    let { showFeedback, question, feedback }: Props = $props();

    const app = getAppStore();
    let isCollapsed = $state(false);

    $effect(() => {
        if (showFeedback) {
            isCollapsed = false;
        }
    });

    function toggleCollapse() {
        isCollapsed = !isCollapsed;
    }
</script>

<div class="quiz-layout" class:has-feedback={showFeedback}>
    <div class="question-area">
        {@render question()}
    </div>

    {#if showFeedback && feedback}
        {#if app.isMobile}
            {#if !isCollapsed}
                <button
                    type="button"
                    class="bottom-sheet-backdrop"
                    onclick={toggleCollapse}
                    aria-label="收起回饋"
                ></button>
            {/if}
            <div class="bottom-sheet" class:collapsed={isCollapsed}>
                <button
                    type="button"
                    class="bottom-sheet-handle-btn"
                    onclick={toggleCollapse}
                    aria-label={isCollapsed ? "展開回饋" : "收起回饋"}
                >
                    {#if isCollapsed}
                        <span class="collapsed-hint">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="18 15 12 9 6 15"></polyline>
                            </svg>
                            查看回饋
                        </span>
                    {:else}
                        <div class="bottom-sheet-handle"></div>
                    {/if}
                </button>
                {#if !isCollapsed}
                    <div class="bottom-sheet-content">
                        {@render feedback()}
                    </div>
                {/if}
            </div>
        {:else}
            <div class="feedback-area">
                {@render feedback()}
            </div>
        {/if}
    {/if}
</div>

<style>
    .quiz-layout {
        display: flex;
        flex-direction: column;
        flex: 1;
        min-height: 0;
    }

    .question-area {
        flex: 1;
    }

    .feedback-area {
        margin-top: 1.5rem;
        padding: 1.25rem;
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 12px;
        animation: fadeIn 0.25s ease-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Desktop: Side by Side */
    @media (min-width: 1024px) {
        .quiz-layout.has-feedback {
            flex-direction: row;
            gap: 1.5rem;
            align-items: flex-start;
        }

        .quiz-layout.has-feedback .question-area {
            flex: 1 1 0;
            min-width: 0;
        }

        .quiz-layout.has-feedback .feedback-area {
            flex: 0 0 400px;
            margin-top: 0;
            position: sticky;
            top: 1rem;
        }
    }

    /* Mobile: Bottom Sheet */
    .bottom-sheet-backdrop,
    .bottom-sheet {
        display: none;
    }

    @media (max-width: 767px) {
        .quiz-layout.has-feedback .question-area {
            opacity: 0.4;
            pointer-events: none;
            transition: opacity 0.2s;
        }

        .quiz-layout.has-feedback:has(.collapsed) .question-area {
            opacity: 1;
            pointer-events: auto;
        }

        .bottom-sheet-backdrop {
            display: block;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.15);
            z-index: 40;
            animation: fadeInBackdrop 0.2s ease-out;
            border: none;
            cursor: pointer;
        }

        .bottom-sheet {
            display: flex;
            flex-direction: column;
            position: fixed;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--color-surface-primary);
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
            z-index: 55;
            max-height: 65vh;
            box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.12);
            animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .bottom-sheet.collapsed {
            transform: translateY(calc(100% - var(--bottom-nav-height, 70px)));
        }

        .bottom-sheet-handle-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.25rem;
            width: 100%;
            padding: 0.75rem 0;
            background: transparent;
            border: none;
            cursor: pointer;
            flex-shrink: 0;
        }

        .bottom-sheet.collapsed .bottom-sheet-handle-btn {
            min-height: var(--bottom-nav-height, 70px);
            padding-bottom: calc(0.5rem + env(safe-area-inset-bottom, 0px));
        }

        .collapsed-hint {
            display: inline-flex;
            align-items: center;
            gap: 0.375rem;
            font-size: 0.8125rem;
            font-weight: 500;
            color: var(--color-content-secondary);
            background: var(--color-surface-hover);
            padding: 0.375rem 0.75rem;
            border-radius: 100px;
        }

        .bottom-sheet-handle {
            width: 36px;
            height: 4px;
            background: var(--color-border);
            border-radius: 2px;
        }

        .bottom-sheet-content {
            flex: 1;
            overflow-y: auto;
            padding: 0 1.25rem 1.25rem;
        }
    }

    @keyframes fadeInBackdrop {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes slideUp {
        from {
            transform: translateY(100%);
        }
        to {
            transform: translateY(0);
        }
    }
</style>
