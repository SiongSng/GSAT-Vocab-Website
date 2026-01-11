<script lang="ts">
    import {
        getWordLookupStore,
        closeLookup,
    } from "$lib/stores/word-lookup.svelte";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";
    import BottomSheet from "$lib/components/ui/BottomSheet.svelte";
    import HighlightedText from "$lib/components/ui/HighlightedText.svelte";
    import WordDetailModal from "$lib/components/srs/WordDetailModal.svelte";
    import type { VocabEntryUnion, WordEntry, PhraseEntry, VocabSense } from "$lib/types/vocab";
    import { isWordEntry, isPhraseEntry } from "$lib/types/vocab";

    const lookup = getWordLookupStore();

    const item = $derived(lookup.mobileItem);

    let modalEntry = $state<WordEntry | PhraseEntry | null>(null);
    let isModalOpen = $state(false);

    function getSenses(entry: VocabEntryUnion | null): VocabSense[] {
        if (!entry) return [];
        if (isWordEntry(entry) || isPhraseEntry(entry)) {
            return entry.senses ?? [];
        }
        return [];
    }

    const senses = $derived(getSenses(item?.entry ?? null));
    const isSheetOpen = $derived(
        lookup.isMobileOpen && lookup.position === "bottom-sheet",
    );

    function getExample(sense: VocabSense): string | null {
        return sense.generated_example || null;
    }

    function handleViewFull() {
        if (item?.entry && (isWordEntry(item.entry) || isPhraseEntry(item.entry))) {
            modalEntry = item.entry;
            closeLookup();
            isModalOpen = true;
        }
    }

    function handleCloseModal() {
        isModalOpen = false;
        modalEntry = null;
    }
</script>

<BottomSheet isOpen={isSheetOpen} onClose={closeLookup}>
    {#if item?.isLoading}
        <div class="sheet-content">
            <div class="skeleton" style="width: 100px; height: 24px;"></div>
            <div class="skeleton" style="width: 100%; height: 18px; margin-top: 12px;"></div>
        </div>
    {:else if item?.entry}
        <div class="sheet-content">
            <div class="header">
                <span class="lemma">{item.entry.lemma}</span>
                <AudioButton text={item.entry.lemma} size="md" />
            </div>

            {#if senses.length > 0}
                {@const displaySenses = senses.slice(0, 3)}
                {@const remaining = senses.length - 3}
                <div class="senses">
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
                        <p class="more-hint">+{remaining} 更多</p>
                    {/if}
                </div>
            {/if}

            <button type="button" class="full-btn" onclick={handleViewFull}>
                查看完整資訊
            </button>
        </div>
    {:else if item}
        <div class="sheet-content">
            <p class="not-found">找不到此單字</p>
        </div>
    {/if}
</BottomSheet>

{#if modalEntry}
    <WordDetailModal
        entry={modalEntry}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
    />
{/if}

<style>
    .sheet-content {
        padding-top: 4px;
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }

    .lemma {
        font-size: 22px;
        font-weight: 600;
        color: rgb(55, 53, 47);
    }

    .senses {
        display: flex;
        flex-direction: column;
        gap: 14px;
    }

    .sense {
        line-height: 1.5;
    }

    .def {
        margin: 0;
        font-size: 16px;
        color: rgb(55, 53, 47);
    }

    .pos {
        color: rgba(55, 53, 47, 0.5);
        margin-right: 6px;
    }

    .example {
        margin: 6px 0 0;
        font-size: 15px;
        color: rgba(55, 53, 47, 0.65);
        line-height: 1.6;
    }

    .not-found {
        font-size: 15px;
        color: rgba(55, 53, 47, 0.5);
        margin: 0;
    }

    .more-hint {
        font-size: 14px;
        color: rgba(55, 53, 47, 0.45);
        margin: 0;
    }

    .full-btn {
        display: block;
        width: 100%;
        margin-top: 20px;
        padding: 12px;
        font-size: 15px;
        font-weight: 500;
        color: rgb(55, 53, 47);
        background: rgba(55, 53, 47, 0.08);
        border-radius: 6px;
        transition: background 0.15s;
    }

    .full-btn:hover {
        background: rgba(55, 53, 47, 0.12);
    }

    .full-btn:active {
        background: rgba(55, 53, 47, 0.16);
    }

    .skeleton {
        background: rgba(55, 53, 47, 0.08);
        border-radius: 4px;
        animation: pulse 1.5s ease-in-out infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
</style>
