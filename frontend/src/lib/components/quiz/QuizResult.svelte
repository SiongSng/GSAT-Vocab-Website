<script lang="ts">
    interface WrongWord {
        lemma: string;
        definition: string;
    }

    interface Props {
        score: number;
        total: number;
        wrongWords: WrongWord[];
        onRetryWrong: () => void;
        onContinue: () => void;
    }

    let { score, total, wrongWords, onRetryWrong, onContinue }: Props =
        $props();

    const percent = $derived(total > 0 ? Math.round((score / total) * 100) : 0);

    const result = $derived.by(() => {
        if (percent >= 90)
            return { emoji: "🎉", title: "太棒了！", desc: "你掌握得非常好" };
        if (percent >= 70)
            return { emoji: "👍", title: "不錯喔！", desc: "大部分都答對了" };
        if (percent >= 50)
            return {
                emoji: "💪",
                title: "繼續加油！",
                desc: "再多練習幾次會更好",
            };
        return {
            emoji: "📚",
            title: "再接再厲",
            desc: "建議複習一下不熟的單字",
        };
    });

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter") {
            e.preventDefault();
            onContinue();
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="result-container">
    <div class="card">
        <div class="header">
            <div class="icon-circle">
                <span class="emoji">{result.emoji}</span>
            </div>
            <h1 class="title">{result.title}</h1>
            <p class="subtitle">{result.desc}</p>
        </div>

        <div class="score-display">
            <div class="score-ring" style="--percent: {percent}%">
                <svg viewBox="0 0 36 36" class="circular-chart">
                    <path
                        class="circle-bg"
                        d="M18 2.0845
                            a 15.9155 15.9155 0 0 1 0 31.831
                            a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                        class="circle"
                        stroke-dasharray="{percent}, 100"
                        d="M18 2.0845
                            a 15.9155 15.9155 0 0 1 0 31.831
                            a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                </svg>
                <div class="score-text">
                    <span class="score-val">{score}</span>
                    <span class="score-total">/{total}</span>
                </div>
            </div>
        </div>

        {#if wrongWords.length > 0}
            <div class="review-section">
                <div class="section-header">
                    <h3>需要加強 ({wrongWords.length})</h3>
                </div>
                <div class="wrong-list">
                    {#each wrongWords as word}
                        <div class="wrong-item">
                            <span class="word">{word.lemma}</span>
                            <span class="def">{word.definition}</span>
                        </div>
                    {/each}
                </div>
            </div>
        {/if}

        <div class="actions">
            {#if wrongWords.length > 0}
                <button class="btn-secondary" onclick={onRetryWrong}>
                    複習錯題
                </button>
            {/if}
            <button class="btn-primary" onclick={onContinue}>
                完成
                <span class="kbd-hint">Enter</span>
            </button>
        </div>
    </div>
</div>

<style>
    .result-container {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100%;
        padding: 1.5rem;
        background-color: var(--color-surface-page);
    }

    .card {
        width: 100%;
        max-width: 400px;
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }

    /* Header */
    .header {
        text-align: center;
        margin-bottom: 2rem;
    }

    .icon-circle {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 64px;
        height: 64px;
        border-radius: 50%;
        background: var(--color-surface-page);
        margin-bottom: 1rem;
    }

    .emoji {
        font-size: 2rem;
    }

    .title {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--color-content-primary);
        margin: 0 0 0.5rem 0;
    }

    .subtitle {
        font-size: 0.9375rem;
        color: var(--color-content-secondary);
        margin: 0;
    }

    /* Score Ring */
    .score-display {
        display: flex;
        justify-content: center;
        margin-bottom: 2rem;
    }

    .score-ring {
        position: relative;
        width: 120px;
        height: 120px;
    }

    .circular-chart {
        display: block;
        width: 100%;
        max-width: 100%;
        max-height: 100%;
    }

    .circle-bg {
        fill: none;
        stroke: var(--color-surface-hover);
        stroke-width: 2.5;
    }

    .circle {
        fill: none;
        stroke: var(--color-accent);
        stroke-width: 2.5;
        stroke-linecap: round;
        animation: progress 1s ease-out forwards;
    }

    @keyframes progress {
        0% {
            stroke-dasharray: 0, 100;
        }
    }

    .score-text {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        display: flex;
        align-items: baseline;
    }

    .score-val {
        font-size: 2rem;
        font-weight: 700;
        color: var(--color-content-primary);
    }

    .score-total {
        font-size: 1rem;
        color: var(--color-content-tertiary);
        margin-left: 2px;
    }

    /* Wrong List */
    .review-section {
        margin-bottom: 2rem;
        border-top: 1px solid var(--color-border);
        padding-top: 1.5rem;
    }

    .section-header h3 {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--color-content-tertiary);
        text-transform: uppercase;
        margin: 0 0 1rem 0;
        letter-spacing: 0.05em;
    }

    .wrong-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        max-height: 240px;
        overflow-y: auto;
        padding-right: 4px; /* Space for scrollbar */
    }

    /* Custom Scrollbar for list */
    .wrong-list::-webkit-scrollbar {
        width: 4px;
    }
    .wrong-list::-webkit-scrollbar-track {
        background: transparent;
    }
    .wrong-list::-webkit-scrollbar-thumb {
        background-color: var(--color-border);
        border-radius: 4px;
    }

    .wrong-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem;
        background: var(--color-surface-page);
        border-radius: 8px;
        font-size: 0.9375rem;
    }

    .word {
        font-weight: 600;
        color: var(--color-content-primary);
    }

    .def {
        color: var(--color-content-secondary);
        max-width: 60%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        text-align: right;
    }

    /* Actions */
    .actions {
        display: flex;
        gap: 0.75rem;
    }

    .btn-primary,
    .btn-secondary {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.875rem;
        border-radius: 8px;
        font-size: 0.9375rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }

    .btn-primary {
        background: var(--color-accent);
        color: white;
        border: none;
    }

    .btn-primary:hover {
        opacity: 0.9;
    }

    .btn-secondary {
        background: transparent;
        border: 1px solid var(--color-border);
        color: var(--color-content-secondary);
    }

    .btn-secondary:hover {
        background: var(--color-surface-hover);
        color: var(--color-content-primary);
        border-color: var(--color-content-tertiary);
    }

    .kbd-hint {
        font-size: 0.75rem;
        background: rgba(255, 255, 255, 0.2);
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
    }

    @media (max-width: 640px) {
        .card {
            padding: 0;
            background: transparent;
            border: none;
            box-shadow: none;
        }

        .actions {
            flex-direction: column-reverse;
        }
    }
</style>
