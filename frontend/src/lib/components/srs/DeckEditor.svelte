<script lang="ts">
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import type { VocabIndexItem } from "$lib/types/vocab";
    import { isWordIndexItem } from "$lib/types/vocab";

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
    let successMessage: string | null = $state(null);
    let isDropdownOpen = $state(false);
    let searchInputEl: HTMLInputElement | null = $state(null);
    let isSelectingItem = $state(false);
    let blurTimeoutId: ReturnType<typeof setTimeout> | null = null;
    let successTimeoutId: ReturnType<typeof setTimeout> | null = null;
    let isPenMode = $state(false);

    const selectedSet = $derived(new Set(selectedLemmas));

    // Fuzzy search scoring: calculate similarity between query and word
    function fuzzyScore(query: string, text: string): number {
        const q = query.toLowerCase();
        const t = text.toLowerCase();

        if (t === q) return 100; // Exact match
        if (t.startsWith(q)) return 80; // Prefix match (prioritized)
        if (t.includes(q)) return 50; // Substring match

        // Character-level fuzzy match: score consecutive character matches
        let score = 0;
        let textIdx = 0;
        let lastMatchIdx = -1;

        for (let i = 0; i < q.length && textIdx < t.length; i++) {
            const idx = t.indexOf(q[i], textIdx);
            if (idx === -1) {
                return 0; // Query character not found
            }
            const gap = idx - lastMatchIdx - 1;
            score += 10 - (gap > 0 ? Math.min(gap, 5) : 0); // Consecutive matches score higher
            textIdx = idx + 1;
            lastMatchIdx = idx;
        }

        return Math.max(0, score);
    }

    const searchResults = $derived.by(() => {
        const query = searchQuery.trim();
        if (!query || !vocab.index) return [];

        const results: Array<VocabIndexItem & { score: number }> = [];

        for (const item of vocab.index) {
            if (selectedSet.has(item.lemma)) continue;

            const score = fuzzyScore(query, item.lemma);
            if (score > 0) {
                results.push({ ...item, score });
            }
        }

        // Sort by score, take top 8
        return results.sort((a, b) => b.score - a.score).slice(0, 8);
    });

    // Parse pasted words (supports multiple delimiters)
    function parsePastedWords(text: string): string[] {
        const words = text
            .split(/[\s,;，；\n\r]+/) // Support space, comma, semicolon, newline, etc.
            .map((w) => w.trim())
            .filter((w) => w.length > 0);

        return words;
    }

    // Add multiple words at once
    function addMultipleWords(words: string[]) {
        const newLemmas: string[] = [];
        const notFound: string[] = [];

        // Build index map for faster lookup
        const indexMap = new Map(
            (vocab.index || []).map((item) => [item.lemma.toLowerCase(), item.lemma]),
        );

        for (const word of words) {
            const normalizedWord = word.trim();
            if (!normalizedWord) continue;

            // Exact match (case-insensitive)
            const found = indexMap.get(normalizedWord.toLowerCase());
            if (found && !selectedSet.has(found)) {
                newLemmas.push(found);
                selectedSet.add(found);
            } else if (!found) {
                notFound.push(normalizedWord);
            }
        }

        if (newLemmas.length > 0) {
            selectedLemmas = [...selectedLemmas, ...newLemmas];
            showSuccessMessage(
                `已加入 ${newLemmas.length} 個單字${notFound.length > 0 ? `（${notFound.join("、")} 找不到）` : ""}`,
            );
        } else if (notFound.length > 0) {
            error = `找不到單字：${notFound.join("、")}`;
        }
    }

    function showSuccessMessage(message: string) {
        successMessage = message;
        error = null;

        if (successTimeoutId) {
            clearTimeout(successTimeoutId);
        }
        successTimeoutId = setTimeout(() => {
            successMessage = null;
            successTimeoutId = null;
        }, 3000);
    }

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

    // Handle paste event
    function handlePaste(e: ClipboardEvent) {
        e.preventDefault();
        const text = e.clipboardData?.getData("text/plain");
        if (text) {
            const words = parsePastedWords(text);
            if (words.length > 0) {
                addMultipleWords(words);
            }
        }
    }

    // Detect Apple Pencil / stylus pen
    function handlePointerDown(e: PointerEvent) {
        if (e.pointerType === "pen") {
            isPenMode = true;
        }
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
                class:pen-mode={isPenMode}
                onpointerdown={handlePointerDown}
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
                        onpaste={handlePaste}
                        onpointerdown={handlePointerDown}
                        class="search-input"
                        class:pen-mode={isPenMode}
                        placeholder="搜尋或貼上多個單字（逗號/空格/換行分隔）"
                        autocomplete="off"
                    />
                </div>

                {#if showDropdown}
                    <div class="dropdown" class:pen-mode={isPenMode}>
                        {#each searchResults as item}
                            <button
                                type="button"
                                class="dropdown-item"
                                onpointerdown={handleItemPointerDown}
                                onclick={() => handleItemClick(item.lemma)}
                            >
                                <span class="item-lemma">{item.lemma}</span>
                                <span class="item-pos">{isWordIndexItem(item) ? item.primary_pos : ""}</span>
                            </button>
                        {/each}
                    </div>
                {:else if isDropdownOpen && searchQuery.trim() && searchResults.length === 0}
                    <div class="dropdown" class:pen-mode={isPenMode}>
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

        {#if successMessage}
            <div class="toast toast-success">
                <span class="toast-dot"></span>
                <span class="toast-text">{successMessage}</span>
            </div>
        {/if}

        {#if error}
            <div class="toast toast-error">
                <span class="toast-dot"></span>
                <span class="toast-text">{error}</span>
            </div>
        {/if}
    </div>

    <div class="editor-footer" class:pen-mode={isPenMode}>
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

    .field-input.pen-mode {
        padding: 0.875rem 1rem;
        font-size: 1rem;
        min-height: 48px;
        border-radius: 0.5rem;
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

    .search-input.pen-mode {
        padding: 0.875rem 1rem 0.875rem 2.75rem;
        font-size: 1rem;
        min-height: 48px;
        border-radius: 0.5rem;
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
        max-height: 280px;
        overflow-y: auto;
        background-color: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 0.5rem;
        box-shadow: var(--shadow-float);
        z-index: 200;
    }

    .dropdown::-webkit-scrollbar {
        width: 6px;
    }

    .dropdown::-webkit-scrollbar-track {
        background: transparent;
    }

    .dropdown::-webkit-scrollbar-thumb {
        background-color: var(--color-scrollbar);
        border-radius: 3px;
    }

    .dropdown::-webkit-scrollbar-thumb:hover {
        background-color: var(--color-scrollbar-hover);
    }

    .dropdown-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: 0.625rem 0.875rem;
        text-align: left;
        background: none;
        border: none;
        cursor: pointer;
        transition: background-color 0.1s ease;
    }

    .dropdown.pen-mode .dropdown-item {
        padding: 0.875rem 1rem;
        min-height: 48px;
    }

    .dropdown-item:hover {
        background-color: var(--color-surface-hover);
    }

    .dropdown-item:not(:last-child) {
        border-bottom: none;
    }

    .item-lemma {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--color-content-primary);
    }

    .item-pos {
        font-size: 0.6875rem;
        font-weight: 500;
        color: var(--color-content-secondary);
        text-transform: uppercase;
    }

    .dropdown-empty {
        padding: 1rem;
        font-size: 0.875rem;
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

    .selected-area::-webkit-scrollbar {
        width: 6px;
    }

    .selected-area::-webkit-scrollbar-track {
        background: transparent;
    }

    .selected-area::-webkit-scrollbar-thumb {
        background-color: var(--color-scrollbar);
        border-radius: 3px;
    }

    .selected-area::-webkit-scrollbar-thumb:hover {
        background-color: var(--color-scrollbar-hover);
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
        transition: all 0.15s ease;
        height: fit-content;
    }

    .word-chip:hover {
        border-color: var(--color-border-hover);
        background-color: var(--color-surface-hover);
    }

    .chip-x {
        width: 0.875rem;
        height: 0.875rem;
        color: var(--color-content-tertiary);
        transition: color 0.15s ease;
    }

    .word-chip:hover .chip-x {
        color: var(--color-content-secondary);
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

    /* Toast notification: subtle and refined design */
    .toast {
        display: flex;
        align-items: center;
        gap: 0.625rem;
        padding: 0.75rem 1rem;
        font-size: 0.8125rem;
        background-color: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 0.5rem;
        box-shadow: var(--shadow-card);
        animation: toastIn 0.2s ease-out;
    }

    .toast-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .toast-success .toast-dot {
        background-color: var(--color-srs-good);
    }

    .toast-error .toast-dot {
        background-color: var(--color-srs-again);
    }

    .toast-text {
        color: var(--color-content-secondary);
        line-height: 1.4;
    }

    @keyframes toastIn {
        from {
            opacity: 0;
            transform: translateY(-4px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .editor-footer {
        display: flex;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-top: 1px solid var(--color-border);
    }

    .editor-footer.pen-mode {
        padding: 1.25rem;
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

    .editor-footer.pen-mode .btn-secondary,
    .editor-footer.pen-mode .btn-primary {
        padding: 0.875rem 1.25rem;
        min-height: 48px;
        font-size: 1rem;
        border-radius: 0.5rem;
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
