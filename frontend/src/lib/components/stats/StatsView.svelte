<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import {
        getAllDailyStats,
        getAllCards,
        onDataChange,
    } from "$lib/stores/srs-storage";
    import { initSRS } from "$lib/stores/srs.svelte";
    import {
        calculateStreak,
        getLast7DaysStats,
        getMasteryProgress,
        getHeatmapData,
        getMultiSenseProgress,
        type StreakInfo,
        type MasteryProgress,
        type HeatmapCell,
        type MultiSenseProgress,
    } from "$lib/utils/stats";
    import type { DailyStats } from "$lib/types/srs";
    import { getAppStore } from "$lib/stores/app.svelte";
    import { getVocabStore, loadVocabData } from "$lib/stores/vocab.svelte";
    import YearlyHeatmap from "./YearlyHeatmap.svelte";
    import NotificationSettings from "./NotificationSettings.svelte";
    import HelpTooltip from "$lib/components/ui/HelpTooltip.svelte";

    const app = getAppStore();
    const vocab = getVocabStore();

    let streakInfo: StreakInfo = $state({
        currentStreak: 0,
        longestStreak: 0,
        lastStudyDate: null,
        isActiveToday: false,
    });
    let last7Days: DailyStats[] = $state([]);
    // Removed unused allCards state
    let heatmapData: HeatmapCell[][] = $state.raw([]);
    let isLoading = $state(true);
    let showSettings = $state(false);

    // Mastery calculation state
    let masteryProgress: MasteryProgress = $state({
        new: 0,
        learning: 0,
        review: 0,
        mastered: 0,
        total: 0,
    });

    // Multi-sense progress state
    let multiSenseProgress: MultiSenseProgress = $state({
        totalSenses: 0,
        masteredSenses: 0,
        activeSenses: 0,
        wordsFullyMastered: 0,
        wordsPartiallyMastered: 0,
        wordsStarted: 0,
        wordsNotStarted: 0,
        multiSenseWords: 0,
    });

    // Helper to calculate mastery (non-reactive to avoid freezing)
    // Only considers top 75% importance words
    function calculateMasteryStats(cards: any[], vocabList: any[]) {
        try {
            if (vocabList && vocabList.length > 0) {
                // Sort by importance_score descending and take top 75%
                const sortedVocab = [...vocabList]
                    .filter((v) => v && v.importance_score > 0)
                    .sort((a, b) => b.importance_score - a.importance_score);

                const top75Count = Math.ceil(sortedVocab.length * 0.75);
                const importantLemmas = new Set(
                    sortedVocab.slice(0, top75Count).map((v) => v.lemma),
                );

                // Filter cards to only those in important lemmas
                const filteredCards = cards.filter((card) =>
                    importantLemmas.has(card.lemma),
                );

                // Get progress from existing cards
                const progress = getMasteryProgress(filteredCards);

                // Calculate how many important words have no card yet
                const cardsLemmaSet = new Set(
                    filteredCards.map((c) => c.lemma),
                );
                const notStartedCount = top75Count - cardsLemmaSet.size;

                // Update: "new" means not started (no card or State.New)
                // progress.new (State.New cards) should be counted as not started
                masteryProgress = {
                    mastered: progress.mastered,
                    review: progress.review,
                    learning: progress.learning,
                    new: notStartedCount + progress.new,
                    total: top75Count,
                };

                // Calculate multi-sense progress for all vocab (not just top 75%)
                multiSenseProgress = getMultiSenseProgress(cards, vocabList);
            } else {
                masteryProgress = getMasteryProgress(cards);
            }
        } catch (e) {
            console.error("Error calculating mastery:", e);
            masteryProgress = getMasteryProgress(cards);
        }
    }

    async function loadData() {
        isLoading = true;

        // Ensure SRS is initialized (uses cache if already done)
        await initSRS();

        // Use Promise.all only for truly async tasks
        const promises: Promise<any>[] = [getAllDailyStats()];

        // Only trigger vocab load if needed, don't await if already loading
        if (vocab.index.length === 0) {
            loadVocabData().catch(console.error);
        }

        const [stats] = await Promise.all(promises);

        // Get cards synchronously from cache (fast!)
        const cards = getAllCards();

        streakInfo = calculateStreak(stats);
        last7Days = getLast7DaysStats(stats);
        heatmapData = getHeatmapData(stats);

        // Initial calculation
        if (vocab.index.length > 0) {
            calculateMasteryStats(cards, vocab.index);
        } else {
            masteryProgress = getMasteryProgress(cards);
        }

        isLoading = false;

        // Check for vocab update
        if (vocab.index.length === 0) {
            setTimeout(() => {
                if (vocab.index.length > 0) {
                    calculateMasteryStats(cards, vocab.index);
                }
            }, 500);
        }
    }

    const unsubscribe = onDataChange(() => {
        loadData();
    });

    onMount(() => {
        loadData();
    });

    onDestroy(() => {
        unsubscribe();
    });

    // Calculate max value for bar chart scaling
    const maxBarValue = $derived.by(() => {
        const max = Math.max(...last7Days.map((s) => s.new_cards + s.reviews));
        return Math.max(max, 1);
    });

    function getBarHeight(stat: DailyStats): number {
        const total = stat.new_cards + stat.reviews;
        if (total === 0) return 0;
        return Math.max((total / maxBarValue) * 100, 8);
    }

    function getDayLabel(dateStr: string): string {
        const date = new Date(dateStr + "T00:00:00");
        const days = ["日", "一", "二", "三", "四", "五", "六"];
        return days[date.getDay()];
    }

    function isToday(dateStr: string): boolean {
        const today = new Date();
        const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
        return dateStr === todayStr;
    }

    // Mastery percentage
    const masteredPercentage = $derived.by(() => {
        if (masteryProgress.total === 0) return 0;
        return Math.round(
            (masteryProgress.mastered / masteryProgress.total) * 100,
        );
    });
</script>

<div class="stats-page">
    {#if isLoading}
        <div class="loading-container">
            <div class="skeleton skeleton-card"></div>
            <div class="skeleton skeleton-card-small"></div>
        </div>
    {:else}
        <!-- Header -->
        <header class="page-header">
            <h1 class="page-title">學習統計</h1>
        </header>

        <!-- Main Layout -->
        <div class="stats-grid">
            <!-- Main Card: Streak + Weekly -->
            <div class="main-card grid-main-top">
                <!-- Streak Hero -->
                <div class="streak-section">
                    <div class="streak-hero">
                        <span class="streak-hero-number"
                            >{streakInfo.currentStreak}</span
                        >
                        <span class="streak-hero-label">天連續</span>
                        {#if streakInfo.isActiveToday}
                            <span class="streak-today-badge">今日 ✓</span>
                        {/if}
                    </div>
                </div>

                <!-- Weekly Chart -->
                <div class="weekly-section">
                    <h2 class="section-title">過去 7 天</h2>
                    <div class="bar-chart">
                        {#each last7Days as stat}
                            {@const total = stat.new_cards + stat.reviews}
                            {@const height = getBarHeight(stat)}
                            <div class="bar-column">
                                <div class="bar-area">
                                    {#if total > 0}
                                        <span class="bar-value">{total}</span>
                                    {/if}
                                    <div class="bar-track">
                                        <div
                                            class="bar"
                                            class:bar-today={isToday(stat.date)}
                                            style="height: {height}%"
                                        ></div>
                                    </div>
                                </div>
                                <span
                                    class="day-label"
                                    class:day-today={isToday(stat.date)}
                                >
                                    {getDayLabel(stat.date)}
                                </span>
                            </div>
                        {/each}
                    </div>
                </div>

                <!-- Mobile: Settings toggle -->
                {#if app.isMobile}
                    <div class="mobile-settings-wrapper">
                        <button
                            class="settings-toggle"
                            onclick={() => (showSettings = !showSettings)}
                        >
                            <span class="toggle-text">學習提醒</span>
                            <svg
                                class="toggle-chevron"
                                class:toggle-open={showSettings}
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
                        {#if showSettings}
                            <div class="mobile-settings">
                                <NotificationSettings showTitle={false} />
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>

            <!-- Mastery Progress Card -->
            <div class="side-card grid-side-top">
                <div class="section-title-row">
                    <h3 class="section-title">掌握進度</h3>
                    <HelpTooltip text="僅計算重要性前 75% 的單字" />
                </div>
                <div class="mastery-content">
                    <div class="mastery-ring-container">
                        <svg viewBox="0 0 100 100" class="mastery-ring">
                            <!-- Background circle -->
                            <circle
                                cx="50"
                                cy="50"
                                r="40"
                                fill="none"
                                stroke="var(--color-surface-secondary)"
                                stroke-width="8"
                            />
                            {#if masteryProgress.total > 0}
                                {@const circumference = 2 * Math.PI * 40}
                                {@const masteredPct =
                                    masteryProgress.mastered /
                                    masteryProgress.total}
                                {@const reviewPct =
                                    masteryProgress.review /
                                    masteryProgress.total}
                                {@const learningPct =
                                    masteryProgress.learning /
                                    masteryProgress.total}

                                <!-- Learning (blue) - drawn first, will be at the end -->
                                {#if learningPct > 0}
                                    <circle
                                        cx="50"
                                        cy="50"
                                        r="40"
                                        fill="none"
                                        stroke="var(--color-srs-easy)"
                                        stroke-width="8"
                                        stroke-dasharray="{(masteredPct +
                                            reviewPct +
                                            learningPct) *
                                            circumference} {circumference}"
                                        stroke-linecap="round"
                                        transform="rotate(-90 50 50)"
                                    />
                                {/if}
                                <!-- Review (orange) - drawn second, overlaps learning -->
                                {#if reviewPct > 0 || masteredPct > 0}
                                    <circle
                                        cx="50"
                                        cy="50"
                                        r="40"
                                        fill="none"
                                        stroke="var(--color-srs-hard)"
                                        stroke-width="8"
                                        stroke-dasharray="{(masteredPct +
                                            reviewPct) *
                                            circumference} {circumference}"
                                        stroke-linecap="round"
                                        transform="rotate(-90 50 50)"
                                    />
                                {/if}
                                <!-- Mastered (green) - drawn last, on top -->
                                {#if masteredPct > 0}
                                    <circle
                                        cx="50"
                                        cy="50"
                                        r="40"
                                        fill="none"
                                        stroke="var(--color-srs-good)"
                                        stroke-width="8"
                                        stroke-dasharray="{masteredPct *
                                            circumference} {circumference}"
                                        stroke-linecap="round"
                                        transform="rotate(-90 50 50)"
                                    />
                                {/if}
                            {/if}
                        </svg>
                        <div class="ring-center">
                            <span class="ring-value">{masteredPercentage}%</span
                            >
                            <span class="ring-label">精熟</span>
                        </div>
                    </div>
                    <div class="mastery-legend">
                        <div class="legend-item">
                            <div class="legend-info">
                                <span
                                    class="legend-dot"
                                    style="background: var(--color-srs-good);"
                                ></span>
                                <span class="legend-label">精熟</span>
                                <HelpTooltip text="穩定度達 21 天以上" />
                            </div>
                            <span class="legend-value"
                                >{masteryProgress.mastered}</span
                            >
                        </div>
                        <div class="legend-item">
                            <div class="legend-info">
                                <span
                                    class="legend-dot"
                                    style="background: var(--color-srs-hard);"
                                ></span>
                                <span class="legend-label">複習中</span>
                            </div>
                            <span class="legend-value"
                                >{masteryProgress.review}</span
                            >
                        </div>
                        <div class="legend-item">
                            <div class="legend-info">
                                <span
                                    class="legend-dot"
                                    style="background: var(--color-srs-easy);"
                                ></span>
                                <span class="legend-label">學習中</span>
                            </div>
                            <span class="legend-value"
                                >{masteryProgress.learning}</span
                            >
                        </div>
                        <div class="legend-item">
                            <div class="legend-info">
                                <span
                                    class="legend-dot"
                                    style="background: var(--color-surface-secondary);"
                                ></span>
                                <span class="legend-label">未學習</span>
                            </div>
                            <span class="legend-value"
                                >{masteryProgress.new}</span
                            >
                        </div>
                    </div>
                </div>
            </div>

            <!-- Multi-sense Progress Card -->
            {#if multiSenseProgress.multiSenseWords > 0}
                <div class="side-card multi-sense-card">
                    <div class="section-title-row">
                        <h3 class="section-title">多義詞學習</h3>
                        <HelpTooltip text="追蹤一字多義的學習進度，這是學測重點" />
                    </div>
                    <div class="multi-sense-content">
                        <div class="sense-stats-row">
                            <div class="sense-stat">
                                <span class="sense-stat-value">{multiSenseProgress.masteredSenses}</span>
                                <span class="sense-stat-label">字義精熟</span>
                            </div>
                            <div class="sense-stat-divider"></div>
                            <div class="sense-stat">
                                <span class="sense-stat-value">{multiSenseProgress.totalSenses}</span>
                                <span class="sense-stat-label">總字義數</span>
                            </div>
                        </div>
                        <div class="multi-sense-legend">
                            <div class="legend-item">
                                <div class="legend-info">
                                    <span class="legend-dot" style="background: var(--color-srs-good);"></span>
                                    <span class="legend-label">完全精熟</span>
                                </div>
                                <span class="legend-value">{multiSenseProgress.wordsFullyMastered}</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-info">
                                    <span class="legend-dot" style="background: var(--color-srs-hard);"></span>
                                    <span class="legend-label">部分精熟</span>
                                </div>
                                <span class="legend-value">{multiSenseProgress.wordsPartiallyMastered}</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-info">
                                    <span class="legend-dot" style="background: var(--color-srs-easy);"></span>
                                    <span class="legend-label">學習中</span>
                                </div>
                                <span class="legend-value">{multiSenseProgress.wordsStarted}</span>
                            </div>
                        </div>
                        <p class="multi-sense-hint">
                            共 {multiSenseProgress.multiSenseWords} 個多義詞
                        </p>
                    </div>
                </div>
            {/if}

            <!-- Heatmap Card -->
            <div class="heatmap-card grid-main-bottom">
                <YearlyHeatmap data={heatmapData} />
            </div>

            <!-- Notification Settings Card (Desktop Only) -->
            {#if !app.isMobile}
                <div class="notification-card grid-side-bottom">
                    <NotificationSettings showTitle={true} />
                </div>
            {/if}
        </div>
    {/if}
</div>

<style>
    .stats-page {
        min-height: 100%;
        background-color: var(--color-surface-page);
        padding: 1rem;
        padding-bottom: calc(5rem + env(safe-area-inset-bottom, 0px));
    }

    @media (min-width: 640px) {
        .stats-page {
            padding: 1rem 1.5rem;
        }
    }

    @media (min-width: 1024px) {
        .stats-page {
            padding: 1.5rem 1rem;
            padding-bottom: 1.5rem;
            max-width: 1100px;
            margin: 0 auto;
        }
    }

    /* Loading */
    .loading-container {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .skeleton {
        background: linear-gradient(
            90deg,
            var(--color-surface-secondary) 25%,
            var(--color-surface-page) 50%,
            var(--color-surface-secondary) 75%
        );
        background-size: 200% 100%;
        animation: shimmer 2.5s infinite;
        border-radius: 0.5rem;
    }

    .skeleton-card {
        height: 280px;
    }

    .skeleton-card-small {
        height: 180px;
    }

    @keyframes shimmer {
        0% {
            background-position: 200% 0;
        }
        100% {
            background-position: -200% 0;
        }
    }

    /* Header */
    .page-header {
        margin-bottom: 1.25rem;
    }

    .page-title {
        font-size: 1.25rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        color: var(--color-content-primary);
        margin: 0;
    }

    @media (min-width: 768px) {
        .page-title {
            font-size: 1.5rem;
        }
    }

    /* Layout */
    .stats-grid {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    @media (min-width: 768px) {
        .stats-grid {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 280px;
            grid-template-rows: auto auto;
            gap: 1.25rem;
        }

        .grid-main-top {
            grid-column: 1;
            grid-row: 1;
        }

        .grid-side-top {
            grid-column: 2;
            grid-row: 1;
        }

        .grid-main-bottom {
            grid-column: 1;
            grid-row: 2;
        }

        .grid-side-bottom {
            grid-column: 2;
            grid-row: 2;
        }
    }

    /* Cards */
    .main-card,
    .side-card,
    .heatmap-card,
    .notification-card {
        background-color: var(--color-surface-primary);
        border-radius: 0.75rem;
        border: 1px solid var(--color-border);
        padding: 1.25rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }

    @media (min-width: 768px) {
        .main-card {
            padding: 1.75rem;
        }
    }

    /* Streak Section */
    .streak-section {
        margin-bottom: 2rem;
        padding-bottom: 2rem;
        border-bottom: 1px dashed var(--color-border);
    }

    .streak-hero {
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
    }

    .streak-hero-number {
        font-size: 3.5rem;
        font-weight: 600;
        line-height: 1;
        letter-spacing: -0.03em;
        color: var(--color-content-primary);
    }

    .streak-hero-label {
        font-size: 1.125rem;
        color: var(--color-content-tertiary);
    }

    .streak-today-badge {
        margin-left: 0.5rem;
        padding: 0.25rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        background-color: var(--color-srs-good);
        color: white;
    }

    .section-title-row {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        margin-bottom: 1.25rem;
    }

    .section-title-row .section-title {
        margin: 0;
    }

    .section-title {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--color-section-header);
        margin: 0 0 1.25rem 0;
    }

    /* Bar Chart */
    .weekly-section {
        min-width: 0;
    }

    .bar-chart {
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
        height: 140px;
        align-items: flex-end;
        padding-top: 1rem;
    }

    .bar-column {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
        gap: 0.5rem;
        height: 100%;
    }

    .bar-area {
        flex: 1;
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-end;
        position: relative;
    }

    .bar-value {
        position: absolute;
        top: -1.5rem;
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--color-content-primary);
    }

    .bar-track {
        width: 100%;
        max-width: 1.5rem;
        height: 100%;
        /* Make track more subtle or transparent based on feedback */
        background-color: var(--color-surface-secondary);
        border-radius: 9999px; /* Fuller rounding */
        display: flex;
        align-items: flex-end;
        overflow: hidden;
    }

    .bar {
        width: 100%;
        background-color: var(--color-border-hover); /* Default: Gray */
        border-radius: 9999px; /* Match track */
        transition: height 0.3s ease;
    }

    .bar:hover {
        background-color: var(--color-content-tertiary);
    }

    .bar-today {
        background-color: var(
            --color-content-primary
        ); /* Today: Black/Primary */
    }

    .day-label {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
    }

    .day-today {
        color: var(--color-content-primary);
        font-weight: 600;
    }

    /* Mobile Settings Toggle */
    .mobile-settings-wrapper {
        margin-top: 1.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid var(--color-border);
    }

    .settings-toggle {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0;
        cursor: pointer;
        color: var(--color-content-primary);
        font-weight: 500;
        font-size: 0.875rem;
    }

    .toggle-chevron {
        width: 1rem;
        height: 1rem;
        color: var(--color-content-tertiary);
        transition: transform 0.2s ease;
    }

    .toggle-open {
        transform: rotate(180deg);
    }

    .mobile-settings {
        padding-top: 0.75rem;
    }

    /* Mastery Ring */
    .mastery-content {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        margin-top: 1rem;
    }

    .mastery-ring-container {
        position: relative;
        width: 120px;
        height: 120px;
        align-self: center;
    }

    .mastery-ring {
        width: 100%;
        height: 100%;
    }

    .ring-center {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        text-align: center;
    }

    .ring-value {
        display: block;
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--color-content-primary);
        line-height: 1;
        letter-spacing: -0.02em;
    }

    .ring-label {
        display: block;
        font-size: 0.75rem;
        color: var(--color-content-secondary);
        margin-top: 0.25rem;
    }

    /* Mastery Legend */
    .mastery-legend {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        width: 100%;
    }

    .legend-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.25rem 0;
    }

    .legend-info {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .legend-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .legend-label {
        font-size: 0.875rem;
        color: var(--color-content-secondary);
    }

    .legend-value {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--color-content-primary);
        font-variant-numeric: tabular-nums;
    }

    /* Multi-sense Card */
    .multi-sense-card {
        margin-top: 1rem;
    }

    @media (min-width: 768px) {
        .multi-sense-card {
            grid-column: 2;
            grid-row: 2;
            margin-top: 0;
        }

        .grid-side-bottom {
            grid-row: 3;
        }
    }

    .multi-sense-content {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        margin-top: 1rem;
    }

    .sense-stats-row {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1.5rem;
        padding: 0.75rem 0;
    }

    .sense-stat {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.25rem;
    }

    .sense-stat-value {
        font-size: 2rem;
        font-weight: 600;
        color: var(--color-content-primary);
        line-height: 1;
        letter-spacing: -0.02em;
        font-variant-numeric: tabular-nums;
    }

    .sense-stat-label {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
    }

    .sense-stat-divider {
        width: 1px;
        height: 2rem;
        background: var(--color-border);
    }

    .multi-sense-legend {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .multi-sense-hint {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
        text-align: center;
        margin: 0;
        padding-top: 0.5rem;
        border-top: 1px dashed var(--color-border);
    }
</style>
