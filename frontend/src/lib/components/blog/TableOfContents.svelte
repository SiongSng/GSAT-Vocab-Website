<script lang="ts">
    import { onMount } from "svelte";

    interface TocItem {
        id: string;
        text: string;
        level: number;
    }

    let tocItems = $state<TocItem[]>([]);
    let activeId = $state<string>("");
    let scrollContainer: Element | null = null;

    onMount(() => {
        const content = document.querySelector(".content");
        if (!content) return;

        // Find the scroll container (main with overflow-y: auto)
        scrollContainer = document.querySelector("main");

        const headings = content.querySelectorAll("h2[id], h3[id]");
        const items: TocItem[] = [];

        headings.forEach((heading) => {
            const el = heading as HTMLElement;
            const id = el.id;
            const text = el.textContent?.trim() || "";
            const level = parseInt(el.tagName[1]);
            if (id && text) {
                items.push({ id, text, level });
            }
        });

        tocItems = items;
        if (items.length > 0) {
            activeId = items[0].id;
        }

        const observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        activeId = entry.target.id;
                        break;
                    }
                }
            },
            {
                root: scrollContainer,
                rootMargin: "-80px 0px -70% 0px",
            },
        );

        headings.forEach((h) => observer.observe(h));

        return () => observer.disconnect();
    });

    function handleClick(id: string) {
        const el = document.getElementById(id);
        if (!el || !scrollContainer) return;

        const headerOffset = 80;
        const containerRect = scrollContainer.getBoundingClientRect();
        const elementRect = el.getBoundingClientRect();
        const relativeTop = elementRect.top - containerRect.top;
        const scrollTop =
            scrollContainer.scrollTop + relativeTop - headerOffset;

        scrollContainer.scrollTo({
            top: scrollTop,
            behavior: "smooth",
        });

        activeId = id;
    }
</script>

{#if tocItems.length > 0}
    <nav class="toc">
        <div class="toc-title">目錄</div>
        <ul class="toc-list">
            {#each tocItems as item}
                <li>
                    <button
                        type="button"
                        class="toc-item"
                        class:active={activeId === item.id}
                        class:indent={item.level === 3}
                        onclick={() => handleClick(item.id)}
                    >
                        {item.text}
                    </button>
                </li>
            {/each}
        </ul>
    </nav>
{/if}

<style>
    .toc {
        position: sticky;
        top: 5rem;
        font-size: 0.8125rem;
    }

    .toc-title {
        font-size: 0.6875rem;
        font-weight: 600;
        color: var(--color-content-tertiary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.75rem;
    }

    .toc-list {
        list-style: none;
        margin: 0;
        padding: 0;
        border-left: 1px solid var(--color-border);
    }

    .toc-list li {
        margin: 0;
    }

    .toc-item {
        display: block;
        width: 100%;
        text-align: left;
        padding: 0.375rem 0.75rem;
        margin-left: -1px;
        border-left: 2px solid transparent;
        background: none;
        border-top: none;
        border-right: none;
        border-bottom: none;
        color: var(--color-content-tertiary);
        cursor: pointer;
        line-height: 1.4;
        transition: all 0.15s ease;
        font-size: inherit;
    }

    .toc-item:hover {
        color: var(--color-content-secondary);
    }

    .toc-item.active {
        color: var(--color-content-primary);
        border-left-color: var(--color-content-primary);
    }

    .toc-item.indent {
        padding-left: 1.25rem;
        font-size: 0.75rem;
    }
</style>
