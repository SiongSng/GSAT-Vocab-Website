<script lang="ts">
    import type { VocabEntry } from "$lib/types/vocab";
    import { isWordEntry, isPhraseEntry } from "$lib/types/vocab";
    import EntryDetailContent from "$lib/components/word/EntryDetailContent.svelte";

    interface Props {
        entry: VocabEntry;
        isOpen: boolean;
        onClose: () => void;
    }

    let { entry, isOpen, onClose }: Props = $props();

    const isWordOrPhrase = $derived(isWordEntry(entry) || isPhraseEntry(entry));

    function handleBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) {
            onClose();
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (!isOpen) return;
        if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
            onClose();
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
        class="modal-backdrop"
        onclick={handleBackdropClick}
        role="presentation"
    >
        <div class="modal-container" role="dialog" aria-modal="true">
            <div class="modal-header">
                <button
                    type="button"
                    class="close-btn"
                    onclick={onClose}
                    aria-label="關閉"
                >
                    <svg
                        class="w-5 h-5"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke-width="1.5"
                        stroke="currentColor"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M6 18 18 6M6 6l12 12"
                        />
                    </svg>
                </button>
            </div>

            <div class="modal-content">
                {#if isWordOrPhrase}
                    <EntryDetailContent {entry} compact={true} />
                {:else}
                    <div class="text-center py-8 text-content-tertiary">
                        無法顯示此類型的詞條
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}

<style>
    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.25);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
        z-index: 100;
        animation: fadeIn 0.15s ease-out;
    }

    .modal-container {
        position: relative;
        width: 100%;
        max-width: 600px;
        max-height: calc(100vh - 4rem);
        background: var(--color-surface-page);
        border-radius: 12px;
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-float);
        overflow: hidden;
        animation: slideUp 0.2s ease-out;
    }

    .modal-header {
        display: flex;
        justify-content: flex-end;
        padding: 0.75rem 0.75rem 0;
    }

    .modal-content {
        padding: 0 1.5rem 1.5rem;
        overflow-y: auto;
        max-height: calc(100vh - 8rem);
        scrollbar-width: thin;
        scrollbar-color: var(--color-border-hover) transparent;
    }

    .modal-content::-webkit-scrollbar {
        width: 6px;
    }

    .modal-content::-webkit-scrollbar-track {
        background: transparent;
    }

    .modal-content::-webkit-scrollbar-thumb {
        background-color: var(--color-border-hover);
        border-radius: 3px;
    }

    .close-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 2rem;
        height: 2rem;
        border-radius: 6px;
        color: var(--color-content-tertiary);
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        transition: all 0.15s ease;
    }

    .close-btn:hover {
        color: var(--color-content-primary);
        background: var(--color-surface-hover);
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(16px) scale(0.98);
        }
        to {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
    }
</style>
