<script lang="ts">
    import { onMount } from "svelte";
    import Header from "$lib/components/Header.svelte";
    import BrowseView from "$lib/components/BrowseView.svelte";
    import SRSFlashcardView from "$lib/components/srs/SRSFlashcardView.svelte";
    import QuizView from "$lib/components/QuizView.svelte";
    import { getAppStore, setMobile } from "$lib/stores/app.svelte";
    import { loadVocabData } from "$lib/stores/vocab.svelte";

    const app = getAppStore();

    onMount(() => {
        const mediaQuery = window.matchMedia("(max-width: 1023px)");
        setMobile(mediaQuery.matches);

        const handleMediaChange = (e: MediaQueryListEvent) => {
            setMobile(e.matches);
        };

        mediaQuery.addEventListener("change", handleMediaChange);
        loadVocabData();

        return () => {
            mediaQuery.removeEventListener("change", handleMediaChange);
        };
    });
</script>

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
        background-color: rgba(0, 0, 0, 0.15);
        border-radius: 3px;
    }

    :global(::-webkit-scrollbar-thumb:hover) {
        background-color: rgba(0, 0, 0, 0.25);
    }
</style>
