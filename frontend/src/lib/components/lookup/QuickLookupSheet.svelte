<script lang="ts">
    import {
        getWordLookupStore,
        closeLookup,
    } from "$lib/stores/word-lookup.svelte";
    import { selectWordAndNavigate } from "$lib/stores/vocab.svelte";
    import AudioButton from "$lib/components/ui/AudioButton.svelte";
    import BottomSheet from "$lib/components/ui/BottomSheet.svelte";

    const lookup = getWordLookupStore();

    const item = $derived(lookup.mobileItem);
    const primarySense = $derived(item?.entry?.senses?.[0] ?? null);
    const isSheetOpen = $derived(
        lookup.isMobileOpen && lookup.position === "bottom-sheet",
    );

    function handleViewFull() {
        if (item?.lemma) {
            selectWordAndNavigate(item.lemma);
            closeLookup();
        }
    }

    function formatLevel(level: number | null): string {
        if (level === null) return "";
        return `L${level}`;
    }
</script>

<BottomSheet isOpen={isSheetOpen} onClose={closeLookup}>
    {#if item?.isLoading}
        <div class="sheet-content">
            <div class="skeleton-text h-7 w-28 mb-2"></div>
            <div class="skeleton-text h-4 w-20 mb-4"></div>
            <div class="skeleton-text h-4 w-full mb-2"></div>
            <div class="skeleton-text h-4 w-3/4"></div>
        </div>
    {:else if item?.entry}
        <div class="sheet-content">
            <div class="flex items-center justify-between mb-1">
                <div class="flex items-center gap-2">
                    <h2 class="text-2xl font-semibold text-accent">
                        {item.entry.lemma}
                    </h2>
                    <AudioButton text={item.entry.lemma} size="md" />
                </div>
            </div>

            <div
                class="flex items-center gap-1 text-sm text-content-tertiary mb-4"
            >
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
                <p class="text-base text-content-primary leading-relaxed mb-2">
                    {primarySense.zh_def}
                </p>
                {#if primarySense.en_def}
                    <p class="text-sm text-content-secondary leading-relaxed">
                        {primarySense.en_def}
                    </p>
                {/if}
            {/if}

            {#if item.entry.senses && item.entry.senses.length > 1}
                <p class="text-sm text-content-tertiary mt-4">
                    +{item.entry.senses.length - 1} 其他涵義
                </p>
            {/if}

            <button
                type="button"
                class="view-full-btn"
                onclick={handleViewFull}
            >
                查看完整資訊
            </button>
        </div>
    {:else if item}
        <div class="sheet-content">
            <p class="text-base text-content-tertiary">找不到此單字</p>
        </div>
    {/if}
</BottomSheet>

<style>
    .sheet-content {
        padding-top: 8px;
    }

    .view-full-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        margin-top: 24px;
        padding: 14px 20px;
        font-size: 1rem;
        font-weight: 600;
        color: white;
        background-color: var(--color-accent);
        border-radius: 12px;
        transition: all 0.15s ease;
    }

    .view-full-btn:hover {
        opacity: 0.9;
    }

    .view-full-btn:active {
        transform: scale(0.98);
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
