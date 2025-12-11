<script lang="ts">
    import { getSRSStore } from "$lib/stores/srs.svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { getAppStore } from "$lib/stores/app.svelte";
    import { getNewCards } from "$lib/stores/srs-storage";

    interface Props {
        onStart: (newCardPool: string[]) => void;
    }

    let { onStart }: Props = $props();

    const srs = getSRSStore();
    const vocab = getVocabStore();
    const app = getAppStore();

    const STORAGE_KEY = "gsat_srs_study_settings";

    interface StudySettings {
        newCardLimit: number;
        selectedPos: string[];
        freqMin: number;
        freqMax: number;
        excludePropn: boolean;
        autoSpeak: boolean;
    }

    const defaultSettings: StudySettings = {
        newCardLimit: 20,
        selectedPos: [],
        freqMin: 1,
        freqMax: 100,
        excludePropn: true,
        autoSpeak: true,
    };

    let newCardLimit = $state(defaultSettings.newCardLimit);
    let selectedPos = $state<Set<string>>(new Set(defaultSettings.selectedPos));
    let freqMin = $state(defaultSettings.freqMin);
    let freqMax = $state(defaultSettings.freqMax);
    let excludePropn = $state(defaultSettings.excludePropn);
    let autoSpeak = $state(defaultSettings.autoSpeak);
    let showSettings = $state(false);

    function loadSettings(): void {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const settings: StudySettings = JSON.parse(saved);
                newCardLimit =
                    settings.newCardLimit ?? defaultSettings.newCardLimit;
                selectedPos = new Set(
                    settings.selectedPos ?? defaultSettings.selectedPos,
                );
                freqMin = settings.freqMin ?? defaultSettings.freqMin;
                freqMax = settings.freqMax ?? defaultSettings.freqMax;
                excludePropn =
                    settings.excludePropn ?? defaultSettings.excludePropn;
                autoSpeak = settings.autoSpeak ?? defaultSettings.autoSpeak;
            }
        } catch {
            // ignore
        }
    }

    function saveSettings(): void {
        try {
            const settings: StudySettings = {
                newCardLimit,
                selectedPos: Array.from(selectedPos),
                freqMin,
                freqMax,
                excludePropn,
                autoSpeak,
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
        } catch {
            // ignore
        }
    }

    loadSettings();

    const posOptions = ["NOUN", "VERB", "ADJ", "ADV"];
    const posLabels: Record<string, string> = {
        NOUN: "名詞",
        VERB: "動詞",
        ADJ: "形容詞",
        ADV: "副詞",
    };

    const newCardLemmas = $derived.by(() => {
        return new Set(getNewCards().map((c) => c.lemma));
    });

    const filteredNewCardPool = $derived.by(() => {
        let pool = vocab.index || [];

        pool = pool.filter((w) => newCardLemmas.has(w.lemma));

        if (selectedPos.size > 0) {
            pool = pool.filter((w) => selectedPos.has(w.primary_pos));
        }

        if (excludePropn) {
            pool = pool.filter((w) => w.primary_pos !== "PROPN");
        }

        pool = pool.filter((w) => w.count >= freqMin && w.count <= freqMax);

        return pool.map((w) => w.lemma);
    });

    const actualNewCardCount = $derived(
        Math.min(newCardLimit, filteredNewCardPool.length),
    );

    const todayTotal = $derived(
        srs.deckStats.reviewCount +
            srs.deckStats.learningCount +
            actualNewCardCount,
    );

    const hasCardsToStudy = $derived(
        srs.deckStats.reviewCount > 0 ||
            srs.deckStats.learningCount > 0 ||
            filteredNewCardPool.length > 0,
    );

    function togglePos(pos: string) {
        const newSet = new Set(selectedPos);
        if (newSet.has(pos)) {
            newSet.delete(pos);
        } else {
            newSet.add(pos);
        }
        selectedPos = newSet;
    }

    function handleStart() {
        saveSettings();
        onStart(filteredNewCardPool);
    }
</script>

<div class="flex flex-col lg:flex-row gap-5">
    <div
        class="bg-surface-primary rounded-lg border border-border p-6 lg:p-7 flex-1"
    >
        <h2
            class="text-xl lg:text-2xl font-semibold tracking-tight text-content-primary mb-6"
        >
            今日學習
        </h2>

        <div class="grid grid-cols-3 gap-3 mb-6">
            <div
                class="text-center py-4 lg:py-5 px-2 lg:px-3 rounded-md bg-surface-page/60"
            >
                <div
                    class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight"
                >
                    {srs.deckStats.reviewCount}
                </div>
                <div class="text-sm text-content-secondary mt-1.5">待複習</div>
                <div
                    class="w-1.5 h-1.5 rounded-full bg-srs-again/70 mx-auto mt-2 lg:mt-3"
                ></div>
            </div>
            <div
                class="text-center py-4 lg:py-5 px-2 lg:px-3 rounded-md bg-surface-page/60"
            >
                <div
                    class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight"
                >
                    {srs.deckStats.learningCount}
                </div>
                <div class="text-sm text-content-secondary mt-1.5">學習中</div>
                <div
                    class="w-1.5 h-1.5 rounded-full bg-srs-hard/70 mx-auto mt-2 lg:mt-3"
                ></div>
            </div>
            <div
                class="text-center py-4 lg:py-5 px-2 lg:px-3 rounded-md bg-surface-page/60"
            >
                <div
                    class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight"
                >
                    {filteredNewCardPool.length}
                </div>
                <div class="text-sm text-content-secondary mt-1.5">新卡片</div>
                <div
                    class="w-1.5 h-1.5 rounded-full bg-srs-easy/70 mx-auto mt-2 lg:mt-3"
                ></div>
            </div>
        </div>

        {#if app.isMobile}
            <button
                onclick={() => (showSettings = !showSettings)}
                class="w-full flex items-center justify-between py-2.5 px-1 text-sm text-content-secondary hover:text-content-primary transition-colors rounded mb-4"
            >
                <span>學習設定</span>
                <svg
                    class="w-4 h-4 text-content-tertiary transition-transform {showSettings
                        ? 'rotate-180'
                        : ''}"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="m19 9-7 7-7-7"
                    />
                </svg>
            </button>
        {/if}

        {#if app.isMobile && showSettings}
            <div class="border-t border-border pt-4 mb-4">
                {@render settingsContent()}
            </div>
        {/if}

        <button
            onclick={handleStart}
            disabled={!hasCardsToStudy}
            class="w-full py-3 px-5 bg-content-primary text-white rounded-lg text-base font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
        >
            {#if hasCardsToStudy}
                開始學習
                <span class="text-white/60 ml-1.5">約 {todayTotal} 張</span>
            {:else}
                今日已完成
            {/if}
        </button>

        {#if hasCardsToStudy}
            <div class="text-sm text-content-tertiary text-center mt-3">
                {#if srs.deckStats.learningCount > 0}
                    {srs.deckStats.learningCount} 張學習中
                {/if}
                {#if srs.deckStats.reviewCount > 0}
                    {#if srs.deckStats.learningCount > 0}+{/if}
                    {srs.deckStats.reviewCount} 張複習
                {/if}
                {#if actualNewCardCount > 0}
                    {#if srs.deckStats.learningCount > 0 || srs.deckStats.reviewCount > 0}+{/if}
                    最多 {actualNewCardCount} 張新卡片
                {/if}
            </div>
        {/if}
    </div>

    {#if !app.isMobile}
        <div
            class="bg-surface-primary rounded-lg border border-border p-6 lg:p-7 flex-1 max-w-md"
        >
            <h2
                class="text-lg font-semibold tracking-tight text-content-primary mb-5"
            >
                學習設定
            </h2>
            {@render settingsContent()}
        </div>
    {/if}
</div>

{#snippet settingsContent()}
    <div class="space-y-5">
        <div>
            <label
                for="new-card-limit"
                class="block text-sm font-medium text-content-secondary mb-2"
            >
                每次新卡片上限
            </label>
            <input
                id="new-card-limit"
                type="number"
                bind:value={newCardLimit}
                min="0"
                max="100"
                class="w-full px-3.5 py-2.5 text-sm bg-surface-primary border border-border rounded-md focus:outline-none focus:border-border-hover transition-colors"
            />
            <p class="text-xs text-content-tertiary mt-1.5">
                設為 0 則只複習已學過的卡片
            </p>
        </div>

        <div>
            <span
                class="block text-sm font-medium text-content-secondary mb-2.5"
            >
                新卡片詞性
            </span>
            <div class="flex flex-wrap gap-2">
                <button
                    onclick={() => (selectedPos = new Set())}
                    class="px-3 py-1.5 text-sm font-medium rounded-md transition-all {selectedPos.size ===
                    0
                        ? 'bg-accent-soft text-accent border border-accent/20'
                        : 'bg-surface-page text-content-secondary border border-transparent hover:border-border-hover'}"
                >
                    全部
                </button>
                {#each posOptions as pos}
                    <button
                        onclick={() => togglePos(pos)}
                        class="px-3 py-1.5 text-sm font-medium rounded-md transition-all {selectedPos.has(
                            pos,
                        )
                            ? 'bg-accent-soft text-accent border border-accent/20'
                            : 'bg-surface-page text-content-secondary border border-transparent hover:border-border-hover'}"
                    >
                        {posLabels[pos] || pos}
                    </button>
                {/each}
            </div>
        </div>

        <div>
            <span class="block text-sm font-medium text-content-secondary mb-2">
                新卡片出現頻率
            </span>
            <div class="flex gap-3 items-center">
                <input
                    type="number"
                    bind:value={freqMin}
                    min="1"
                    class="flex-1 px-3 py-2 text-sm bg-surface-primary border border-border rounded-md focus:outline-none focus:border-border-hover transition-colors"
                />
                <span class="text-content-tertiary text-sm">至</span>
                <input
                    type="number"
                    bind:value={freqMax}
                    min="1"
                    class="flex-1 px-3 py-2 text-sm bg-surface-primary border border-border rounded-md focus:outline-none focus:border-border-hover transition-colors"
                />
            </div>
        </div>

        <div class="space-y-2.5">
            <label class="flex items-center gap-3 cursor-pointer group">
                <input
                    type="checkbox"
                    bind:checked={excludePropn}
                    class="w-4 h-4 rounded border-border-hover text-accent focus:ring-0 focus:ring-offset-0"
                />
                <span
                    class="text-sm text-content-secondary group-hover:text-content-primary transition-colors"
                >
                    排除專有名詞
                </span>
            </label>
            <label class="flex items-center gap-3 cursor-pointer group">
                <input
                    type="checkbox"
                    bind:checked={autoSpeak}
                    class="w-4 h-4 rounded border-border-hover text-accent focus:ring-0 focus:ring-offset-0"
                />
                <span
                    class="text-sm text-content-secondary group-hover:text-content-primary transition-colors"
                >
                    自動播放發音
                </span>
            </label>
        </div>
    </div>
{/snippet}
