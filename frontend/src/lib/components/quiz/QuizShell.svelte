<script lang="ts">
    import type { Snippet } from "svelte";

    interface Props {
        progress: { current: number; total: number };
        onExit: () => void;
        children: Snippet;
    }

    let { progress, onExit, children }: Props = $props();

    let progressPercent = $derived((progress.current / progress.total) * 100);
</script>

<div class="quiz-shell">
    <header class="header">
        <div class="progress-container">
            <div class="progress-track">
                <div class="progress-fill" style="width: {progressPercent}%"></div>
            </div>
            <span class="progress-text">{progress.current} / {progress.total}</span>
        </div>

        <button class="btn-icon" onclick={onExit} aria-label="退出測驗">
            <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
            >
                <path d="M18 6 6 18" />
                <path d="m6 6 12 12" />
            </svg>
        </button>
    </header>

    <main class="content">
        {@render children()}
    </main>
</div>

<style>
    .quiz-shell {
        display: flex;
        flex-direction: column;
        width: 100%;
        max-width: 640px; /* Notion-like reading width */
        margin: 0 auto;
        padding: 1rem;
        min-height: 100%;
    }

    .header {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding-bottom: 2rem;
    }

    .progress-container {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .progress-track {
        flex: 1;
        height: 6px;
        background-color: var(--color-surface-hover);
        border-radius: 999px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        background-color: var(--color-accent);
        border-radius: 999px;
        transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .progress-text {
        font-size: 0.75rem;
        font-family: var(--font-mono, monospace);
        color: var(--color-content-tertiary);
        min-width: 3.5em;
        text-align: right;
    }

    .btn-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 6px;
        background: transparent;
        border: none;
        color: var(--color-content-tertiary);
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .btn-icon:hover {
        background-color: var(--color-surface-hover);
        color: var(--color-content-primary);
    }

    .content {
        flex: 1;
        display: flex;
        flex-direction: column;
        /* Animation for entering questions */
        animation: fadeIn 0.3s ease-out;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
</style>
