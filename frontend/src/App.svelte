<script lang="ts">
    import { onMount } from "svelte";
    import Header from "$lib/components/Header.svelte";
    import BrowseView from "$lib/components/BrowseView.svelte";
    import SRSFlashcardView from "$lib/components/srs/SRSFlashcardView.svelte";
    import QuizView from "$lib/components/QuizView.svelte";
    import LoadingOverlay from "$lib/components/LoadingOverlay.svelte";
    import QuickLookupSidebar from "$lib/components/lookup/QuickLookupSidebar.svelte";
    import QuickLookupSheet from "$lib/components/lookup/QuickLookupSheet.svelte";
    import { getAppStore, setMobile } from "$lib/stores/app.svelte";
    import {
        loadVocabData,
        syncWordFromRoute,
        getVocabStore,
    } from "$lib/stores/vocab.svelte";
    import {
        initRouter,
        destroyRouter,
        getRouterStore,
    } from "$lib/stores/router.svelte";

    const app = getAppStore();
    const router = getRouterStore();
    const vocab = getVocabStore();

    $effect(() => {
        router.route;
        syncWordFromRoute();
    });

    onMount(() => {
        initRouter();

        const mediaQuery = window.matchMedia("(max-width: 1023px)");
        setMobile(mediaQuery.matches);

        const handleMediaChange = (e: MediaQueryListEvent) => {
            setMobile(e.matches);
        };

        mediaQuery.addEventListener("change", handleMediaChange);
        loadVocabData();

        return () => {
            destroyRouter();
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

    <main class="flex-1 overflow-hidden">
        {#if app.mode === "browse"}
            <BrowseView />
        {:else if app.mode === "flashcard"}
            <SRSFlashcardView />
        {:else if app.mode === "quiz"}
            <QuizView />
        {/if}
    </main>
</div>

<QuickLookupSidebar />
<QuickLookupSheet />

<style>
    .app {
        min-height: 100vh;
        min-height: 100dvh;
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
