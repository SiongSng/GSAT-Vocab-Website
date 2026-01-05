<script lang="ts">
    import { getAppStore, setMode } from "$lib/stores/app.svelte";
    import type { ViewMode } from "$lib/types";
    import SyncButton from "$lib/components/srs/SyncButton.svelte";
    import StreakBadge from "$lib/components/stats/StreakBadge.svelte";

    const app = getAppStore();

    function handleModeChange(mode: ViewMode) {
        setMode(mode);
    }
</script>

<header class="header">
    <div class="header-left">
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 32 32"
            class="logo-icon"
        >
            <rect
                x="4"
                y="6"
                width="18"
                height="14"
                rx="2"
                fill="currentColor"
                class="text-accent/25"
            />
            <rect
                x="7"
                y="9"
                width="18"
                height="14"
                rx="2"
                fill="currentColor"
                class="text-accent/50"
            />
            <rect
                x="10"
                y="12"
                width="18"
                height="14"
                rx="2"
                fill="currentColor"
                class="text-accent"
            />
        </svg>
        <button class="logo-text" onclick={() => handleModeChange("browse")}>
            學測高頻單字
        </button>
    </div>

    <div class="header-right">
        <SyncButton />
        <StreakBadge />

        {#if !app.isMobile}
            <div class="nav-divider"></div>

            <button
                class="mode-btn"
                class:active={app.mode === "browse"}
                onclick={() => handleModeChange("browse")}
                title="瀏覽模式"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-5 h-5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
                    />
                </svg>
            </button>

            <button
                class="mode-btn"
                class:active={app.mode === "flashcard"}
                onclick={() => handleModeChange("flashcard")}
                title="字卡模式"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-5 h-5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M6 6.878V6a2.25 2.25 0 0 1 2.25-2.25h7.5A2.25 2.25 0 0 1 18 6v.878m-12 0c.235-.083.487-.128.75-.128h10.5c.263 0 .515.045.75.128m-12 0A2.25 2.25 0 0 0 4.5 9v.878m13.5-3A2.25 2.25 0 0 1 19.5 9v.878m0 0a2.246 2.246 0 0 0-.75-.128H5.25c-.263 0-.515.045-.75.128m15 0A2.25 2.25 0 0 1 21 12v6a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18v-6c0-1.007.661-1.859 1.572-2.145"
                    />
                </svg>
            </button>

            <button
                class="mode-btn"
                class:active={app.mode === "quiz"}
                onclick={() => handleModeChange("quiz")}
                title="測驗模式"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-5 h-5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"
                    />
                </svg>
            </button>
        {/if}
    </div>
</header>

<style>
    .header {
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.625rem 1rem;
        background-color: var(--color-surface-primary);
        border-bottom: 1px solid var(--color-border);
        z-index: 20;
    }

    @media (min-width: 640px) {
        .header {
            padding: 0.625rem 1.5rem;
        }
    }

    .header-left {
        display: flex;
        align-items: center;
        gap: 0.625rem;
    }

    .logo-icon {
        width: 1.625rem;
        height: 1.625rem;
    }

    .logo-text {
        font-size: 1.125rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        color: var(--color-content-primary);
        cursor: pointer;
        background: none;
        border: none;
        padding: 0;
        transition: color 0.15s ease;
    }

    .logo-text:hover {
        color: var(--color-accent);
    }

    .header-right {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    @media (min-width: 640px) {
        .header-right {
            gap: 0.5rem;
        }
    }

    .nav-divider {
        width: 1px;
        height: 1rem;
        background-color: var(--color-border);
        margin: 0 0.25rem;
    }

    .mode-btn {
        padding: 0.5rem;
        border-radius: 0.375rem;
        transition: all 0.15s ease;
        color: var(--color-content-tertiary);
        background: none;
        border: none;
        cursor: pointer;
    }

    .mode-btn:hover {
        background-color: var(--color-surface-hover);
        color: var(--color-content-secondary);
    }

    .mode-btn:focus-visible {
        outline: none;
        box-shadow:
            0 0 0 2px var(--color-surface-primary),
            0 0 0 4px var(--color-accent);
    }

    .mode-btn.active {
        background-color: var(--color-accent-soft);
        color: var(--color-accent);
    }
</style>
