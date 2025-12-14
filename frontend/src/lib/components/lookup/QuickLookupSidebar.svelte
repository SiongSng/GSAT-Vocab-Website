<script lang="ts">
    import {
        getWordLookupStore,
        closeLookupItem,
        closeAllLookups,
    } from "$lib/stores/word-lookup.svelte";
    import { selectWordAndNavigate } from "$lib/stores/vocab.svelte";
    import { speakText } from "$lib/tts";
    import type { VocabEntry } from "$lib/types/vocab";

    const lookup = getWordLookupStore();

    let playingLemma = $state<string | null>(null);
    let audioPlayer: HTMLAudioElement | null = null;

    function getPrimarySense(entry: VocabEntry | null) {
        return entry?.senses?.[0] ?? null;
    }

    async function playAudio(lemma: string) {
        if (playingLemma === lemma) return;
        playingLemma = lemma;
        try {
            const url = await speakText(lemma);
            if (!audioPlayer) audioPlayer = new Audio();
            audioPlayer.src = url;
            audioPlayer.onended = () => (playingLemma = null);
            audioPlayer.onerror = () => (playingLemma = null);
            await audioPlayer.play();
        } catch {
            playingLemma = null;
        }
    }

    function handleWordClick(lemma: string) {
        selectWordAndNavigate(lemma);
    }

    function formatLevel(level: number | null): string {
        if (level === null) return "";
        return `L${level}`;
    }

    function handleClose(lemma: string) {
        closeLookupItem(lemma);
    }
</script>

{#if lookup.hasItems && lookup.position === "sidebar"}
    <aside class="lookup-sidebar">
        <div class="sidebar-header">
            <h3 class="text-xs font-semibold text-content-tertiary uppercase tracking-wider">
                Quick Lookup
            </h3>
            <button
                type="button"
                class="close-btn"
                onclick={closeAllLookups}
                aria-label="Close all"
            >
                <svg
                    class="w-4 h-4"
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

        <div class="sidebar-content">
            {#each lookup.items as item (item.lemma)}
                {@const primarySense = getPrimarySense(item.entry)}
                <div class="lookup-card">
                    <div class="card-header">
                        {#if item.isLoading}
                            <div class="skeleton-text h-5 w-20"></div>
                        {:else if item.entry}
                            <div class="flex items-center gap-2">
                                <button
                                    type="button"
                                    class="text-lg font-semibold text-accent hover:underline"
                                    onclick={() => handleWordClick(item.lemma)}
                                >
                                    {item.entry.lemma}
                                </button>
                                <button
                                    type="button"
                                    class="p-1 rounded-md hover:bg-surface-hover transition-colors"
                                    class:animate-pulse={playingLemma === item.lemma}
                                    onclick={() => playAudio(item.lemma)}
                                    title="播放發音"
                                >
                                    <svg
                                        class="w-4 h-4 text-content-tertiary"
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke-width="1.5"
                                        stroke="currentColor"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
                                        />
                                    </svg>
                                </button>
                            </div>
                        {:else}
                            <span class="text-sm text-content-tertiary">{item.lemma}</span>
                        {/if}
                        <button
                            type="button"
                            class="close-card-btn"
                            onclick={() => handleClose(item.lemma)}
                            aria-label="Close"
                        >
                            <svg
                                class="w-3.5 h-3.5"
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

                    {#if item.isLoading}
                        <div class="card-body">
                            <div class="skeleton-text h-4 w-16 mb-3"></div>
                            <div class="skeleton-text h-4 w-full mb-2"></div>
                            <div class="skeleton-text h-4 w-3/4"></div>
                        </div>
                    {:else if item.entry}
                        <div class="card-body">
                            <div class="flex items-center gap-1 text-xs text-content-tertiary mb-2">
                                {#if primarySense}
                                    <span>{primarySense.pos}</span>
                                {/if}
                                {#if item.entry.level !== null}
                                    <span>·</span>
                                    <span>{formatLevel(item.entry.level)}</span>
                                {/if}
                                {#if item.entry.in_official_list}
                                    <span>·</span>
                                    <span class="text-accent">官方</span>
                                {/if}
                            </div>

                            {#if primarySense}
                                <p class="text-sm text-content-primary leading-relaxed mb-1">
                                    {primarySense.zh_def}
                                </p>
                                {#if primarySense.en_def}
                                    <p class="text-xs text-content-secondary leading-relaxed">
                                        {primarySense.en_def}
                                    </p>
                                {/if}
                            {/if}

                            {#if item.entry.senses && item.entry.senses.length > 1}
                                <p class="text-xs text-content-tertiary mt-2">
                                    +{item.entry.senses.length - 1} 其他涵義
                                </p>
                            {/if}
                        </div>
                    {:else}
                        <div class="card-body">
                            <p class="text-sm text-content-tertiary">找不到此單字</p>
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    </aside>
{/if}

<style>
    .lookup-sidebar {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        width: 300px;
        background-color: var(--color-surface-primary);
        border-left: 1px solid var(--color-border);
        box-shadow: -4px 0 20px rgba(0, 0, 0, 0.08);
        z-index: 90;
        display: flex;
        flex-direction: column;
        animation: slideIn 0.2s ease-out;
    }

    @keyframes slideIn {
        from {
            transform: translateX(100%);
        }
        to {
            transform: translateX(0);
        }
    }

    .sidebar-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 20px;
        border-bottom: 1px solid var(--color-border);
        flex-shrink: 0;
    }

    .close-btn {
        padding: 4px;
        border-radius: 4px;
        color: var(--color-content-tertiary);
        transition: all 0.15s ease;
    }

    .close-btn:hover {
        background-color: var(--color-surface-hover);
        color: var(--color-content-secondary);
    }

    .sidebar-content {
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .lookup-card {
        background-color: var(--color-surface-page);
        border: 1px solid var(--color-border);
        border-radius: 10px;
        overflow: hidden;
        animation: cardIn 0.15s ease-out;
        flex-shrink: 0;
    }

    @keyframes cardIn {
        from {
            opacity: 0;
            transform: translateY(-8px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 14px;
        background-color: var(--color-surface-secondary);
        border-bottom: 1px solid var(--color-border);
    }

    .close-card-btn {
        padding: 4px;
        border-radius: 4px;
        color: var(--color-content-tertiary);
        transition: all 0.15s ease;
    }

    .close-card-btn:hover {
        background-color: var(--color-surface-hover);
        color: var(--color-content-secondary);
    }

    .card-body {
        padding: 14px;
    }

    .skeleton-text {
        background: linear-gradient(
            90deg,
            var(--color-surface-secondary) 25%,
            var(--color-surface-page) 50%,
            var(--color-surface-secondary) 75%
        );
        background-size: 200% 100%;
        animation: shimmer 2s infinite;
        border-radius: 4px;
    }

    @keyframes shimmer {
        0% {
            background-position: 200% 0;
        }
        100% {
            background-position: -200% 0;
        }
    }
</style>
