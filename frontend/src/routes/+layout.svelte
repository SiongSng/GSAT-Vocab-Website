<script lang="ts">
    import { onMount } from "svelte";
    import { browser } from "$app/environment";
    import { page } from "$app/stores";
    import Header from "$lib/components/Header.svelte";
    import BottomNav from "$lib/components/BottomNav.svelte";
    import LoadingOverlay from "$lib/components/LoadingOverlay.svelte";
    import QuickLookupSidebar from "$lib/components/lookup/QuickLookupSidebar.svelte";
    import QuickLookupSheet from "$lib/components/lookup/QuickLookupSheet.svelte";
    import PWAInstallPrompt from "$lib/components/PWAInstallPrompt.svelte";
    import { getAppStore, setMobile, setMode } from "$lib/stores/app.svelte";
    import { loadVocabData, getVocabStore } from "$lib/stores/vocab.svelte";
    import "../app.css";

    let { children } = $props();

    const vocab = getVocabStore();

    function getRelativePath(pathname: string): string {
        const base = import.meta.env.BASE_URL || '';
        if (base && base !== '/' && pathname.startsWith(base)) {
            return pathname.slice(base.length) || '/';
        }
        return pathname;
    }

    $effect(() => {
        if (!browser) return;
        const relativePath = getRelativePath($page.url.pathname);

        if (relativePath.startsWith('/flashcard')) {
            setMode('flashcard');
        } else if (relativePath.startsWith('/quiz')) {
            setMode('quiz');
        } else if (relativePath.startsWith('/stats')) {
            setMode('stats');
        } else if (relativePath.startsWith('/blog')) {
            setMode('browse');
        } else if (relativePath.startsWith('/word')) {
            setMode('browse');
        } else {
            setMode('browse');
        }
    });

    const needsScrollableMain = $derived.by(() => {
        const relativePath = getRelativePath($page.url.pathname);
        return relativePath.startsWith('/blog') ||
               relativePath.startsWith('/word') ||
               relativePath.startsWith('/stats');
    });

    function needsVocabData(pathname: string): boolean {
        const relativePath = getRelativePath(pathname);
        return !relativePath.startsWith('/blog');
    }

    $effect(() => {
        if (!browser) return;
        if (needsVocabData($page.url.pathname) && !vocab.isLoaded && !vocab.isLoading) {
            loadVocabData();
        }
    });

    onMount(() => {
        const mediaQuery = window.matchMedia("(max-width: 1023px)");
        setMobile(mediaQuery.matches);

        const handleMediaChange = (e: MediaQueryListEvent) => {
            setMobile(e.matches);
        };

        mediaQuery.addEventListener("change", handleMediaChange);
        document.getElementById("initial-loader")?.remove();

        return () => {
            mediaQuery.removeEventListener("change", handleMediaChange);
        };
    });
</script>

{#if vocab.loadProgress}
    <LoadingOverlay progress={vocab.loadProgress} />
{/if}

<div
    class="app h-full flex flex-col bg-surface-page text-content-primary antialiased"
>
    <Header />

    <main
        class="flex-1 min-h-0"
        class:overflow-hidden={!needsScrollableMain}
        class:overflow-y-auto={needsScrollableMain}
    >
        {@render children()}
    </main>
</div>

<QuickLookupSidebar />
<QuickLookupSheet />
<PWAInstallPrompt />
<BottomNav />

<style>
    .app {
        min-height: 100vh;
        min-height: 100dvh;
    }

    :global(:root) {
        --bottom-nav-height: 0px;
    }

    @media (max-width: 1023px) {
        :global(:root) {
            --bottom-nav-height: calc(4.5rem + env(safe-area-inset-bottom, 0px));
        }
    }

    :global(html, body) {
        height: 100%;
        margin: 0;
        padding: 0;
    }

    :global(*) {
        box-sizing: border-box;
    }

    :global(::-webkit-scrollbar) {
        width: 6px;
        height: 6px;
    }

    :global(::-webkit-scrollbar-track) {
        background: transparent;
    }

    :global(::-webkit-scrollbar-thumb) {
        background-color: var(--color-scrollbar);
        border-radius: 3px;
    }

    :global(::-webkit-scrollbar-thumb:hover) {
        background-color: var(--color-scrollbar-hover);
    }
</style>
