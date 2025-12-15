<script lang="ts">
    interface Props {
        text: string;
    }

    let { text }: Props = $props();

    let isOpen = $state(false);
    let btnRef: HTMLButtonElement | null = $state(null);
    let tooltipStyle = $state("");

    function open(e: Event) {
        e.stopPropagation();
        if (isOpen) {
            isOpen = false;
            return;
        }
        document.dispatchEvent(new CustomEvent("help-tooltip-close"));
        isOpen = true;
    }

    function close() {
        isOpen = false;
    }

    function handleClickOutside(e: MouseEvent) {
        if (btnRef && !btnRef.contains(e.target as Node)) {
            isOpen = false;
        }
    }

    function updatePosition() {
        if (!btnRef) return;

        const rect = btnRef.getBoundingClientRect();
        const contentWidth = 200;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const padding = 12;
        const tooltipHeight = 60;

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

        tooltipStyle = `top: ${top}px; left: ${left}px;`;
    }

    $effect(() => {
        document.addEventListener("help-tooltip-close", close);
        return () => document.removeEventListener("help-tooltip-close", close);
    });

    $effect(() => {
        if (isOpen) {
            updatePosition();
            document.addEventListener("click", handleClickOutside);
            window.addEventListener("scroll", updatePosition, true);
            window.addEventListener("resize", updatePosition);
            return () => {
                document.removeEventListener("click", handleClickOutside);
                window.removeEventListener("scroll", updatePosition, true);
                window.removeEventListener("resize", updatePosition);
            };
        }
    });
</script>

<button
    type="button"
    class="help-btn"
    onclick={open}
    aria-label="說明"
    bind:this={btnRef}
>
    <svg
        class="w-3.5 h-3.5"
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
</button>

{#if isOpen}
    <span class="tooltip-content" style={tooltipStyle}>
        {text}
    </span>
{/if}

<style>
    .help-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        color: var(--color-content-tertiary);
        transition: all 0.15s ease;
        flex-shrink: 0;
        vertical-align: middle;
    }

    .help-btn:hover {
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
    }
</style>
