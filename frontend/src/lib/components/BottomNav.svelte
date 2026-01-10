<script lang="ts">
    import { page } from "$app/stores";
    import { getAppStore } from "$lib/stores/app.svelte";
    import { base } from "$app/paths";

    const app = getAppStore();

    const navItems = [
        { href: "/", icon: "browse", label: "瀏覽單字" },
        { href: "/flashcard", icon: "flashcard", label: "字卡學習" },
        { href: "/quiz", icon: "quiz", label: "測驗模式" },
    ];

    function isActive(href: string, currentPath: string): boolean {
        if (href === "/") {
            return currentPath === "/" || currentPath === "" || currentPath.startsWith("/word");
        }
        return currentPath.startsWith(href);
    }

    const isBlogPage = $derived($page.url.pathname.replace(base, '').startsWith('/blog'));
</script>

{#if app.isMobile && !isBlogPage}
    <nav class="bottom-nav">
        <div class="nav-pill">
            {#each navItems as item}
                <a
                    href="{base}{item.href}"
                    class="nav-item"
                    class:active={isActive(item.href, $page.url.pathname.replace(base, ''))}
                    aria-label={item.label}
                >
                    {#if item.icon === "browse"}
                        <svg
                            class="nav-icon"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="1.5"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        >
                            <path
                                d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
                            />
                        </svg>
                    {:else if item.icon === "flashcard"}
                        <svg
                            class="nav-icon"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="1.5"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        >
                            <path
                                d="M6 6.878V6a2.25 2.25 0 0 1 2.25-2.25h7.5A2.25 2.25 0 0 1 18 6v.878m-12 0c.235-.083.487-.128.75-.128h10.5c.263 0 .515.045.75.128m-12 0A2.25 2.25 0 0 0 4.5 9v.878m13.5-3A2.25 2.25 0 0 1 19.5 9v.878m0 0a2.246 2.246 0 0 0-.75-.128H5.25c-.263 0-.515.045-.75.128m15 0A2.25 2.25 0 0 1 21 12v6a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18v-6c0-1.007.661-1.859 1.572-2.145"
                            />
                        </svg>
                    {:else if item.icon === "quiz"}
                        <svg
                            class="nav-icon"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="1.5"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        >
                            <path
                                d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"
                            />
                        </svg>
                    {/if}
                </a>
            {/each}
        </div>
    </nav>
{/if}

<style>
    .bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 50;
        display: flex;
        justify-content: center;
        padding: 0.75rem 1rem calc(env(safe-area-inset-bottom, 0px) + 0.75rem);
        pointer-events: none;
    }

    .nav-pill {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 9999px;
        padding: 0.375rem;
        box-shadow:
            0 4px 20px rgba(0, 0, 0, 0.1),
            0 0 0 1px rgba(0, 0, 0, 0.02);
        pointer-events: auto;
    }

    .nav-item {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 3rem;
        height: 3rem;
        border-radius: 9999px;
        color: var(--color-content-tertiary);
        transition: all 0.2s ease;
        cursor: pointer;
        background: transparent;
        border: none;
    }

    .nav-item:active {
        transform: scale(0.92);
    }

    .nav-item.active {
        color: var(--color-accent);
        background: var(--color-accent-soft);
    }

    .nav-icon {
        width: 1.375rem;
        height: 1.375rem;
    }
</style>
