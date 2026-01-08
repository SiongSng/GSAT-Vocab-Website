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
        matchedInflected?: boolean;
    }

    let {
        isCorrect,
        question,
        onContinue,
        onShowDetail,
        matchedInflected = false,
    }: Props = $props();

    const app = getAppStore();
    const statusClass = $derived(isCorrect ? "status-correct" : "status-wrong");
    const type = $derived(question.type);

    const needsSentence = $derived(type === "recognition" || type === "reverse");
    const showSentence = $derived(
        needsSentence && !!question.explanation?.correct_usage,
    );
    const showConfusion = $derived(
        type === "distinction" &&
            !isCorrect &&
            !!question.explanation?.confusion_note,
    );
    const showMemoryTip = $derived(
        !isCorrect &&
            !needsSentence &&
            !showConfusion &&
            !!question.explanation?.memory_tip,
    );
    const showInflection = $derived(
        type === "spelling" &&
            isCorrect &&
            !matchedInflected &&
            !!question.inflected_form,
    );
</script>

<div class="feedback-container {statusClass}">
    <div class="feedback-layout">
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
                    {#if isCorrect}
                        {#if type === "spelling" && matchedInflected}
                            完美拼寫！
                        {:else}
                            答對了！
                        {/if}
                    {:else}
                        再接再厲
                    {/if}
                </h3>

                {#if showInflection}
                    <p class="inflection-hint">
                        句中形態為 <strong>{question.inflected_form}</strong>
                    </p>
                {/if}

                {#if !isCorrect}
                    <div class="answer-reveal">
                        <span class="label">正確答案：</span>
                        <span class="lemma">{question.correct}</span>
                        <AudioButton text={question.lemma} size="sm" />
                    </div>
                {/if}
            </div>
        </div>

        {#if showSentence || showConfusion || showMemoryTip}
            <div class="details-section">
                {#if showSentence}
                    <div class="detail-item">
                        <div class="detail-header">
                            <span class="detail-label">情境例句</span>
                            <AudioButton
                                text={question.explanation?.correct_usage ?? ""}
                                size="md"
                                variant="subtle"
                            />
                        </div>
                        <p class="example-text">
                            <HighlightedText
                                text={question.explanation?.correct_usage ?? ""}
                                highlightLemma={question.lemma}
                            />
                        </p>
                    </div>
                {/if}

                {#if showConfusion && question.explanation?.confusion_note}
                    <div class="insight-pill">
                        <span class="pill-icon">⚠️</span>
                        <div class="confusion-content">
                            <span class="confused-with">
                                與 {question.explanation.confusion_note.confused_with} 區分：
                            </span>
                            <span class="pill-text">
                                {question.explanation.confusion_note.distinction}
                            </span>
                        </div>
                    </div>
                {/if}

                {#if showMemoryTip}
                    <div class="insight-pill">
                        <span class="pill-icon">💡</span>
                        <span class="pill-text">{question.explanation?.memory_tip}</span>
                    </div>
                {/if}
            </div>
        {/if}

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
                class="action-btn primary"
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
        animation: fadeIn 0.2s ease-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    .status-correct {
        --feedback-accent: var(--color-srs-good, #52c41a);
        --feedback-accent-dark: #389e0d;
        --feedback-title: #237804;
    }
    .status-wrong {
        --feedback-accent: var(--color-srs-again, #ff4d4f);
        --feedback-accent-dark: #cf1322;
        --feedback-title: #a8071a;
    }

    .feedback-layout {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .header-row {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .icon-indicator {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        background: var(--feedback-accent);
        color: white;
    }
    .icon-indicator svg {
        width: 22px;
        height: 22px;
    }

    .status-title {
        font-size: 1.125rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
        color: var(--feedback-title);
    }

    .inflection-hint {
        font-size: 0.8125rem;
        color: var(--color-content-secondary);
        margin: 0.25rem 0 0 0;
    }
    .inflection-hint strong {
        color: var(--color-accent);
        font-weight: 600;
    }

    .answer-reveal {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 0.25rem;
    }
    .answer-reveal .label {
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
    }
    .lemma {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--color-content-primary);
    }

    .details-section {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .detail-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.25rem;
    }
    .detail-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--color-content-tertiary);
    }

    .example-text {
        font-size: 0.9375rem;
        line-height: 1.6;
        color: var(--color-content-secondary);
        font-family: var(--font-serif, serif);
        margin: 0;
        word-break: break-word;
    }

    .insight-pill {
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        background: var(--color-surface-hover);
        border-radius: 8px;
        font-size: 0.875rem;
        line-height: 1.4;
    }
    .pill-icon {
        font-size: 1rem;
        line-height: 1;
    }
    .confusion-content {
        display: flex;
        flex-direction: column;
    }
    .confused-with {
        font-weight: 600;
        font-size: 0.75rem;
        color: var(--color-content-primary);
        margin-bottom: 0.125rem;
    }

    .feedback-actions {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-top: 0.5rem;
    }

    .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 48px;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.2s;
        font-weight: 600;
        border: 1px solid transparent;
    }
    .action-btn.primary {
        flex: 1;
        gap: 0.5rem;
        font-size: 1rem;
        background: var(--feedback-accent);
        color: white;
    }
    .action-btn.primary:hover {
        background: var(--feedback-accent-dark);
    }

    .action-btn.secondary {
        width: 48px;
        background: var(--color-surface-primary);
        border-color: var(--color-border);
        color: var(--color-content-secondary);
    }
    .action-btn.secondary:hover {
        border-color: var(--color-content-tertiary);
        color: var(--color-content-primary);
    }

    .kbd {
        font-size: 0.7rem;
        background: rgba(255, 255, 255, 0.2);
        padding: 2px 5px;
        border-radius: 4px;
    }

    @media (max-width: 480px) {
        .icon-indicator {
            width: 36px;
            height: 36px;
        }
        .status-title {
            font-size: 1rem;
        }
        .lemma {
            font-size: 1.125rem;
        }
        .action-btn {
            height: 44px;
        }
    }
</style>
