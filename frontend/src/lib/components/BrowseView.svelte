<script lang="ts">
    import WordList from "./WordList.svelte";
    import WordDetail from "./WordDetail.svelte";
    import Sidebar from "./Sidebar.svelte";
    import { getVocabStore, getFilters, setSortBy } from "$lib/stores/vocab.svelte";
    import {
        getAppStore,
        toggleSidebar,
        toggleGridMode,
    } from "$lib/stores/app.svelte";
    import type { SortOption } from "$lib/types";

    const vocab = getVocabStore();
    const filters = getFilters();
    const app = getAppStore();

    let isSortDropdownOpen = $state(false);

    const sortOptions: { value: SortOption; label: string }[] = [
        { value: "importance_desc", label: "重要性優先" },
        { value: "count_desc", label: "出現次數 (多→少)" },
        { value: "count_asc", label: "出現次數 (少→多)" },
        { value: "year_spread_desc", label: "年份分布" },
        { value: "alphabetical_asc", label: "字母順序 A-Z" },
        { value: "alphabetical_desc", label: "字母順序 Z-A" },
        { value: "level_asc", label: "等級 (低→高)" },
        { value: "level_desc", label: "等級 (高→低)" },
    ];

    function getCurrentSortLabel(): string {
        return sortOptions.find((o) => o.value === filters.sortBy)?.label ?? "重要性優先";
    }

    function handleSortSelect(option: SortOption) {
        setSortBy(option);
        isSortDropdownOpen = false;
    }

    function toggleSortDropdown() {
        isSortDropdownOpen = !isSortDropdownOpen;
    }

    function closeSortDropdown() {
        isSortDropdownOpen = false;
    }
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
                    <div class="relative">
                        <button
                            class="sort-btn"
                            onclick={toggleSortDropdown}
                            type="button"
                        >
                            <svg
                                class="w-4 h-4"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="1.5"
                                stroke="currentColor"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M3 7.5 7.5 3m0 0L12 7.5M7.5 3v13.5m13.5 0L16.5 21m0 0L12 16.5m4.5 4.5V7.5"
                                />
                            </svg>
                            <span class="text-xs hidden sm:inline">{getCurrentSortLabel()}</span>
                            <svg
                                class="w-3 h-3 hidden sm:block"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="2"
                                stroke="currentColor"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="m19.5 8.25-7.5 7.5-7.5-7.5"
                                />
                            </svg>
                        </button>

                        {#if isSortDropdownOpen}
                            <button
                                class="fixed inset-0 z-10"
                                onclick={closeSortDropdown}
                                aria-label="Close dropdown"
                                type="button"
                            ></button>
                            <div class="sort-dropdown">
                                {#each sortOptions as option}
                                    <button
                                        class="sort-option"
                                        class:active={filters.sortBy === option.value}
                                        onclick={() => handleSortSelect(option.value)}
                                        type="button"
                                    >
                                        {#if filters.sortBy === option.value}
                                            <svg
                                                class="w-4 h-4 text-accent"
                                                xmlns="http://www.w3.org/2000/svg"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke-width="2"
                                                stroke="currentColor"
                                            >
                                                <path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    d="m4.5 12.75 6 6 9-13.5"
                                                />
                                            </svg>
                                        {:else}
                                            <span class="w-4"></span>
                                        {/if}
                                        {option.label}
                                    </button>
                                {/each}
                            </div>
                        {/if}
                    </div>
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
                                d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25A2.25 2.25 0 0 1 13.5 8.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"
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

    .sort-btn {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.375rem 0.5rem;
        border-radius: 6px;
        font-weight: 500;
        color: var(--color-content-secondary);
        transition: all 0.15s ease;
        cursor: pointer;
        border: 1px solid transparent;
        background-color: transparent;
    }

    .sort-btn:hover {
        background-color: var(--color-surface-hover);
        border-color: var(--color-border);
    }

    .sort-dropdown {
        position: absolute;
        top: 100%;
        right: 0;
        margin-top: 0.25rem;
        min-width: 10rem;
        background-color: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 8px;
        box-shadow: var(--shadow-float);
        z-index: 20;
        padding: 0.25rem;
    }

    .sort-option {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        width: 100%;
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        font-size: 0.8125rem;
        color: var(--color-content-secondary);
        transition: all 0.15s ease;
        cursor: pointer;
        border: none;
        background-color: transparent;
        text-align: left;
    }

    .sort-option:hover {
        background-color: var(--color-surface-hover);
    }

    .sort-option.active {
        color: var(--color-accent);
        background-color: var(--color-accent-soft);
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
