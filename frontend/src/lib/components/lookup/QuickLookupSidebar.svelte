<script lang="ts">
    import {
        getWordLookupStore,
        closeLookupItem,
        closeAllLookups,
    } from "$lib/stores/word-lookup.svelte";
    import { selectWordAndNavigate } from "$lib/stores/vocab.svelte";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";
    import type { VocabEntryUnion } from "$lib/types/vocab";
    import { isWordEntry, isPhraseEntry } from "$lib/types/vocab";

    const lookup = getWordLookupStore();

    function getPrimarySense(entry: VocabEntryUnion | null) {
        if (!entry) return null;
        if (isWordEntry(entry) || isPhraseEntry(entry)) {
            return entry.senses?.[0] ?? null;
        }
        return null;
    }

    function getLevel(entry: VocabEntryUnion | null): number | null {
        if (!entry) return null;
        if (isWordEntry(entry)) return entry.level;
        return null;
    }

    function getIsOfficial(entry: VocabEntryUnion | null): boolean {
        if (!entry) return false;
        if (isWordEntry(entry)) return entry.in_official_list;
        return false;
    }

    function getSenseCount(entry: VocabEntryUnion | null): number {
        if (!entry) return 0;
        if (isWordEntry(entry) || isPhraseEntry(entry)) {
            return entry.senses?.length ?? 0;
        }
        return 0;
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
            <h3
                class="text-xs font-semibold text-content-tertiary uppercase tracking-wider"
            >
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
                                <AudioButton text={item.lemma} size="sm" />
                            </div>
                        {:else}
                            <span class="text-sm text-content-tertiary"
                                >{item.lemma}</span
                            >
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
                        {@const level = getLevel(item.entry)}
                        {@const isOfficial = getIsOfficial(item.entry)}
                        {@const senseCount = getSenseCount(item.entry)}
                        <div class="card-body">
                            <div
                                class="flex items-center gap-1 text-xs text-content-tertiary mb-2"
                            >
                                {#if primarySense}
                                    <span>{primarySense.pos}</span>
                                {/if}
                                {#if level !== null}
                                    <span>·</span>
                                    <span>{formatLevel(level)}</span>
                                {/if}
                                {#if isOfficial}
                                    <span>·</span>
                                    <span class="text-accent">官方</span>
                                {/if}
                            </div>

                            {#if primarySense}
                                <p
                                    class="text-sm text-content-primary leading-relaxed mb-1"
                                >
                                    {primarySense.zh_def}
                                </p>
                                {#if primarySense.en_def}
                                    <p
                                        class="text-xs text-content-secondary leading-relaxed"
                                    >
                                        {primarySense.en_def}
                                    </p>
                                {/if}
                            {/if}

                            {#if senseCount > 1}
                                <p class="text-xs text-content-tertiary mt-2">
                                    +{senseCount - 1} 其他涵義
                                </p>
                            {/if}
                        </div>
                    {:else}
                        <div class="card-body">
                            <p class="text-sm text-content-tertiary">
                                找不到此單字
                            </p>
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
