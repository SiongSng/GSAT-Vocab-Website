<script lang="ts">
    import type { QuizQuestion } from "$lib/stores/quiz-generator";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";
    import HighlightedText from "$lib/components/ui/HighlightedText.svelte";
    import { getAppStore } from "$lib/stores/app.svelte";

    interface Props {
        isCorrect: boolean;
        question: QuizQuestion;
        onContinue: () => void;
        onShowDetail?: (lemma: string) => void;
        isSentenceDisplayed?: boolean;
    }

    let {
        isCorrect,
        question,
        onContinue,
        onShowDetail,
        isSentenceDisplayed = false,
    }: Props = $props();

    const app = getAppStore();
    const statusClass = $derived(isCorrect ? "status-correct" : "status-wrong");
</script>

<div class="feedback-container {statusClass}">
    <div class="feedback-layout">
        <div class="feedback-content">
            <div class="header-row">
                <div class="icon-indicator">
                    {#if isCorrect}
                        <svg
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="3.5"
                        >
                            <path
                                d="M20 6L9 17l-5-5"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                        </svg>
                    {:else}
                        <svg
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="3.5"
                        >
                            <path
                                d="M18 6L6 18M6 6l12 12"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                        </svg>
                    {/if}
                </div>

                <div class="status-info">
                    <h3 class="status-title">
                        {isCorrect ? "答對了！" : "再接再厲"}
                    </h3>
                    {#if !isCorrect}
                        <div class="answer-reveal">
                            <span class="label">正確答案：</span>
                            <span class="lemma">{question.lemma}</span>
                            <div class="audio-group">
                                <AudioButton text={question.lemma} size="sm" />
                            </div>
                        </div>
                    {/if}
                </div>
            </div>

            <div class="details-grid">
                {#if question.explanation?.correct_usage && !isSentenceDisplayed}
                    <div class="detail-section">
                        <div class="section-header">
                            <span class="section-label">情境例句</span>
                            <AudioButton
                                text={question.explanation.correct_usage}
                                size="md"
                                variant="subtle"
                            />
                        </div>
                        <p class="example-text">
                            <HighlightedText
                                text={question.explanation.correct_usage}
                                highlightLemma={question.lemma}
                            />
                        </p>
                    </div>
                {/if}

                {#if !isCorrect && (question.explanation?.memory_tip || question.explanation?.confusion_note)}
                    <div class="insights-row">
                        {#if question.explanation?.memory_tip}
                            <div class="insight-pill tip">
                                <span class="pill-icon">💡</span>
                                <span class="pill-text"
                                    >{question.explanation.memory_tip}</span
                                >
                            </div>
                        {/if}

                        {#if question.explanation?.confusion_note}
                            <div class="insight-pill confusion">
                                <span class="pill-icon">⚠️</span>
                                <div class="confusion-content">
                                    <span class="confused-with"
                                        >與 {question.explanation.confusion_note
                                            .confused_with} 區分：</span
                                    >
                                    <span class="pill-text"
                                        >{question.explanation.confusion_note
                                            .distinction}</span
                                    >
                                </div>
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        </div>

        <div class="feedback-actions">
            {#if onShowDetail}
                <button
                    class="action-btn secondary"
                    onclick={() => onShowDetail?.(question.lemma)}
                    aria-label="查看詳情"
                    title="查看詳情"
                >
                    <svg
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        />
                    </svg>
                </button>
            {/if}
            <button
                class="action-btn primary continue-btn"
                onclick={onContinue}
            >
                <span>繼續</span>
                {#if !app.isMobile}
                    <span class="kbd">Enter</span>
                {/if}
            </button>
        </div>
    </div>
</div>

<style>
    .feedback-container {
        margin-top: 1.5rem;
        padding: 1.5rem 2rem;
        border-radius: 16px;
        border: 1px solid var(--color-border);
        animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
        overflow: hidden;
    }

    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* Status Colors */
    .status-correct {
        background-color: #f6ffed;
        border-color: #b7eb8f;
    }
    .status-wrong {
        background-color: #fff2f0;
        border-color: #ffccc7;
    }

    .feedback-layout {
        display: flex;
        align-items: center;
        gap: 2rem;
        justify-content: space-between;
    }

    .feedback-content {
        flex: 1;
        min-width: 0;
    }

    /* Header Row */
    .header-row {
        display: flex;
        align-items: center;
        gap: 1.25rem;
        margin-bottom: 1rem;
    }

    .icon-indicator {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .status-correct .icon-indicator {
        background: #52c41a;
        color: white;
    }
    .status-wrong .icon-indicator {
        background: #ff4d4f;
        color: white;
    }
    .icon-indicator svg {
        width: 24px;
        height: 24px;
    }

    .status-info {
        display: flex;
        flex-direction: column;
    }

    .status-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
    }
    .status-correct .status-title {
        color: #237804;
    }
    .status-wrong .status-title {
        color: #a8071a;
    }

    .answer-reveal {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 0.25rem;
    }

    .audio-group {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .answer-reveal .label {
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
        font-weight: 500;
    }

    .lemma {
        font-size: 1.375rem;
        font-weight: 700;
        color: var(--color-content-primary);
        letter-spacing: -0.01em;
    }

    /* Details */
    .details-grid {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.25rem;
    }

    .section-label {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--color-content-tertiary);
        display: block;
    }

    .example-text {
        font-size: 1rem;
        line-height: 1.6;
        color: var(--color-content-secondary);
        font-family: var(--font-serif, serif);
        margin: 0;
    }

    /* Insight Pills */
    .insights-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin-top: 0.5rem;
    }

    .insight-pill {
        display: flex;
        align-items: flex-start;
        gap: 0.625rem;
        padding: 0.625rem 0.875rem;
        background: rgba(255, 255, 255, 0.6);
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 10px;
        font-size: 0.875rem;
        line-height: 1.4;
    }

    .pill-icon {
        font-size: 1.125rem;
        line-height: 1;
        margin-top: 1px;
    }

    .confusion-content {
        display: flex;
        flex-direction: column;
    }

    .confused-with {
        font-weight: 700;
        font-size: 0.75rem;
        color: var(--color-content-primary);
        margin-bottom: 0.125rem;
    }

    /* Actions */
    .feedback-actions {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-shrink: 0;
    }

    .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 52px;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.2s;
        font-weight: 600;
        border: 1px solid transparent;
    }

    .action-btn.primary {
        min-width: 140px;
        gap: 0.75rem;
        font-size: 1.0625rem;
    }

    .status-correct .action-btn.primary {
        background: #52c41a;
        color: white;
    }
    .status-correct .action-btn.primary:hover {
        background: #389e0d;
    }

    .status-wrong .action-btn.primary {
        background: var(--color-content-primary);
        color: var(--color-surface-primary);
    }
    .status-wrong .action-btn.primary:hover {
        opacity: 0.9;
    }

    .action-btn.secondary {
        width: 52px;
        background: var(--color-surface-primary);
        border-color: var(--color-border);
        color: var(--color-content-secondary);
    }
    .action-btn.secondary:hover {
        border-color: var(--color-content-tertiary);
        color: var(--color-content-primary);
    }

    .kbd {
        font-size: 0.75rem;
        background: rgba(255, 255, 255, 0.2);
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 500;
    }

    .status-wrong .kbd {
        background: rgba(255, 255, 255, 0.15);
    }

    /* Responsive */
    @media (max-width: 768px) {
        .feedback-layout {
            flex-direction: column;
            align-items: stretch;
            gap: 1.5rem;
        }

        .feedback-container {
            padding: 1.5rem;
        }

        .feedback-actions {
            flex-direction: row;
        }

        .action-btn.primary {
            flex: 1;
        }
    }

    @media (max-width: 480px) {
        .icon-indicator {
            width: 36px;
            height: 36px;
        }
        .status-title {
            font-size: 1.125rem;
        }
        .lemma {
            font-size: 1.25rem;
        }
        .action-btn {
            height: 48px;
        }
    }

    :global(.dark) .insight-pill {
        background: rgba(0, 0, 0, 0.2);
    }
</style>
