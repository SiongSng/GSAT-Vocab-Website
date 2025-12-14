import {
  fetchVocabIndex,
  fetchSearchIndex,
  fetchWordDetail,
  getCachedWordDetail,
  type VocabIndexItem as LegacyVocabIndexItem,
  type SearchIndex,
  type WordDetail,
} from "$lib/api";

import type { PosFilter } from "$lib/types";
import type { VocabEntry, VocabIndexItem } from "$lib/types/vocab";
import { createIndexItem } from "$lib/types/vocab";
import { getRouterStore, navigate } from "./router.svelte";
import {
  initVocabDB,
  buildIndex,
  getEntry,
  getEntriesCount,
} from "./vocab-db";
import {
  loadVocabWithVersionCheck,
  type LoadProgress,
} from "./vocab-loader";

let vocabIndex: VocabIndexItem[] = $state.raw([]);
let searchIndex: SearchIndex | null = $state.raw(null);
let selectedWord: WordDetail | null = $state.raw(null);
let selectedEntry: VocabEntry | null = $state.raw(null);
let selectedLemma: string | null = $state(null);
let isLoading = $state(false);
let isLoadingDetail = $state(false);
let error: string | null = $state(null);
let freqRange = $state({ min: 1, max: 6359 });

let loadProgress: LoadProgress | null = $state(null);
let useNewDataSource = $state(false);

let searchTerm = $state("");
let freqMin = $state(1);
let freqMax = $state(20);
let pos: PosFilter = $state("all");

function convertLegacyToUnified(item: LegacyVocabIndexItem): VocabIndexItem {
  return {
    lemma: item.lemma,
    type: "word",
    pos: [item.primary_pos],
    level: null,
    tier: "basic",
    in_official_list: false,
    sense_count: item.meaning_count,
    zh_preview: item.zh_preview ?? "",
    importance_score: item.count / 100,
    tested_count: 0,
    year_spread: 0,
    count: item.count,
    primary_pos: item.primary_pos,
    meaning_count: item.meaning_count,
  };
}

const filteredWords = $derived.by(() => {
  let result = vocabIndex;

  if (freqMin > 0 || freqMax < freqRange.max) {
    result = result.filter((w) => w.count >= freqMin && w.count <= freqMax);
  }

  if (searchTerm) {
    const term = searchTerm.toLowerCase();
    result = result.filter((w) => w.lemma.toLowerCase().startsWith(term));
  }

  if (pos !== "all") {
    if (useNewDataSource) {
      result = result.filter((w) => w.pos.includes(pos));
    } else if (searchIndex?.by_pos) {
      const posWords = new Set(searchIndex.by_pos[pos] || []);
      result = result.filter((w) => posWords.has(w.lemma));
    } else {
      result = result.filter((w) => w.primary_pos === pos);
    }
  }

  return result;
});

export function getVocabStore() {
  return {
    get index() {
      return vocabIndex;
    },
    get searchIndex() {
      return searchIndex;
    },
    get selectedWord() {
      return selectedWord;
    },
    get selectedEntry() {
      return selectedEntry;
    },
    get selectedWordDetail() {
      return selectedWord;
    },
    get selectedLemma() {
      return selectedLemma;
    },
    get isLoading() {
      return isLoading;
    },
    get isLoadingDetail() {
      return isLoadingDetail;
    },
    get error() {
      return error;
    },
    get freqRange() {
      return freqRange;
    },
    get filteredWords() {
      return filteredWords;
    },
    get loadProgress() {
      return loadProgress;
    },
    get useNewDataSource() {
      return useNewDataSource;
    },
  };
}

export function getFilters() {
  return {
    get searchTerm() {
      return searchTerm;
    },
    set searchTerm(v: string) {
      searchTerm = v;
    },
    get freqMin() {
      return freqMin;
    },
    set freqMin(v: number) {
      freqMin = v;
    },
    get freqMax() {
      return freqMax;
    },
    set freqMax(v: number) {
      freqMax = v;
    },
    get pos() {
      return pos;
    },
    set pos(v: PosFilter) {
      pos = v;
    },
  };
}

async function tryLoadFromIndexedDB(): Promise<boolean> {
  try {
    await initVocabDB();
    const count = await getEntriesCount();

    if (count > 0) {
      const index = await buildIndex(createIndexItem);
      vocabIndex = index;
      useNewDataSource = true;
      return true;
    }
  } catch (e) {
    console.warn("IndexedDB not available, falling back to API:", e);
  }
  return false;
}

async function loadFromNewSource(): Promise<void> {
  loadProgress = {
    phase: "checking",
    current: 0,
    total: 100,
    message: "正在檢查更新...",
  };

  try {
    await loadVocabWithVersionCheck((progress) => {
      loadProgress = progress;
    });

    const index = await buildIndex(createIndexItem);
    vocabIndex = index;
    useNewDataSource = true;
    loadProgress = null;
  } catch (e) {
    console.error("Failed to load from new source:", e);
    loadProgress = null;
    throw e;
  }
}

async function loadFromLegacyAPI(): Promise<void> {
  const [legacyIndex, search] = await Promise.all([
    fetchVocabIndex(),
    fetchSearchIndex().catch(() => null),
  ]);

  vocabIndex = legacyIndex.map(convertLegacyToUnified);
  searchIndex = search;

  if (legacyIndex.length > 0) {
    let min = legacyIndex[0].count;
    let max = legacyIndex[0].count;
    for (const w of legacyIndex) {
      if (w.count < min) min = w.count;
      if (w.count > max) max = w.count;
    }
    freqRange = { min, max };
  }
}

export async function loadVocabData(): Promise<void> {
  if (isLoading || vocabIndex.length > 0) return;

  isLoading = true;
  error = null;

  try {
    const hasLocalData = await tryLoadFromIndexedDB();

    if (hasLocalData) {
      isLoading = false;
      return;
    }

    try {
      await loadFromNewSource();
    } catch {
      console.log("New data source not available, using legacy API");
      await loadFromLegacyAPI();
    }
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load vocabulary data";
    console.error("Failed to load vocab data:", e);
  } finally {
    isLoading = false;
  }
}

export async function forceRefreshData(): Promise<void> {
  isLoading = true;
  loadProgress = {
    phase: "checking",
    current: 0,
    total: 100,
    message: "正在檢查更新...",
  };

  try {
    await loadFromNewSource();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to refresh data";
    console.error("Failed to refresh data:", e);
  } finally {
    isLoading = false;
  }
}

export async function selectWord(lemma: string): Promise<void> {
  if (selectedLemma === lemma) return;

  selectedLemma = lemma;

  if (useNewDataSource) {
    isLoadingDetail = true;
    try {
      const entry = await getEntry(lemma);
      selectedEntry = entry ?? null;

      if (entry) {
        const primarySense = entry.senses[0];
        selectedWord = {
          lemma: entry.lemma,
          count: entry.frequency.total_occurrences,
          meanings: entry.senses.map((s) => ({
            pos: s.pos,
            en_def: s.en_def,
            zh_def: s.zh_def,
          })),
          pos_distribution: entry.pos.reduce(
            (acc, p) => {
              acc[p] = 1;
              return acc;
            },
            {} as Record<string, number>
          ),
          sentences: {
            preview:
              primarySense?.examples.map((ex) => ({
                text: ex.text,
                source: `${ex.source.year} ${ex.source.exam_type} ${ex.source.section_type}`,
              })) ?? [],
            total_count: primarySense?.examples.length ?? 0,
            next_offset: 0,
          },
        };
      } else {
        selectedWord = null;
      }
    } catch (e) {
      console.error("Failed to load word detail from IndexedDB:", e);
      selectedEntry = null;
      selectedWord = null;
    } finally {
      isLoadingDetail = false;
    }
    return;
  }

  const cached = getCachedWordDetail(lemma);
  if (cached) {
    selectedWord = cached;
    isLoadingDetail = false;
    return;
  }

  isLoadingDetail = true;
  try {
    const detail = await fetchWordDetail(lemma);
    selectedWord = detail;
  } catch (e) {
    console.error("Failed to load word detail:", e);
    selectedWord = null;
  } finally {
    isLoadingDetail = false;
  }
}

export async function selectWordAndNavigate(lemma: string): Promise<void> {
  navigate({ name: "word", params: { lemma } });
  await selectWord(lemma);
}

export function syncWordFromRoute(): void {
  const router = getRouterStore();
  if (router.route.name === "word") {
    const lemma = router.route.params.lemma;
    if (lemma && lemma !== selectedLemma) {
      selectWord(lemma);
    }
  }
}

export function clearSelectedWord(): void {
  selectedWord = null;
  selectedEntry = null;
  selectedLemma = null;
}

export function setSearchTerm(term: string): void {
  searchTerm = term.toLowerCase();
}

export function setFreqRange(min: number, max: number): void {
  freqMin = Math.max(freqRange.min, min);
  freqMax = Math.min(freqRange.max, max);
}

export function setPosFilter(p: PosFilter): void {
  pos = p;
}

export function resetFilters(): void {
  searchTerm = "";
  freqMin = 1;
  freqMax = 20;
  pos = "all";
}
