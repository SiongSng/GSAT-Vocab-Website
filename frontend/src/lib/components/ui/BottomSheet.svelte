<script lang="ts">
    import type { Snippet } from "svelte";

    interface Props {
        isOpen: boolean;
        onClose: () => void;
        children: Snippet;
    }

    let { isOpen, onClose, children }: Props = $props();

    let sheetElement: HTMLDivElement | null = $state(null);
    let startY = 0;
    let currentY = 0;
    let isDragging = false;

    function handleTouchStart(e: TouchEvent) {
        startY = e.touches[0].clientY;
        isDragging = true;
    }

    function handleTouchMove(e: TouchEvent) {
        if (!isDragging) return;
        currentY = e.touches[0].clientY - startY;
        if (currentY < 0) currentY = 0;
        if (sheetElement) {
            sheetElement.style.transform = `translateY(${currentY}px)`;
        }
    }

    function handleTouchEnd() {
        isDragging = false;
        if (currentY > 100) {
            onClose();
        }
        if (sheetElement) {
            sheetElement.style.transform = "";
        }
        currentY = 0;
    }

    function handleBackdropClick() {
        onClose();
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Escape") {
            onClose();
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
    <div class="bottom-sheet-container">
        <button
            type="button"
            class="backdrop"
            onclick={handleBackdropClick}
            aria-label="Close"
        ></button>
        <div
            class="sheet"
            bind:this={sheetElement}
            ontouchstart={handleTouchStart}
            ontouchmove={handleTouchMove}
            ontouchend={handleTouchEnd}
            role="dialog"
            aria-modal="true"
        >
            <div class="drag-handle-container">
                <div class="drag-handle"></div>
            </div>
            <div class="sheet-content">
                {@render children()}
            </div>
        </div>
    </div>
{/if}

<style>
    .bottom-sheet-container {
        position: fixed;
        inset: 0;
        z-index: 100;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
    }

    .backdrop {
        position: absolute;
        inset: 0;
        background-color: rgba(0, 0, 0, 0.4);
        animation: fadeIn 0.2s ease-out;
        border: none;
        cursor: pointer;
    }

    .sheet {
        position: relative;
        background-color: var(--color-surface-primary);
        border-top-left-radius: 16px;
        border-top-right-radius: 16px;
        max-height: 80vh;
        overflow: hidden;
        animation: slideUp 0.25s ease-out;
        box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
    }

    .drag-handle-container {
        display: flex;
        justify-content: center;
        padding: 12px 0 8px;
        cursor: grab;
    }

    .drag-handle {
        width: 36px;
        height: 4px;
        background-color: var(--color-border-hover);
        border-radius: 2px;
    }

    .sheet-content {
        padding: 0 20px 24px;
        overflow-y: auto;
        max-height: calc(80vh - 40px);
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
            transform: translateY(100%);
        }
        to {
            transform: translateY(0);
        }
    }
</style>
