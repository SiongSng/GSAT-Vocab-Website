import {
  fetchVocabIndex,
  fetchSearchIndex,
  fetchWordDetail,
  getCachedWordDetail,
  type VocabIndexItem,
  type SearchIndex,
  type WordDetail,
} from "$lib/api";

import type { PosFilter } from "$lib/types";
import { getRouterStore, navigate } from "./router.svelte";

let vocabIndex: VocabIndexItem[] = $state.raw([]);
let searchIndex: SearchIndex | null = $state.raw(null);
let selectedWord: WordDetail | null = $state.raw(null);
let selectedLemma: string | null = $state(null);
let isLoading = $state(false);
let isLoadingDetail = $state(false);
let error: string | null = $state(null);
let freqRange = $state({ min: 1, max: 6359 });

let searchTerm = $state("");
let freqMin = $state(1);
let freqMax = $state(20);
let pos: PosFilter = $state("all");

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
    if (searchIndex?.by_pos) {
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

export async function loadVocabData(): Promise<void> {
  if (isLoading || vocabIndex.length > 0) return;

  isLoading = true;
  error = null;

  try {
    const [index, search] = await Promise.all([
      fetchVocabIndex(),
      fetchSearchIndex().catch(() => null),
    ]);

    vocabIndex = index;
    searchIndex = search;

    if (index.length > 0) {
      let min = index[0].count;
      let max = index[0].count;
      for (const w of index) {
        if (w.count < min) min = w.count;
        if (w.count > max) max = w.count;
      }
      freqRange = { min, max };
    }
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load vocabulary data";
    console.error("Failed to load vocab data:", e);
  } finally {
    isLoading = false;
  }
}

export async function selectWord(lemma: string): Promise<void> {
  if (selectedLemma === lemma) return;

  selectedLemma = lemma;

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
