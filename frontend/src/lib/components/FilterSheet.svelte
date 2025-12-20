<script lang="ts">
    import BottomSheet from "$lib/components/ui/BottomSheet.svelte";
    import HelpTooltip from "$lib/components/ui/HelpTooltip.svelte";
    import {
        getFilters,
        setPosFilter,
        setVocabTypeFilter,
        toggleLevel,
        setOfficialOnly,
        setTestedOnly,
        resetFilters,
    } from "$lib/stores/vocab.svelte";
    import type { PosFilter, VocabTypeFilter } from "$lib/types";

    interface Props {
        isOpen: boolean;
        onClose: () => void;
    }

    let { isOpen, onClose }: Props = $props();

    const filters = getFilters();

    const posOptions: { value: PosFilter; label: string }[] = [
        { value: "all", label: "全部" },
        { value: "NOUN", label: "名詞" },
        { value: "VERB", label: "動詞" },
        { value: "ADJ", label: "形容詞" },
        { value: "ADV", label: "副詞" },
    ];

    const typeOptions: { value: VocabTypeFilter; label: string }[] = [
        { value: "all", label: "全部" },
        { value: "word", label: "單字" },
        { value: "phrase", label: "片語" },
        { value: "pattern", label: "句型" },
    ];

    const levelOptions = [1, 2, 3, 4, 5, 6];

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
    }
</script>

<BottomSheet {isOpen} {onClose}>
    <div class="filter-content">
        <div class="filter-header">
            <h2 class="text-base font-semibold text-content-primary">
                篩選條件
            </h2>
            <button
                class="text-sm text-accent hover:underline"
                onclick={handleReset}
                type="button"
            >
                重設
            </button>
        </div>

        <div class="filter-section">
            <div class="flex items-center gap-1.5">
                <h3 class="section-header">詞彙等級</h3>
                <HelpTooltip
                    text="大考中心官方難度分級：1-2 基礎、3-4 中級、5-6 進階"
                />
            </div>
            <div class="flex gap-2">
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

        <div class="filter-section">
            <h3 class="section-header">詞彙類型</h3>
            <div class="flex flex-wrap gap-2">
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

        <div class="filter-section">
            <h3 class="section-header">詞性</h3>
            <div class="flex flex-wrap gap-2">
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

        <div class="filter-section">
            <h3 class="section-header">進階篩選</h3>
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
        </div>
    </div>
</BottomSheet>

<style>
    .filter-content {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
    }

    .filter-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .filter-section {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .section-header {
        font-size: 0.8125rem;
        font-weight: 600;
        color: var(--color-section-header);
        line-height: 1;
        margin: 0;
    }

    .filter-chip {
        padding: 0.5rem 0.875rem;
        background-color: var(--color-surface-page);
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.875rem;
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
        width: 2.5rem;
        height: 2.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--color-surface-page);
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.875rem;
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
</style>
