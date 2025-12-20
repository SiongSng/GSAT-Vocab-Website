<script lang="ts">
    import type { VocabEntry } from "$lib/types/vocab";
    import SenseTabs from "$lib/components/word/SenseTabs.svelte";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";
    import StatisticsSection from "$lib/components/word/StatisticsSection.svelte";
    import ConfusionNotes from "$lib/components/word/ConfusionNotes.svelte";
    import RelatedWords from "$lib/components/word/RelatedWords.svelte";
    import RootAnalysis from "$lib/components/word/RootAnalysis.svelte";

    interface Props {
        entry: VocabEntry;
        isOpen: boolean;
        onClose: () => void;
    }

    let { entry, isOpen, onClose }: Props = $props();

    let activeDeepDive = $state<string | null>(null);

    $effect(() => {
        if (isOpen && entry) {
            if (entry.frequency && entry.senses) {
                activeDeepDive = "stats";
            } else if (entry.root_info) {
                activeDeepDive = "root";
            } else if (
                entry.confusion_notes &&
                entry.confusion_notes.length > 0
            ) {
                activeDeepDive = "confusion";
            } else if (
                entry.synonyms ||
                entry.antonyms ||
                entry.derived_forms
            ) {
                activeDeepDive = "related";
            } else {
                activeDeepDive = null;
            }
        }
    });

    const hasConfusionNotes = $derived(
        entry?.confusion_notes != null && entry.confusion_notes.length > 0,
    );
    const hasRootInfo = $derived(entry?.root_info != null);
    const hasRelatedWords = $derived(
        (entry?.synonyms != null && entry.synonyms.length > 0) ||
            (entry?.antonyms != null && entry.antonyms.length > 0) ||
            (entry?.derived_forms != null && entry.derived_forms.length > 0),
    );

    const memoryTip = $derived(entry?.root_info?.memory_strategy ?? null);

    const importanceScore = $derived(() => {
        if (!entry?.frequency) return 0;
        return entry.frequency.ml_score ?? entry.frequency.weighted_score / 30;
    });

    const importancePercentage = $derived(Math.round(importanceScore() * 100));

    function formatLevel(level: number | null): string {
        if (level === null) return "";
        return `L${level}`;
    }

    function toggleDeepDive(section: string) {
        activeDeepDive = activeDeepDive === section ? null : section;
    }

    function handleBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) {
            onClose();
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Escape") {
            onClose();
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="modal-backdrop" onclick={handleBackdropClick}>
        <div class="modal-container" role="dialog" aria-modal="true">
            <div class="modal-header">
                <button
                    type="button"
                    class="close-btn"
                    onclick={onClose}
                    aria-label="關閉"
                >
                    <svg
                        class="w-5 h-5"
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

            <div class="modal-content">
                <header class="mb-5">
                    <div class="flex items-start justify-between">
                        <div>
                            <h2
                                class="text-2xl font-semibold tracking-tight text-content-primary mb-1"
                            >
                                {entry.lemma}
                            </h2>
                            <div
                                class="flex items-center gap-1.5 text-sm text-content-tertiary"
                            >
                                {#if entry.level !== null}
                                    <span>{formatLevel(entry.level)}</span>
                                {/if}
                                {#if entry.in_official_list}
                                    {#if entry.level !== null}
                                        <span class="text-border-hover">·</span>
                                    {/if}
                                    <span class="text-accent">官方</span>
                                {/if}
                                {#if entry.frequency}
                                    <span class="text-border-hover">·</span>
                                    <span>重要 {importancePercentage}%</span>
                                {/if}
                            </div>
                        </div>
                        <AudioButton text={entry.lemma} size="md" />
                    </div>

                    {#if memoryTip}
                        <div
                            class="mt-4 p-3 bg-surface-secondary rounded-lg border border-border"
                        >
                            <div class="flex items-start gap-2.5">
                                <svg
                                    class="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5"
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke-width="1.5"
                                    stroke="currentColor"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
                                    />
                                </svg>
                                <p
                                    class="text-sm text-content-secondary leading-relaxed"
                                >
                                    {memoryTip}
                                </p>
                            </div>
                        </div>
                    {/if}
                </header>

                {#if entry.senses && entry.senses.length > 0}
                    <div class="senses-section mb-5">
                        <SenseTabs senses={entry.senses} lemma={entry.lemma} />
                    </div>
                {/if}

                {#if hasRootInfo || hasConfusionNotes || hasRelatedWords || entry.frequency}
                    <div class="border-t border-border pt-4">
                        <h3
                            class="text-sm font-semibold text-section-header mb-3"
                        >
                            深入學習
                        </h3>

                        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
                            {#if entry.frequency && entry.senses}
                                <button
                                    type="button"
                                    class="deep-dive-btn"
                                    class:active={activeDeepDive === "stats"}
                                    onclick={() => toggleDeepDive("stats")}
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
                                            d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z"
                                        />
                                    </svg>
                                    <span>統計</span>
                                </button>
                            {/if}

                            {#if hasRootInfo}
                                <button
                                    type="button"
                                    class="deep-dive-btn"
                                    class:active={activeDeepDive === "root"}
                                    onclick={() => toggleDeepDive("root")}
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
                                            d="M14.25 6.087c0-.355.186-.676.401-.959.221-.29.349-.634.349-1.003 0-1.036-1.007-1.875-2.25-1.875s-2.25.84-2.25 1.875c0 .369.128.713.349 1.003.215.283.401.604.401.959v0a.64.64 0 0 1-.657.643 48.39 48.39 0 0 1-4.163-.3c.186 1.613.293 3.25.315 4.907a.656.656 0 0 1-.658.663v0c-.355 0-.676-.186-.959-.401a1.647 1.647 0 0 0-1.003-.349c-1.036 0-1.875 1.007-1.875 2.25s.84 2.25 1.875 2.25c.369 0 .713-.128 1.003-.349.283-.215.604-.401.959-.401v0c.31 0 .555.26.532.57a48.039 48.039 0 0 1-.642 5.056c1.518.19 3.058.309 4.616.354a.64.64 0 0 0 .657-.643v0c0-.355-.186-.676-.401-.959a1.647 1.647 0 0 1-.349-1.003c0-1.035 1.008-1.875 2.25-1.875 1.243 0 2.25.84 2.25 1.875 0 .369-.128.713-.349 1.003-.215.283-.4.604-.4.959v0c0 .333.277.599.61.58a48.1 48.1 0 0 0 5.427-.63 48.05 48.05 0 0 0 .582-4.717.532.532 0 0 0-.533-.57v0c-.355 0-.676.186-.959.401-.29.221-.634.349-1.003.349-1.035 0-1.875-1.007-1.875-2.25s.84-2.25 1.875-2.25c.37 0 .713.128 1.003.349.283.215.604.401.96.401v0a.656.656 0 0 0 .658-.663 48.422 48.422 0 0 0-.37-5.36c-1.886.342-3.81.574-5.766.689a.578.578 0 0 1-.61-.58v0Z"
                                        />
                                    </svg>
                                    <span>字根</span>
                                </button>
                            {/if}

                            {#if hasConfusionNotes}
                                <button
                                    type="button"
                                    class="deep-dive-btn"
                                    class:active={activeDeepDive ===
                                        "confusion"}
                                    onclick={() => toggleDeepDive("confusion")}
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
                                            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
                                        />
                                    </svg>
                                    <span>易混淆</span>
                                </button>
                            {/if}

                            {#if hasRelatedWords}
                                <button
                                    type="button"
                                    class="deep-dive-btn"
                                    class:active={activeDeepDive === "related"}
                                    onclick={() => toggleDeepDive("related")}
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
                                            d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"
                                        />
                                    </svg>
                                    <span>相關詞</span>
                                </button>
                            {/if}
                        </div>

                        {#if activeDeepDive}
                            <div
                                class="bg-surface-primary rounded-lg border border-border p-4 animate-fade-in"
                            >
                                {#if activeDeepDive === "stats" && entry.frequency && entry.senses}
                                    <StatisticsSection
                                        frequency={entry.frequency}
                                        senses={entry.senses}
                                    />
                                {:else if activeDeepDive === "root" && entry.root_info}
                                    <RootAnalysis rootInfo={entry.root_info} />
                                {:else if activeDeepDive === "confusion" && entry.confusion_notes}
                                    <ConfusionNotes
                                        notes={entry.confusion_notes}
                                        currentLemma={entry.lemma}
                                    />
                                {:else if activeDeepDive === "related"}
                                    <RelatedWords
                                        synonyms={entry.synonyms}
                                        antonyms={entry.antonyms}
                                        derivedForms={entry.derived_forms}
                                    />
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}

<style>
    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.25);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
        z-index: 100;
        animation: fadeIn 0.15s ease-out;
    }

    .modal-container {
        position: relative;
        width: 100%;
        max-width: 600px;
        max-height: calc(100vh - 4rem);
        background: var(--color-surface-page);
        border-radius: 12px;
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-float);
        overflow: hidden;
        animation: slideUp 0.2s ease-out;
    }

    .modal-header {
        display: flex;
        justify-content: flex-end;
        padding: 0.75rem 0.75rem 0;
    }

    .modal-content {
        padding: 0 1.5rem 1.5rem;
        overflow-y: auto;
        max-height: calc(100vh - 8rem);
        scrollbar-width: thin;
        scrollbar-color: var(--color-border-hover) transparent;
    }

    .modal-content::-webkit-scrollbar {
        width: 6px;
    }

    .modal-content::-webkit-scrollbar-track {
        background: transparent;
    }

    .modal-content::-webkit-scrollbar-thumb {
        background-color: var(--color-border-hover);
        border-radius: 3px;
    }

    .close-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 2rem;
        height: 2rem;
        border-radius: 6px;
        color: var(--color-content-tertiary);
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        transition: all 0.15s ease;
    }

    .close-btn:hover {
        color: var(--color-content-primary);
        background: var(--color-surface-hover);
    }

    .deep-dive-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.375rem;
        padding: 0.5rem 0.75rem;
        background: var(--color-surface-primary);
        border: 1px solid transparent;
        border-radius: 6px;
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--color-content-secondary);
        cursor: pointer;
        transition: all 0.15s ease;
    }

    .deep-dive-btn:hover {
        background: var(--color-surface-hover);
        border-color: var(--color-border);
    }

    .deep-dive-btn.active {
        background: var(--color-accent-soft);
        border-color: transparent;
        color: var(--color-accent);
    }

    .deep-dive-btn svg {
        color: var(--color-content-tertiary);
        transition: color 0.15s ease;
    }

    .deep-dive-btn:hover svg,
    .deep-dive-btn.active svg {
        color: var(--color-accent);
    }

    .animate-fade-in {
        animation: fadeIn 0.15s ease-out;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(16px) scale(0.98);
        }
        to {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
    }
</style>
