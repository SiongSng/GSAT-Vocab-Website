<script lang="ts">
    import { onMount } from "svelte";

    interface Props {
        text: string;
    }

    let { text }: Props = $props();

    let containerRef: HTMLSpanElement | null = $state(null);
    let tooltipEl: HTMLSpanElement | null = $state(null);
    let isVisible = $state(false);

    function updatePosition() {
        if (!containerRef || !tooltipEl) return;

        const rect = containerRef.getBoundingClientRect();
        const contentWidth = 200;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const padding = 12;
        const tooltipHeight = tooltipEl.offsetHeight || 60;

        let top = rect.bottom + 8;
        let left = rect.left + rect.width / 2 - contentWidth / 2;

        if (top + tooltipHeight > viewportHeight - padding) {
            top = rect.top - tooltipHeight - 8;
        }

        if (left < padding) {
            left = padding;
        } else if (left + contentWidth > viewportWidth - padding) {
            left = viewportWidth - padding - contentWidth;
        }

        tooltipEl.style.top = `${top}px`;
        tooltipEl.style.left = `${left}px`;
    }

    onMount(() => {
        if (tooltipEl) {
            document.body.appendChild(tooltipEl);
        }
        return () => {
            if (tooltipEl && tooltipEl.parentNode === document.body) {
                document.body.removeChild(tooltipEl);
            }
        };
    });

    function handleMouseEnter() {
        isVisible = true;
        updatePosition();
    }

    function handleMouseLeave() {
        isVisible = false;
    }

    $effect(() => {
        if (isVisible) {
            window.addEventListener("scroll", updatePosition, true);
            window.addEventListener("resize", updatePosition);
            return () => {
                window.removeEventListener("scroll", updatePosition, true);
                window.removeEventListener("resize", updatePosition);
            };
        }
    });
</script>

<span
    class="help-container"
    bind:this={containerRef}
    onmouseenter={handleMouseEnter}
    onmouseleave={handleMouseLeave}
    onfocus={handleMouseEnter}
    onblur={handleMouseLeave}
    role="button"
    tabindex="0"
>
    <svg
        class="help-icon"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke-width="2"
        stroke="currentColor"
    >
        <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z"
        />
    </svg>
</span>

<span class="tooltip-content" class:visible={isVisible} bind:this={tooltipEl}>
    {text}
</span>

<style>
    .help-container {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 14px;
        height: 14px;
        cursor: help;
        flex-shrink: 0;
    }

    .help-icon {
        width: 14px;
        height: 14px;
        color: var(--color-content-tertiary);
        transition: color 0.15s ease;
    }

    .help-container:hover .help-icon {
        color: var(--color-content-secondary);
    }

    .tooltip-content {
        position: fixed;
        z-index: 9999;
        width: 200px;
        padding: 8px 12px;
        background-color: var(--color-content-primary);
        border-radius: 6px;
        font-size: 0.75rem;
        line-height: 1.5;
        color: white;
        text-align: center;
        white-space: normal;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.15s ease;
    }

    .tooltip-content:global(.visible) {
        opacity: 1;
    }
</style>
