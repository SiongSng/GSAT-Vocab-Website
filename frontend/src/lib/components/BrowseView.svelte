<script lang="ts">
    import WordList from "./WordList.svelte";
    import WordDetail from "./WordDetail.svelte";
    import Sidebar from "./Sidebar.svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import {
        getAppStore,
        toggleSidebar,
        toggleGridMode,
    } from "$lib/stores/app.svelte";

    const vocab = getVocabStore();
    const app = getAppStore();
</script>

<div class="browse-view">
    <Sidebar />

    <div class="browse-content">
        <main class="word-list-section">
            <div class="results-header">
                <p class="text-sm text-content-secondary">
                    {#if vocab.isLoading}
                        正在載入數據...
                    {:else}
                        找到 {vocab.filteredWords.length} 個符合條件的單詞
                    {/if}
                </p>
                <div class="flex items-center gap-1">
                    <button
                        class="lg:hidden p-1.5 rounded-md hover:bg-surface-hover transition-colors"
                        onclick={toggleSidebar}
                        title="顯示篩選器"
                        type="button"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                            class="w-5 h-5 text-content-tertiary"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75"
                            />
                        </svg>
                    </button>
                    <button
                        class="p-1.5 rounded-md transition-colors"
                        class:bg-accent-soft={app.isGridMode}
                        class:text-accent={app.isGridMode}
                        class:hover:bg-surface-hover={!app.isGridMode}
                        class:text-content-tertiary={!app.isGridMode}
                        onclick={toggleGridMode}
                        title="切換網格視圖"
                        type="button"
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
                                d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25A2.25 2.25 0 0 1 13.5 8.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.
25 0 0 1 13.5 18v-2.25Z"
                            />
                        </svg>
                    </button>
                </div>
            </div>

            <div class="word-list-wrapper">
                <WordList
                    words={vocab.filteredWords}
                    isGridMode={app.isGridMode}
                />
            </div>
        </main>

        <div
            class="detail-wrapper
"
            class:mobile-active={app.isMobileDetailOpen}
        >
            <WordDetail />
        </div>
    </div>
</div>

<style>
    .browse-view {
        display: flex;
        height: 100%;
        overflow: hidden;
    }

    .browse-content {
        display: flex;
        flex: 1;
        height: 100%;
        overflow: hidden;
        position: relative;
    }

    .word-list-section {
        display: flex;
        flex-direction: column;
        width: 320px;
        min-width: 280px;
        max-width: 320px;
        height: 100%;
        background-color: var(--color-surface-primary);
        border-right: 1px solid var(--color-border);
        flex-shrink: 0;
    }

    .results-header {
        flex-shrink: 0;
        padding: 0.875rem 1rem;
        border-bottom: 1px solid var(--color-border);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .word-list-wrapper {
        flex: 1;
        min-height: 0;
        overflow: hidden;
    }

    .detail-wrapper {
        flex: 1;
        height: 100%;
        overflow: hidden;
    }

    @media (max-width: 1023px) {
        .browse-view {
            display: block;
        }

        .browse-content {
            display: block;
            position: relative;
        }

        .word-list-section {
            width: 100%;
            max-width: none;
            height: 100%;
        }

        .detail-wrapper {
            position: absolute;
            inset: 0;
            z-index: 20;
            transform: translateX(100%);
            transition: transform 0.3s ease-in-out;
            background-color: var(--color-surface-page);
        }

        .detail-wrapper.mobile-active {
            transform: translateX(0);
        }
    }
</style>
