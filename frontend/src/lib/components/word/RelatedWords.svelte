<script lang="ts">
    interface Props {
        synonyms?: string[] | null;
        antonyms?: string[] | null;
        derivedForms?: string[] | null;
        onWordClick?: (lemma: string) => void;
    }

    let { synonyms, antonyms, derivedForms, onWordClick }: Props = $props();

    const hasSynonyms = $derived(synonyms && synonyms.length > 0);
    const hasAntonyms = $derived(antonyms && antonyms.length > 0);
    const hasDerivedForms = $derived(derivedForms && derivedForms.length > 0);

    function handleClick(word: string) {
        onWordClick?.(word);
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
                    <button
                        type="button"
                        class="px-2.5 py-1 text-sm bg-surface-page border border-border rounded-md text-content-secondary hover:bg-surface-hover hover:text-content-primary hover:border-border-hover transition-colors cursor-pointer"
                        onclick={() => handleClick(word)}
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
                    <button
                        type="button"
                        class="px-2.5 py-1 text-sm bg-surface-page border border-border rounded-md text-content-secondary hover:bg-surface-hover hover:text-content-primary hover:border-border-hover transition-colors cursor-pointer"
                        onclick={() => handleClick(word)}
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
                    <button
                        type="button"
                        class="px-2.5 py-1 text-sm bg-surface-page border border-border rounded-md text-content-secondary hover:bg-surface-hover hover:text-content-primary hover:border-border-hover transition-colors cursor-pointer"
                        onclick={() => handleClick(word)}
                    >
                        {word}
                    </button>
                {/each}
            </div>
        </div>
    {/if}
</div>
