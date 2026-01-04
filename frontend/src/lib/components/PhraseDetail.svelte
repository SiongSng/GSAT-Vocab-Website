<script lang="ts">
    import type { PhraseEntry } from "$lib/types/vocab";
    import EntryDetailContent from "$lib/components/word/EntryDetailContent.svelte";

    interface Props {
        entry: PhraseEntry;
    }

    let { entry }: Props = $props();
</script>

<div class="phrase-detail p-6 lg:p-8">
    <EntryDetailContent {entry} />
</div>
