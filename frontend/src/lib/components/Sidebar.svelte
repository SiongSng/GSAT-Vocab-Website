<script lang="ts">
    import {
        getFilters,
        setSearchTerm,
        setPosFilter,
        setVocabTypeFilter,
        toggleLevel,
        setOfficialOnly,
        setTestedOnly,
        resetFilters,
    } from "$lib/stores/vocab.svelte";
    import { getAppStore, closeSidebar } from "$lib/stores/app.svelte";
    import type { PosFilter, VocabTypeFilter } from "$lib/types";

    const filters = getFilters();
    const app = getAppStore();

    let searchValue = $state(filters.searchTerm);
    let isAdvancedOpen = $state(false);

    const posOptions: { value: PosFilter; label: string; abbr: string }[] = [
        { value: "all", label: "全部", abbr: "全部" },
        { value: "NOUN", label: "名詞", abbr: "n." },
        { value: "VERB", label: "動詞", abbr: "v." },
        { value: "ADJ", label: "形容詞", abbr: "adj." },
        { value: "ADV", label: "副詞", abbr: "adv." },
    ];

    const typeOptions: { value: VocabTypeFilter; label: string }[] = [
        { value: "all", label: "全部" },
        { value: "word", label: "單字" },
        { value: "phrase", label: "片語" },
        { value: "pattern", label: "句型" },
    ];

    const levelOptions = [1, 2, 3, 4, 5, 6];

    let searchTimeout: ReturnType<typeof setTimeout> | null = null;

    function handleSearchInput(e: Event) {
        const target = e.target as HTMLInputElement;
        searchValue = target.value;

        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        searchTimeout = setTimeout(() => {
            setSearchTerm(searchValue);
        }, 300);
    }

    function handlePosClick(pos: PosFilter) {
        setPosFilter(pos);
    }

    function handleTypeClick(type: VocabTypeFilter) {
        setVocabTypeFilter(type);
    }

    function handleLevelClick(level: number) {
        toggleLevel(level);
    }

    function handleOfficialChange(e: Event) {
        const target = e.target as HTMLInputElement;
        setOfficialOnly(target.checked);
    }

    function handleTestedChange(e: Event) {
        const target = e.target as HTMLInputElement;
        setTestedOnly(target.checked);
    }

    function handleReset() {
        resetFilters();
        searchValue = "";
    }

    function handleOverlayClick() {
        closeSidebar();
    }

    function toggleAdvanced() {
        isAdvancedOpen = !isAdvancedOpen;
    }
</script>

{#if app.isSidebarOpen && app.isMobile}
    <button
        class="fixed inset-0 bg-black/20 z-30 lg:hidden"
        onclick={handleOverlayClick}
        aria-label="Close sidebar"
        type="button"
    ></button>
{/if}

<aside
    class="sidebar h-full bg-surface-primary border-r border-border flex flex-col transition-transform duration-300 ease-in-out"
    class:translate-x-0={app.isSidebarOpen || !app.isMobile}
    class:-translate-x-full={!app.isSidebarOpen && app.isMobile}
>
    <div class="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-5">
        <div class="flex items-center justify-between">
            <h2 class="text-sm font-semibold text-content-primary">篩選條件</h2>
            <button
                class="text-xs text-accent hover:underline"
                onclick={handleReset}
                type="button"
            >
                重設
            </button>
        </div>

        <div class="relative">
            <svg
                class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-content-tertiary"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
                />
            </svg>
            <input
                type="text"
                placeholder="搜尋單字..."
                class="w-full bg-surface-secondary border-none rounded-md py-2 pl-9 pr-3 text-sm focus:ring-2 focus:ring-accent/20 focus:outline-none transition placeholder:text-content-tertiary"
                value={searchValue}
                oninput={handleSearchInput}
            />
        </div>

        <div class="space-y-2">
            <div class="flex items-center gap-1.5">
                <h3 class="section-header mb-0">詞彙等級</h3>
                <button
                    class="text-content-tertiary hover:text-content-secondary transition-colors"
                    title="大考中心官方難度分級：1-2 基礎、3-4 中級、5-6 進階"
                    type="button"
                >
                    <svg
                        class="w-3.5 h-3.5"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke-width="1.5"
                        stroke="currentColor"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z"
                        />
                    </svg>
                </button>
            </div>
            <p class="text-xs text-content-tertiary mb-2">
                1-2 基礎 · 3-4 中級 · 5-6 進階
            </p>
            <div class="flex gap-1.5">
                {#each levelOptions as level}
                    <button
                        class="level-chip"
                        class:active={filters.levels.includes(level)}
                        onclick={() => handleLevelClick(level)}
                        type="button"
                    >
                        {level}
                    </button>
                {/each}
            </div>
        </div>

        <div class="space-y-2">
            <h3 class="section-header mb-0">詞彙類型</h3>
            <div class="flex flex-wrap gap-1.5">
                {#each typeOptions as option}
                    <button
                        class="filter-chip"
                        class:active={filters.vocabType === option.value}
                        onclick={() => handleTypeClick(option.value)}
                        type="button"
                    >
                        {option.label}
                    </button>
                {/each}
            </div>
        </div>

        <div class="space-y-2">
            <h3 class="section-header mb-0">詞性</h3>
            <div class="flex flex-wrap gap-1.5">
                {#each posOptions as option}
                    <button
                        class="filter-chip"
                        class:active={filters.pos === option.value}
                        onclick={() => handlePosClick(option.value)}
                        type="button"
                    >
                        {option.label}
                    </button>
                {/each}
            </div>
        </div>

        <div class="space-y-2">
            <button
                class="flex items-center justify-between w-full text-left"
                onclick={toggleAdvanced}
                type="button"
            >
                <h3 class="section-header mb-0">進階篩選</h3>
                <svg
                    class="w-4 h-4 text-content-tertiary transition-transform duration-200"
                    class:rotate-180={isAdvancedOpen}
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="m19.5 8.25-7.5 7.5-7.5-7.5"
                    />
                </svg>
            </button>

            {#if isAdvancedOpen}
                <div class="space-y-3 pt-1">
                    <label class="flex items-start gap-2.5 cursor-pointer group">
                        <input
                            type="checkbox"
                            checked={filters.officialOnly}
                            onchange={handleOfficialChange}
                        />
                        <div class="flex-1 min-w-0">
                            <span
                                class="text-sm text-content-secondary group-hover:text-content-primary transition-colors block"
                            >
                                僅顯示大考中心詞彙表
                            </span>
                            <span class="text-xs text-content-tertiary">
                                官方公布的 7000 單字範圍
                            </span>
                        </div>
                    </label>

                    <label class="flex items-start gap-2.5 cursor-pointer group">
                        <input
                            type="checkbox"
                            checked={filters.testedOnly}
                            onchange={handleTestedChange}
                        />
                        <div class="flex-1 min-w-0">
                            <span
                                class="text-sm text-content-secondary group-hover:text-content-primary transition-colors block"
                            >
                                僅顯示曾出現在考題的詞彙
                            </span>
                            <span class="text-xs text-content-tertiary">
                                作為答案、選項或翻譯關鍵字
                            </span>
                        </div>
                    </label>
                </div>
            {/if}
        </div>
    </div>
</aside>

<style>
    .section-header {
        font-size: 0.8125rem;
        font-weight: 600;
        color: var(--color-section-header);
        margin-bottom: 0.75rem;
    }

    .filter-chip {
        padding: 0.375rem 0.75rem;
        background-color: var(--color-surface-page);
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.8125rem;
        color: var(--color-content-secondary);
        transition: all 0.15s ease;
        cursor: pointer;
        border: 1px solid transparent;
    }

    .filter-chip:hover {
        background-color: var(--color-surface-hover);
        border-color: var(--color-border);
    }

    .filter-chip.active {
        background-color: var(--color-accent-soft);
        color: var(--color-accent);
        border-color: transparent;
    }

    .level-chip {
        width: 2rem;
        height: 2rem;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--color-surface-page);
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8125rem;
        color: var(--color-content-secondary);
        transition: all 0.15s ease;
        cursor: pointer;
        border: 1px solid transparent;
    }

    .level-chip:hover {
        background-color: var(--color-surface-hover);
        border-color: var(--color-border);
    }

    .level-chip.active {
        background-color: var(--color-accent-soft);
        color: var(--color-accent);
        border-color: transparent;
    }

    .sidebar {
        width: 15rem;
        min-width: 200px;
        flex-shrink: 0;
    }

    @media (max-width: 1023px) {
        .sidebar {
            position: absolute;
            top: 0;
            bottom: 0;
            left: 0;
            z-index: 40;
            width: 80%;
            max-width: 18rem;
        }
    }
</style>
