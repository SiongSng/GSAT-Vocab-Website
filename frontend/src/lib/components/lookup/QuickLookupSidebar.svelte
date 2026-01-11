<script lang="ts">
    import {
        getWordLookupStore,
        closeLookupItem,
        closeAllLookups,
    } from "$lib/stores/word-lookup.svelte";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";
    import HighlightedText from "$lib/components/ui/HighlightedText.svelte";
    import WordDetailModal from "$lib/components/srs/WordDetailModal.svelte";
    import type { VocabEntryUnion, WordEntry, PhraseEntry, VocabSense } from "$lib/types/vocab";
    import { isWordEntry, isPhraseEntry } from "$lib/types/vocab";

    const lookup = getWordLookupStore();

    let modalEntry = $state<WordEntry | PhraseEntry | null>(null);
    let isModalOpen = $state(false);

    function getSenses(entry: VocabEntryUnion | null): VocabSense[] {
        if (!entry) return [];
        if (isWordEntry(entry) || isPhraseEntry(entry)) {
            return entry.senses ?? [];
        }
        return [];
    }

    function handleWordClick(entry: VocabEntryUnion) {
        if (isWordEntry(entry) || isPhraseEntry(entry)) {
            modalEntry = entry;
            isModalOpen = true;
        }
    }

    function handleCloseModal() {
        isModalOpen = false;
        modalEntry = null;
    }

    function getExample(sense: VocabSense): string | null {
        return sense.generated_example || null;
    }

    function handleClose(lemma: string, e: MouseEvent) {
        e.stopPropagation();
        closeLookupItem(lemma);
    }
</script>

{#if lookup.hasItems && lookup.position === "sidebar"}
    <aside class="sidebar">
        <div class="header">
            <span class="title">Quick Lookup</span>
            <button
                type="button"
                class="icon-btn"
                onclick={closeAllLookups}
                aria-label="Close all"
            >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
            </button>
        </div>

        <div class="content">
            {#each lookup.items as item (item.lemma)}
                {@const senses = getSenses(item.entry)}
                <article class="card">
                    {#if item.isLoading}
                        <div class="card-header">
                            <div class="skeleton" style="width: 80px; height: 22px;"></div>
                        </div>
                        <div class="card-body">
                            <div class="skeleton" style="width: 100%; height: 16px;"></div>
                            <div class="skeleton" style="width: 70%; height: 16px; margin-top: 8px;"></div>
                        </div>
                    {:else if item.entry}
                        <div class="card-header">
                            <button
                                type="button"
                                class="word-link"
                                onclick={() => handleWordClick(item.entry!)}
                            >
                                {item.entry.lemma}
                            </button>
                            <div class="actions">
                                <AudioButton text={item.lemma} size="sm" />
                                <button
                                    type="button"
                                    class="close-btn"
                                    onclick={(e) => handleClose(item.lemma, e)}
                                    aria-label="Close"
                                >
                                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>
                        </div>

                        {#if senses.length > 0}
                            {@const displaySenses = senses.slice(0, 3)}
                            {@const remaining = senses.length - 3}
                            <div class="card-body">
                                {#each displaySenses as sense}
                                    {@const example = getExample(sense)}
                                    <div class="sense">
                                        <p class="def">
                                            {#if sense.pos}<span class="pos">{sense.pos}</span>{/if}{sense.zh_def}
                                        </p>
                                        {#if example}
                                            <p class="example"><HighlightedText
                                                text={example}
                                                highlightLemma={item.entry?.lemma}
                                                disableClickable={true}
                                                variant="subtle"
                                            /></p>
                                        {/if}
                                    </div>
                                {/each}
                                {#if remaining > 0}
                                    <button
                                        type="button"
                                        class="more-btn"
                                        onclick={() => handleWordClick(item.entry!)}
                                    >
                                        +{remaining} 更多
                                    </button>
                                {/if}
                            </div>
                        {/if}
                    {:else}
                        <div class="card-header">
                            <span class="word-not-found">{item.lemma}</span>
                            <button
                                type="button"
                                class="close-btn"
                                onclick={(e) => handleClose(item.lemma, e)}
                                aria-label="Close"
                            >
                                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                        <div class="card-body">
                            <p class="not-found-msg">找不到此單字</p>
                        </div>
                    {/if}
                </article>
            {/each}
        </div>
    </aside>
{/if}

{#if modalEntry}
    <WordDetailModal
        entry={modalEntry}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
    />
{/if}

<style>
    .sidebar {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        width: 340px;
        background: #f8f8f7;
        box-shadow:
            rgba(0, 0, 0, 0.024) 0px 0px 0px 1px,
            rgba(0, 0, 0, 0.05) 0px 3px 6px,
            rgba(0, 0, 0, 0.04) 0px 9px 24px;
        z-index: 90;
        display: flex;
        flex-direction: column;
        animation: slideIn 0.15s ease-out;
    }

    @keyframes slideIn {
        from { opacity: 0; transform: translateX(10px); }
        to { opacity: 1; transform: translateX(0); }
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 16px;
        flex-shrink: 0;
    }

    .title {
        font-size: 11px;
        font-weight: 600;
        color: rgba(55, 53, 47, 0.45);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .icon-btn {
        width: 26px;
        height: 26px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        color: rgba(55, 53, 47, 0.4);
        transition: all 0.12s ease;
    }

    .icon-btn:hover {
        background: rgba(55, 53, 47, 0.08);
        color: rgba(55, 53, 47, 0.7);
    }

    .content {
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        padding: 0 12px 16px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    .card {
        background: white;
        border-radius: 10px;
        box-shadow:
            0 0 0 1px rgba(0, 0, 0, 0.03),
            0 2px 4px rgba(0, 0, 0, 0.04),
            0 4px 12px rgba(0, 0, 0, 0.03);
        overflow: hidden;
        animation: cardIn 0.12s ease-out;
        transition: box-shadow 0.15s ease;
        flex-shrink: 0;
    }

    .card:hover {
        box-shadow:
            0 0 0 1px rgba(0, 0, 0, 0.04),
            0 4px 8px rgba(0, 0, 0, 0.06),
            0 8px 20px rgba(0, 0, 0, 0.04);
    }

    @keyframes cardIn {
        from { opacity: 0; transform: translateY(-6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 14px;
        border-bottom: 1px solid rgba(0, 0, 0, 0.04);
    }

    .word-link {
        font-size: 17px;
        font-weight: 600;
        color: rgb(55, 53, 47);
        letter-spacing: -0.01em;
        transition: color 0.1s;
    }

    .word-link:hover {
        color: #2383e2;
    }

    .actions {
        display: flex;
        align-items: center;
        gap: 2px;
    }

    .close-btn {
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 5px;
        color: rgba(55, 53, 47, 0.35);
        transition: all 0.1s;
    }

    .close-btn:hover {
        background: rgba(55, 53, 47, 0.08);
        color: rgba(55, 53, 47, 0.65);
    }

    .word-not-found {
        font-size: 15px;
        color: rgba(55, 53, 47, 0.5);
    }

    .card-body {
        padding: 14px;
        display: flex;
        flex-direction: column;
        gap: 14px;
    }

    .sense {
        line-height: 1.55;
    }

    .def {
        margin: 0;
        font-size: 14px;
        color: rgb(55, 53, 47);
    }

    .pos {
        font-size: 11px;
        font-weight: 500;
        color: rgba(55, 53, 47, 0.45);
        margin-right: 5px;
    }

    .example {
        margin: 6px 0 0;
        font-size: 13px;
        color: rgba(55, 53, 47, 0.6);
        line-height: 1.65;
    }

    .not-found-msg {
        margin: 0;
        font-size: 13px;
        color: rgba(55, 53, 47, 0.45);
    }

    .more-btn {
        font-size: 13px;
        font-weight: 500;
        color: rgba(55, 53, 47, 0.5);
        padding: 6px 10px;
        margin: -4px -10px 0;
        border-radius: 5px;
        transition: all 0.1s;
        align-self: flex-start;
    }

    .more-btn:hover {
        background: rgba(55, 53, 47, 0.06);
        color: rgba(55, 53, 47, 0.7);
    }

    .skeleton {
        background: linear-gradient(
            90deg,
            rgba(55, 53, 47, 0.06) 0%,
            rgba(55, 53, 47, 0.03) 50%,
            rgba(55, 53, 47, 0.06) 100%
        );
        background-size: 200% 100%;
        border-radius: 4px;
        animation: shimmer 1.8s ease-in-out infinite;
    }

    @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
</style>
