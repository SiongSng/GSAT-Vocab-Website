<script lang="ts">
    import { getAppStore, setMode } from "$lib/stores/app.svelte";
    import type { ViewMode } from "$lib/types";

    const app = getAppStore();

    function handleModeChange(mode: ViewMode) {
        setMode(mode);
    }
</script>

{#if app.isMobile}
    <nav class="bottom-nav">
        <div class="nav-pill">
            <button
                class="nav-item"
                class:active={app.mode === "browse"}
                onclick={() => handleModeChange("browse")}
                aria-label="瀏覽單字"
            >
                <svg
                    class="nav-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                >
                    <path
                        d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
                    />
                </svg>
            </button>

            <button
                class="nav-item"
                class:active={app.mode === "flashcard"}
                onclick={() => handleModeChange("flashcard")}
                aria-label="字卡學習"
            >
                <svg
                    class="nav-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                >
                    <path
                        d="M6 6.878V6a2.25 2.25 0 0 1 2.25-2.25h7.5A2.25 2.25 0 0 1 18 6v.878m-12 0c.235-.083.487-.128.75-.128h10.5c.263 0 .515.045.75.128m-12 0A2.25 2.25 0 0 0 4.5 9v.878m13.5-3A2.25 2.25 0 0 1 19.5 9v.878m0 0a2.246 2.246 0 0 0-.75-.128H5.25c-.263 0-.515.045-.75.128m15 0A2.25 2.25 0 0 1 21 12v6a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18v-6c0-1.007.661-1.859 1.572-2.145"
                    />
                </svg>
            </button>

            <button
                class="nav-item"
                class:active={app.mode === "quiz"}
                onclick={() => handleModeChange("quiz")}
                aria-label="測驗模式"
            >
                <svg
                    class="nav-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                >
                    <path
                        d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z"
                    />
                </svg>
            </button>
        </div>
    </nav>
{/if}

<style>
    .bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 50;
        display: flex;
        justify-content: center;
        padding: 0.75rem 1rem calc(env(safe-area-inset-bottom, 0px) + 0.75rem);
        pointer-events: none;
    }

    .nav-pill {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 9999px;
        padding: 0.375rem;
        box-shadow:
            0 4px 20px rgba(0, 0, 0, 0.1),
            0 0 0 1px rgba(0, 0, 0, 0.02);
        pointer-events: auto;
    }

    .nav-item {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 3rem;
        height: 3rem;
        border-radius: 9999px;
        color: var(--color-content-tertiary);
        transition: all 0.2s ease;
        cursor: pointer;
        background: transparent;
        border: none;
    }

    .nav-item:active {
        transform: scale(0.92);
    }

    .nav-item.active {
        color: var(--color-accent);
        background: var(--color-accent-soft);
    }

    .nav-icon {
        width: 1.375rem;
        height: 1.375rem;
    }
</style>
