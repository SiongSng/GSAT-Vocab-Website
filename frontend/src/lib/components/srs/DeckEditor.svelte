<script lang="ts">
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import type { VocabIndexItem } from "$lib/types/vocab";

    interface Props {
        initialName: string;
        initialLemmas: string[];
        onSave: (name: string, lemmas: string[]) => void;
        onCancel: () => void;
        isEditing: boolean;
    }

    let { initialName, initialLemmas, onSave, onCancel, isEditing }: Props =
        $props();

    const vocab = getVocabStore();

    // svelte-ignore state_referenced_locally
    let deckName = $state(initialName);
    // svelte-ignore state_referenced_locally
    let selectedLemmas: string[] = $state([...initialLemmas]);
    let searchQuery = $state("");
    let error: string | null = $state(null);
    let isDropdownOpen = $state(false);
    let searchInputEl: HTMLInputElement | null = $state(null);
    let isSelectingItem = $state(false);
    let blurTimeoutId: ReturnType<typeof setTimeout> | null = null;

    const selectedSet = $derived(new Set(selectedLemmas));

    const searchResults = $derived.by(() => {
        const query = searchQuery.trim().toLowerCase();
        if (!query || !vocab.index) return [];

        const results: VocabIndexItem[] = [];
        for (const item of vocab.index) {
            if (selectedSet.has(item.lemma)) continue;
            if (item.lemma.toLowerCase().startsWith(query)) {
                results.push(item);
                if (results.length >= 8) break;
            }
        }
        return results;
    });

    const showDropdown = $derived(
        isDropdownOpen && searchQuery.trim() && searchResults.length > 0,
    );

    function addWord(lemma: string) {
        if (!selectedSet.has(lemma)) {
            selectedLemmas = [...selectedLemmas, lemma];
        }
        searchQuery = "";
        isSelectingItem = false;
        searchInputEl?.focus();
    }

    function removeWord(lemma: string) {
        selectedLemmas = selectedLemmas.filter((l) => l !== lemma);
    }

    function handleSave() {
        const name = deckName.trim();
        if (!name) {
            error = "請輸入卡組名稱";
            return;
        }
        if (selectedLemmas.length === 0) {
            error = "請至少加入一個單字";
            return;
        }
        error = null;
        onSave(name, selectedLemmas);
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter" && searchResults.length > 0) {
            e.preventDefault();
            addWord(searchResults[0].lemma);
        } else if (e.key === "Escape") {
            isDropdownOpen = false;
        }
    }

    function handleInputFocus() {
        isDropdownOpen = true;
    }

    function handleInput() {
        isDropdownOpen = true;
    }

    function handleInputBlur() {
        if (blurTimeoutId) {
            clearTimeout(blurTimeoutId);
        }
        blurTimeoutId = setTimeout(() => {
            if (!isSelectingItem) {
                isDropdownOpen = false;
            }
            blurTimeoutId = null;
        }, 200);
    }

    function handleItemPointerDown() {
        isSelectingItem = true;
    }

    function handleItemClick(lemma: string) {
        addWord(lemma);
    }
</script>

<div class="deck-editor">
    <div class="editor-header">
        <h3 class="text-lg font-semibold text-content-primary tracking-tight">
            {isEditing ? "編輯卡組" : "建立卡組"}
        </h3>
        <button
            type="button"
            onclick={onCancel}
            class="p-1.5 -m-1.5 rounded-md text-content-tertiary hover:text-content-primary hover:bg-surface-hover transition-colors"
            aria-label="關閉"
        >
            <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                stroke-width="1.5"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M6 18 18 6M6 6l12 12"
                />
            </svg>
        </button>
    </div>

    <div class="editor-body">
        <div class="field">
            <label for="deck-name-input" class="field-label">名稱</label>
            <input
                id="deck-name-input"
                type="text"
                bind:value={deckName}
                class="field-input"
                placeholder="例：高一上 Unit 1"
            />
        </div>

        <div class="field">
            <label for="word-search" class="field-label">新增單字</label>
            <div class="search-container">
                <div class="search-box">
                    <svg
                        class="search-icon"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        stroke-width="1.5"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
                        />
                    </svg>
                    <input
                        id="word-search"
                        type="text"
                        bind:this={searchInputEl}
                        bind:value={searchQuery}
                        onkeydown={handleKeydown}
                        onfocus={handleInputFocus}
                        oninput={handleInput}
                        onblur={handleInputBlur}
                        class="search-input"
                        placeholder="搜尋單字..."
                        autocomplete="off"
                    />
                </div>

                {#if showDropdown}
                    <div class="dropdown">
                        {#each searchResults as item}
                            <button
                                type="button"
                                class="dropdown-item"
                                onpointerdown={handleItemPointerDown}
                                onclick={() => handleItemClick(item.lemma)}
                            >
                                <span class="item-lemma">{item.lemma}</span>
                                <span class="item-pos">{item.primary_pos}</span>
                            </button>
                        {/each}
                    </div>
                {:else if isDropdownOpen && searchQuery.trim() && searchResults.length === 0}
                    <div class="dropdown">
                        <div class="dropdown-empty">找不到此單字</div>
                    </div>
                {/if}
            </div>
        </div>

        <div class="field selected-field">
            <div class="field-label-row">
                <span class="field-label">已加入</span>
                <span class="field-count">{selectedLemmas.length} 字</span>
            </div>
            <div class="selected-area">
                {#if selectedLemmas.length > 0}
                    {#each selectedLemmas as lemma}
                        <button
                            type="button"
                            class="word-chip"
                            onclick={() => removeWord(lemma)}
                        >
                            <span>{lemma}</span>
                            <svg
                                class="chip-x"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                                stroke-width="2"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M6 18 18 6M6 6l12 12"
                                />
                            </svg>
                        </button>
                    {/each}
                {:else}
                    <div class="empty-hint">搜尋並點選單字加入</div>
                {/if}
            </div>
        </div>

        {#if error}
            <div class="error-box">
                <svg
                    class="w-4 h-4 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
                    />
                </svg>
                {error}
            </div>
        {/if}
    </div>

    <div class="editor-footer">
        <button type="button" onclick={onCancel} class="btn-secondary">
            取消
        </button>
        <button type="button" onclick={handleSave} class="btn-primary">
            {isEditing ? "儲存變更" : "建立卡組"}
        </button>
    </div>
</div>

<style>
    .deck-editor {
        display: flex;
        flex-direction: column;
    }

    .editor-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--color-border);
    }

    .editor-body {
        padding: 1.25rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .field {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .field-label {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--color-content-secondary);
    }

    .field-label-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .field-count {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
    }

    .field-input {
        padding: 0.625rem 0.875rem;
        font-size: 0.875rem;
        background-color: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 0.375rem;
        transition: all 0.15s ease;
    }

    .field-input:focus {
        outline: none;
        border-color: var(--color-accent);
        box-shadow: 0 0 0 2px var(--color-accent-soft);
    }

    .search-container {
        position: relative;
    }

    .search-box {
        position: relative;
    }

    .search-icon {
        position: absolute;
        left: 0.875rem;
        top: 50%;
        transform: translateY(-50%);
        width: 1rem;
        height: 1rem;
        color: var(--color-content-tertiary);
        pointer-events: none;
    }

    .search-input {
        width: 100%;
        padding: 0.625rem 0.875rem 0.625rem 2.5rem;
        font-size: 0.875rem;
        background-color: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 0.375rem;
        transition: all 0.15s ease;
    }

    .search-input:focus {
        outline: none;
        border-color: var(--color-accent);
        box-shadow: 0 0 0 2px var(--color-accent-soft);
    }

    .dropdown {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        margin-top: 0.25rem;
        background-color: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 0.375rem;
        box-shadow: var(--shadow-float);
        z-index: 10;
        overflow: hidden;
    }

    .dropdown-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        width: 100%;
        padding: 0.625rem 0.875rem;
        text-align: left;
        transition: background-color 0.1s ease;
    }

    .dropdown-item:hover {
        background-color: var(--color-surface-hover);
    }

    .dropdown-item:not(:last-child) {
        border-bottom: 1px solid var(--color-border);
    }

    .item-lemma {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--color-content-primary);
    }

    .item-pos {
        font-size: 0.6875rem;
        font-weight: 500;
        color: var(--color-content-tertiary);
        text-transform: uppercase;
    }

    .dropdown-empty {
        padding: 0.75rem;
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
        text-align: center;
    }

    .selected-field {
        flex: 1;
        min-height: 0;
    }

    .selected-area {
        flex: 1;
        min-height: 100px;
        max-height: 180px;
        padding: 0.75rem;
        background-color: var(--color-surface-page);
        border: 1px solid var(--color-border);
        border-radius: 0.375rem;
        overflow-y: auto;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-content: flex-start;
    }

    .word-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.375rem 0.625rem;
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--color-content-primary);
        background-color: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 0.375rem;
        transition: all 0.1s ease;
        height: fit-content;
    }

    .word-chip:hover {
        border-color: var(--color-srs-again);
        background-color: var(--color-srs-again-soft);
    }

    .chip-x {
        width: 0.875rem;
        height: 0.875rem;
        color: var(--color-content-tertiary);
        transition: color 0.1s ease;
    }

    .word-chip:hover .chip-x {
        color: var(--color-srs-again);
    }

    .empty-hint {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 80px;
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
    }

    .error-box {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.625rem 0.75rem;
        font-size: 0.875rem;
        color: var(--color-srs-again);
        background-color: var(--color-srs-again-soft);
        border-radius: 0.375rem;
    }

    .editor-footer {
        display: flex;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-top: 1px solid var(--color-border);
    }

    .btn-secondary {
        flex: 1;
        padding: 0.625rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--color-content-secondary);
        background-color: var(--color-surface-page);
        border: 1px solid var(--color-border);
        border-radius: 0.375rem;
        transition: all 0.15s ease;
    }

    .btn-secondary:hover {
        background-color: var(--color-surface-hover);
    }

    .btn-primary {
        flex: 1;
        padding: 0.625rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        color: white;
        background-color: var(--color-content-primary);
        border-radius: 0.375rem;
        transition: all 0.15s ease;
    }

    .btn-primary:hover {
        background-color: var(--color-content-primary-hover);
    }
</style>
