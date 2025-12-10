<script lang="ts">
    import { onMount } from "svelte";
    import type { Snippet } from "svelte";

    interface Props<T> {
        items: T[];
        itemHeight: number;
        overscan?: number;
        containerClass?: string;
        children: Snippet<[{ item: T; index: number }]>;
    }

    let {
        items,
        itemHeight,
        overscan = 5,
        containerClass = "",
        children,
    }: Props<unknown> = $props();

    let container: HTMLDivElement | null = $state(null);
    let scrollTop = $state(0);
    let containerHeight = $state(0);

    const totalHeight = $derived(items.length * itemHeight);

    const visibleRange = $derived.by(() => {
        const start = Math.max(
            0,
            Math.floor(scrollTop / itemHeight) - overscan,
        );
        const visibleCount = Math.ceil(containerHeight / itemHeight);
        const end = Math.min(items.length, start + visibleCount + overscan * 2);
        return { start, end };
    });

    const visibleItems = $derived(
        items.slice(visibleRange.start, visibleRange.end).map((item, i) => ({
            item,
            index: visibleRange.start + i,
            offset: (visibleRange.start + i) * itemHeight,
        })),
    );

    function handleScroll(e: Event) {
        const target = e.target as HTMLDivElement;
        scrollTop = target.scrollTop;
    }

    onMount(() => {
        if (container) {
            containerHeight = container.clientHeight;

            const resizeObserver = new ResizeObserver((entries) => {
                for (const entry of entries) {
                    containerHeight = entry.contentRect.height;
                }
            });

            resizeObserver.observe(container);

            return () => resizeObserver.disconnect();
        }
    });
</script>

<div
    bind:this={container}
    class="virtual-list-container overflow-y-auto {containerClass}"
    onscroll={handleScroll}
>
    <div class="virtual-list-spacer relative" style="height: {totalHeight}px;">
        {#each visibleItems as { item, index, offset } (index)}
            <div
                class="virtual-list-item absolute left-0 right-0"
                style="top: {offset}px; height: {itemHeight}px;"
            >
                {@render children({ item, index })}
            </div>
        {/each}
    </div>
</div>

<style>
    .virtual-list-container {
        height: 100%;
        will-change: scroll-position;
    }

    .virtual-list-spacer {
        will-change: contents;
    }

    .virtual-list-item {
        contain: layout style;
    }
</style>
