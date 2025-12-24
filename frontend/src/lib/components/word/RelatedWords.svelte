<script lang="ts">
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { openLookup } from "$lib/stores/word-lookup.svelte";

    interface Props {
        synonyms?: string[] | null;
        antonyms?: string[] | null;
        derivedForms?: string[] | null;
    }

    let { synonyms, antonyms, derivedForms }: Props = $props();

    const vocab = getVocabStore();

    const hasSynonyms = $derived(synonyms && synonyms.length > 0);
    const hasAntonyms = $derived(antonyms && antonyms.length > 0);
    const hasDerivedForms = $derived(derivedForms && derivedForms.length > 0);

    function isInVocab(word: string): boolean {
        return vocab.lemmaSet.has(word.toLowerCase());
    }

    function handleClick(word: string) {
        if (isInVocab(word)) {
            openLookup(word);
        }
    }
</script>

<div class="related-words space-y-4">
    {#if hasSynonyms}
        <div class="synonym-group">
            <h4 class="text-xs font-medium text-content-tertiary mb-2">
                同義詞
            </h4>
            <div class="flex flex-wrap gap-2">
                {#each synonyms as word}
                    {@const clickable = isInVocab(word)}
                    <button
                        type="button"
                        class="word-chip"
                        class:clickable
                        onclick={() => handleClick(word)}
                        disabled={!clickable}
                    >
                        {word}
                    </button>
                {/each}
            </div>
        </div>
    {/if}

    {#if hasAntonyms}
        <div class="antonym-group">
            <h4 class="text-xs font-medium text-content-tertiary mb-2">
                反義詞
            </h4>
            <div class="flex flex-wrap gap-2">
                {#each antonyms as word}
                    {@const clickable = isInVocab(word)}
                    <button
                        type="button"
                        class="word-chip"
                        class:clickable
                        onclick={() => handleClick(word)}
                        disabled={!clickable}
                    >
                        {word}
                    </button>
                {/each}
            </div>
        </div>
    {/if}

    {#if hasDerivedForms}
        <div class="derived-group">
            <h4 class="text-xs font-medium text-content-tertiary mb-2">
                衍生詞
            </h4>
            <div class="flex flex-wrap gap-2">
                {#each derivedForms as word}
                    {@const clickable = isInVocab(word)}
                    <button
                        type="button"
                        class="word-chip"
                        class:clickable
                        onclick={() => handleClick(word)}
                        disabled={!clickable}
                    >
                        {word}
                    </button>
                {/each}
            </div>
        </div>
    {/if}
</div>

<style>
    .word-chip {
        padding: 0.25rem 0.625rem;
        font-size: 0.875rem;
        background: var(--color-surface-page);
        border: 1px solid var(--color-border);
        border-radius: 0.375rem;
        color: var(--color-content-tertiary);
        transition: all 0.15s ease;
    }

    .word-chip.clickable {
        color: var(--color-content-secondary);
        cursor: pointer;
    }

    .word-chip.clickable:hover {
        background: var(--color-surface-hover);
        color: var(--color-content-primary);
        border-color: var(--color-border-hover);
    }
</style>
