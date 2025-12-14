<script lang="ts">
    import { getSRSStore } from "$lib/stores/srs.svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { getAppStore } from "$lib/stores/app.svelte";
    import { getNewCards, getAllCards } from "$lib/stores/srs-storage";
    import { State } from "ts-fsrs";
    import HelpTooltip from "$lib/components/ui/HelpTooltip.svelte";

    interface Props {
        onStart: (newCardPool: string[], excludeLemmas: Set<string>) => void;
    }

    let { onStart }: Props = $props();

    const srs = getSRSStore();
    const vocab = getVocabStore();
    const app = getAppStore();

    const STORAGE_KEY = "gsat_srs_study_settings";

    interface StudySettings {
        newCardLimit: number;
        autoSpeak: boolean;
        smartMode: boolean;
    }

    const defaultSettings: StudySettings = {
        newCardLimit: 20,
        autoSpeak: true,
        smartMode: true,
    };

    let newCardLimit = $state(defaultSettings.newCardLimit);
    let autoSpeak = $state(defaultSettings.autoSpeak);
    let smartMode = $state(defaultSettings.smartMode);
    let showSettings = $state(false);

    function loadSettings(): void {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const settings: StudySettings = JSON.parse(saved);
                newCardLimit = settings.newCardLimit ?? defaultSettings.newCardLimit;
                autoSpeak = settings.autoSpeak ?? defaultSettings.autoSpeak;
                smartMode = settings.smartMode ?? defaultSettings.smartMode;
            }
        } catch {
            // ignore
        }
    }

    function saveSettings(): void {
        try {
            const settings: StudySettings = {
                newCardLimit,
                autoSpeak,
                smartMode,
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
        } catch {
            // ignore
        }
    }

    loadSettings();

    $effect(() => {
        newCardLimit;
        autoSpeak;
        smartMode;
        saveSettings();
    });

    const newCardLemmas = $derived.by(() => {
        return new Set(getNewCards().map((c) => c.lemma));
    });

    const learnedLemmaCount = $derived.by(() => {
        const cards = getAllCards();
        const learnedLemmas = new Set<string>();
        for (const card of cards) {
            if (card.state !== State.New) {
                learnedLemmas.add(card.lemma);
            }
        }
        return learnedLemmas.size;
    });

    const filteredNewCardPool = $derived.by(() => {
        let pool = vocab.index || [];

        pool = pool.filter((w) => newCardLemmas.has(w.lemma));
        pool = pool.filter((w) => w.primary_pos !== "PROPN");

        if (smartMode) {
            pool = pool.sort((a, b) => b.importance_score - a.importance_score);
        }

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

    const excludedLemmas = $derived.by(() => {
        const propnLemmas = (vocab.index || [])
            .filter((w) => w.primary_pos === "PROPN")
            .map((w) => w.lemma);
        return new Set(propnLemmas);
    });

    function handleStart() {
        onStart(filteredNewCardPool, excludedLemmas);
    }
</script>

<div class="flex flex-col lg:flex-row gap-5">
    <div
        class="bg-surface-primary rounded-lg border border-border p-6 lg:p-8 flex-[1.5]"
    >
        <h2
            class="text-xl lg:text-2xl font-semibold tracking-tight text-content-primary mb-8"
        >
            今日學習
        </h2>

        <div class="grid grid-cols-4 gap-3 lg:gap-4 mb-8">
            <div class="text-center py-4 lg:py-5 px-2 rounded-lg bg-surface-page/60">
                <div class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight leading-none">
                    {srs.deckStats.reviewCount}
                </div>
                <div class="flex items-center justify-center gap-1 text-xs lg:text-sm text-content-secondary mt-1.5">
                    <span>待複習</span>
                    <HelpTooltip text="已學會的卡片，到了排程的複習時間" />
                </div>
                <div class="w-1.5 h-1.5 rounded-full bg-srs-again/70 mx-auto mt-2.5"></div>
            </div>
            <div class="text-center py-4 lg:py-5 px-2 rounded-lg bg-surface-page/60">
                <div class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight leading-none">
                    {srs.deckStats.learningCount}
                </div>
                <div class="flex items-center justify-center gap-1 text-xs lg:text-sm text-content-secondary mt-1.5">
                    <span>學習中</span>
                    <HelpTooltip text="剛開始學的卡片，還在短間隔複習階段" />
                </div>
                <div class="w-1.5 h-1.5 rounded-full bg-srs-hard/70 mx-auto mt-2.5"></div>
            </div>
            <div class="text-center py-4 lg:py-5 px-2 rounded-lg bg-surface-page/60">
                <div class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight leading-none">
                    {filteredNewCardPool.length}
                </div>
                <div class="flex items-center justify-center gap-1 text-xs lg:text-sm text-content-secondary mt-1.5">
                    <span>新卡片</span>
                    <HelpTooltip text="從未學過的卡片" />
                </div>
                <div class="w-1.5 h-1.5 rounded-full bg-srs-easy/70 mx-auto mt-2.5"></div>
            </div>
            <div class="text-center py-4 lg:py-5 px-2 rounded-lg bg-surface-page/60">
                <div class="text-2xl lg:text-3xl font-semibold text-content-primary tracking-tight leading-none">
                    {srs.deckStats.relearningCount}
                </div>
                <div class="flex items-center justify-center gap-1 text-xs lg:text-sm text-content-secondary mt-1.5">
                    <span>待鞏固</span>
                    <HelpTooltip text="複習時忘記了，需要重新鞏固記憶" />
                </div>
                <div class="w-1.5 h-1.5 rounded-full bg-srs-again/70 mx-auto mt-2.5"></div>
            </div>
        </div>

        <div class="mb-6 p-3 bg-surface-page/40 rounded-lg">
            <div class="flex items-center justify-between text-sm">
                <span class="text-content-tertiary">已學習詞彙</span>
                <span class="font-medium text-content-primary">{learnedLemmaCount} 個</span>
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
        <div class="flex items-center justify-between p-3 bg-surface-page/60 rounded-lg">
            <div>
                <span class="text-sm font-medium text-content-primary">智慧推薦模式</span>
                <p class="text-xs text-content-tertiary mt-0.5">
                    {smartMode ? "根據 ML 模型自動安排學習順序" : "隨機順序學習新卡片"}
                </p>
            </div>
            <button
                type="button"
                onclick={() => (smartMode = !smartMode)}
                class="relative w-10 h-6 rounded-full transition-colors {smartMode ? 'bg-accent' : 'bg-border'}"
                role="switch"
                aria-checked={smartMode}
                aria-label="智慧推薦模式"
            >
                <span
                    class="absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-sm transition-transform {smartMode ? 'translate-x-4' : 'translate-x-0'}"
                ></span>
            </button>
        </div>

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

        <div class="space-y-2.5">
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
