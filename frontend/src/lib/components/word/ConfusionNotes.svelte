<script lang="ts">
    import type { ConfusionNote } from "$lib/types/vocab";

    interface Props {
        notes: ConfusionNote[];
        currentLemma: string;
    }

    let { notes, currentLemma }: Props = $props();
</script>

<div class="confusion-notes space-y-3">
    {#each notes as note}
        <div
            class="note-item bg-surface-primary rounded-lg p-4 border border-border shadow-card"
        >
            <div class="flex items-center gap-2 mb-2">
                <span class="font-medium text-content-primary"
                    >{currentLemma}</span
                >
                <span class="text-content-tertiary">vs.</span>
                <span class="font-medium text-srs-hard">{note.confused_with}</span>
            </div>
            <p class="text-sm text-content-secondary leading-relaxed mb-2">
                {note.distinction}
            </p>
            {#if note.memory_tip}
                <div
                    class="memory-tip flex items-start gap-2 pt-2 border-t border-border/50"
                >
                    <svg
                        class="w-4 h-4 text-accent flex-shrink-0 mt-0.5"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke-width="1.5"
                        stroke="currentColor"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
                        />
                    </svg>
                    <p class="text-xs text-content-tertiary italic">
                        {note.memory_tip}
                    </p>
                </div>
            {/if}
        </div>
    {/each}
</div>
