<script lang="ts">
    import {
        getVocabStore,
        getFilters,
        setSearchTerm,
        setFreqRange,
        setPosFilter,
    } from "$lib/stores/vocab.svelte";
    import { getAppStore, closeSidebar } from "$lib/stores/app.svelte";
    import { fetchRandomWord } from "$lib/api";
    import { selectWord } from "$lib/stores/vocab.svelte";
    import type { PosFilter } from "$lib/types";

    const vocab = getVocabStore();
    const filters = getFilters();
    const app = getAppStore();

    let searchValue = $state(filters.searchTerm);
    let freqMinValue = $state(filters.freqMin);
    let freqMaxValue = $state(filters.freqMax);
    let isLoadingRandom = $state(false);

    const posOptions: { value: PosFilter; label: string }[] = [
        { value: "all", label: "全部詞性" },
        { value: "NOUN", label: "名詞" },
        { value: "VERB", label: "動詞" },
        { value: "ADJ", label: "形容詞" },
        { value: "ADV", label: "副詞" },
    ];

    let searchTimeout: ReturnType<typeof setTimeout> | null = null;

    function handleSearchInput(e: Event) {
        const target = e.target as HTMLInputElement;
        searchValue = target.value;

        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        searchTimeout = setTimeout(() => {
            setSearchTerm(searchValue);
        }, 300);
    }

    function handleFreqMinChange() {
        if (freqMinValue > freqMaxValue) {
            freqMinValue = freqMaxValue;
        }
        setFreqRange(freqMinValue, freqMaxValue);
    }

    function handleFreqMaxChange() {
        if (freqMaxValue < freqMinValue) {
            freqMaxValue = freqMinValue;
        }
        setFreqRange(freqMinValue, freqMaxValue);
    }

    function handlePosClick(pos: PosFilter) {
        setPosFilter(pos);
    }

    function handleResetFreq() {
        freqMinValue = 1;
        freqMaxValue = 20;
        setFreqRange(1, 20);
    }

    async function handleRandomWord() {
        if (isLoadingRandom) return;

        isLoadingRandom = true;
        try {
            const word = await fetchRandomWord({
                freqMin: filters.freqMin,
                freqMax: filters.freqMax,
                pos: filters.pos !== "all" ? filters.pos : undefined,
            });
            await selectWord(word.lemma);

            if (app.isMobile) {
                closeSidebar();
            }
        } catch (e) {
            console.error("Failed to fetch random word:", e);
        } finally {
            isLoadingRandom = false;
        }
    }

    function handleOverlayClick() {
        closeSidebar();
    }

    $effect(() => {
        freqMinValue = filters.freqMin;
        freqMaxValue = filters.freqMax;
    });
</script>

{#if app.isSidebarOpen && app.isMobile}
    <button
        class="fixed inset-0 bg-black/30 z-30 lg:hidden"
        onclick={handleOverlayClick}
        aria-label="Close sidebar"
        type="button"
    ></button>
{/if}

<aside
    class="sidebar h-full bg-white border-r border-slate-200 p-4 flex flex-col space-y-6 overflow-y-auto transition-transform duration-300 ease-in-out"
    class:translate-x-0={app.isSidebarOpen || !app.isMobile}
    class:-translate-x-full={!app.isSidebarOpen && app.isMobile}
>
    <div class="relative">
        <svg
            class="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
            />
        </svg>
        <input
            type="text"
            placeholder="搜尋單字..."
            class="w-full bg-slate-100 border border-slate-200 rounded-md py-2 pl-10 pr-4 focus:ring-2 focus:ring-indigo-500 focus:outline-none focus:border-indigo-500 transition"
            value={searchValue}
            oninput={handleSearchInput}
        />
    </div>

    <div>
        <div class="flex justify-between items-center mb-2">
            <h3 class="text-xs font-semibold uppercase text-slate-500">
                按頻率篩選
            </h3>
            <span class="text-xs font-mono text-indigo-600">
                {freqMinValue}-{freqMaxValue}
            </span>
        </div>
        <input
            type="range"
            min={vocab.freqRange.min}
            max={vocab.freqRange.max}
            bind:value={freqMinValue}
            onchange={handleFreqMinChange}
            class="freq-slider w-full mb-2"
        />
        <input
            type="range"
            min={vocab.freqRange.min}
            max={vocab.freqRange.max}
            bind:value={freqMaxValue}
            onchange={handleFreqMaxChange}
            class="freq-slider w-full"
        />
        <div class="mt-3 grid grid-cols-2 gap-2 text-xs">
            <input
                type="number"
                class="w-full px-2 py-1 border rounded"
                min={vocab.freqRange.min}
                max={vocab.freqRange.max}
                bind:value={freqMinValue}
                onchange={handleFreqMinChange}
                placeholder="最小值"
            />
            <input
                type="number"
                class="w-full px-2 py-1 border rounded"
                min={vocab.freqRange.min}
                max={vocab.freqRange.max}
                bind:value={freqMaxValue}
                onchange={handleFreqMaxChange}
                placeholder="最大值"
            />
            <button
                class="col-span-2 filter-btn"
                onclick={handleResetFreq}
                type="button"
            >
                重設為 1-20
            </button>
        </div>
    </div>

    <div>
        <h3 class="text-xs font-semibold uppercase text-slate-500 mb-2">
            按詞性分類
        </h3>
        <div class="grid grid-cols-2 gap-2 text-sm">
            {#each posOptions as option}
                <button
                    class="filter-btn"
                    class:active={filters.pos === option.value}
                    onclick={() => handlePosClick(option.value)}
                    type="button"
                >
                    {option.label}
                </button>
            {/each}
        </div>
    </div>

    <div>
        <button
            class="w-full bg-indigo-600 text-white font-semibold rounded-md py-2.5 hover:bg-indigo-700 active:bg-indigo-800 transition-transform active:scale-95 flex items-center justify-center gap-2 disabled:opacity-50"
            onclick={handleRandomWord}
            disabled={isLoadingRandom}
            type="button"
        >
            {#if isLoadingRandom}
                <svg
                    class="w-5 h-5 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                >
                    <circle
                        class="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="4"
                    ></circle>
                    <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                </svg>
            {:else}
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
                        d="M19.5 12c0-1.232-.046-2.453-.138-3.662a4.006 4.006 0 0 0-3.7-3.7 48.678 48.678 0 0 0-7.324 0 4.006 4.006 0 0 0-3.7 3.7c-.017.22-.032.441-.046.662M19.5 12l3-3m-3 3-3-3m-12 3c0 1.232.046 2.453.138 3.662a4.006 4.006 0 0 0 3.7 3.7 48.656 48.656 0 0 0 7.324 0 4.006 4.006 0 0 0 3.7-3.7c.017-.22.032-.441.046-.662M4.5 12l3 3m-3-3-3 3"
                    />
                </svg>
            {/if}
            隨機一字
        </button>
    </div>
</aside>

<style>
    .freq-slider {
        -webkit-appearance: none;
        appearance: none;
        width: 100%;
        height: 6px;
        background: rgb(226 232 240);
        border-radius: 3px;
        outline: none;
    }

    .freq-slider::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 16px;
        height: 16px;
        background: rgb(99 102 241);
        border-radius: 50%;
        cursor: pointer;
        transition: transform 0.15s ease;
    }

    .freq-slider::-webkit-slider-thumb:hover {
        transform: scale(1.2);
    }

    .freq-slider::-moz-range-thumb {
        width: 16px;
        height: 16px;
        background: rgb(99 102 241);
        border-radius: 50%;
        cursor: pointer;
        border: none;
    }

    .filter-btn {
        padding: 0.5rem 0.75rem;
        background-color: rgb(241 245 249);
        border-radius: 0.375rem;
        font-weight: 500;
        color: rgb(71 85 105);
        transition: all 0.15s ease;
        cursor: pointer;
        border: 1px solid transparent;
    }

    .filter-btn:hover {
        background-color: rgb(226 232 240);
    }

    .filter-btn.active {
        background-color: rgb(238 242 255);
        color: rgb(79 70 229);
        border-color: rgb(165 180 252);
    }

    .sidebar {
        width: 16rem;
        min-width: 200px;
        flex-shrink: 0;
    }

    @media (max-width: 1023px) {
        .sidebar {
            position: absolute;
            inset-y: 0;
            left: 0;
            z-index: 40;
            width: 80%;
            max-width: 20rem;
        }
    }
</style>
