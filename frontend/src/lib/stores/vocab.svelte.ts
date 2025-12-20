import type {
  PosFilter,
  VocabTypeFilter,
  TierFilter,
  SortOption,
} from "$lib/types";
import type { VocabEntry, VocabIndexItem } from "$lib/types/vocab";
import { createIndexItem } from "$lib/types/vocab";
import { getRouterStore, navigate } from "./router.svelte";
import { openMobileDetail } from "./app.svelte";
import { initVocabDB, buildIndex, getEntry, getEntriesCount } from "./vocab-db";
import { loadVocabWithVersionCheck, type LoadProgress } from "./vocab-loader";
import { updateWordStructuredData } from "$lib/utils/seo";

let vocabIndex: VocabIndexItem[] = $state.raw([]);
let selectedEntry: VocabEntry | null = $state.raw(null);
let selectedLemma: string | null = $state(null);
let isLoading = $state(false);
let isLoadingDetail = $state(false);
let error: string | null = $state(null);

let loadProgress: LoadProgress | null = $state(null);

let lemmaSet: Set<string> = $state.raw(new Set());

let searchTerm = $state("");
let pos: PosFilter = $state("all");
let vocabType: VocabTypeFilter = $state("all");
let tier: TierFilter = $state("all");
let levels: number[] = $state([]);
let officialOnly = $state(false);
let testedOnly = $state(false);
let sortBy: SortOption = $state("importance_desc");

const filteredWords = $derived.by(() => {
  let result = vocabIndex;

  if (searchTerm) {
    const term = searchTerm.toLowerCase();
    result = result.filter((w) => w.lemma.toLowerCase().startsWith(term));
  }

  if (pos !== "all") {
    result = result.filter((w) => w.pos.includes(pos));
  }

  if (vocabType !== "all") {
    result = result.filter((w) => w.type === vocabType);
  }

  if (tier !== "all") {
    result = result.filter((w) => w.tier === tier);
  }

  if (levels.length > 0) {
    result = result.filter((w) => w.level !== null && levels.includes(w.level));
  }

  if (officialOnly) {
    result = result.filter((w) => w.in_official_list);
  }

  if (testedOnly) {
    result = result.filter((w) => w.tier === "tested");
  }

  switch (sortBy) {
    case "importance_desc":
      result = [...result].sort(
        (a, b) => b.importance_score - a.importance_score,
      );
      break;
    case "importance_asc":
      result = [...result].sort(
        (a, b) => a.importance_score - b.importance_score,
      );
      break;
    case "count_desc":
      result = [...result].sort((a, b) => b.count - a.count);
      break;
    case "count_asc":
      result = [...result].sort((a, b) => a.count - b.count);
      break;
    case "year_spread_desc":
      result = [...result].sort((a, b) => b.year_spread - a.year_spread);
      break;
    case "alphabetical_asc":
      result = [...result].sort((a, b) => a.lemma.localeCompare(b.lemma));
      break;
    case "alphabetical_desc":
      result = [...result].sort((a, b) => b.lemma.localeCompare(a.lemma));
      break;
    case "level_asc":
      result = [...result].sort((a, b) => (a.level ?? 99) - (b.level ?? 99));
      break;
    case "level_desc":
      result = [...result].sort((a, b) => (b.level ?? 0) - (a.level ?? 0));
      break;
  }

  return result;
});

export function getVocabStore() {
  return {
    get index() {
      return vocabIndex;
    },
    get lemmaSet() {
      return lemmaSet;
    },
    get selectedEntry() {
      return selectedEntry;
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
    get filteredWords() {
      return filteredWords;
    },
    get loadProgress() {
      return loadProgress;
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
    get pos() {
      return pos;
    },
    set pos(v: PosFilter) {
      pos = v;
    },
    get vocabType() {
      return vocabType;
    },
    set vocabType(v: VocabTypeFilter) {
      vocabType = v;
    },
    get tier() {
      return tier;
    },
    set tier(v: TierFilter) {
      tier = v;
    },
    get levels() {
      return levels;
    },
    set levels(v: number[]) {
      levels = v;
    },
    get officialOnly() {
      return officialOnly;
    },
    set officialOnly(v: boolean) {
      officialOnly = v;
    },
    get testedOnly() {
      return testedOnly;
    },
    set testedOnly(v: boolean) {
      testedOnly = v;
    },
    get sortBy() {
      return sortBy;
    },
    set sortBy(v: SortOption) {
      sortBy = v;
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
      lemmaSet = new Set(index.map((item) => item.lemma.toLowerCase()));
      return true;
    }
  } catch (e) {
    console.warn("IndexedDB load failed:", e);
  }
  return false;
}

async function downloadAndBuildIndex(): Promise<void> {
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
    lemmaSet = new Set(index.map((item) => item.lemma.toLowerCase()));
    loadProgress = null;
  } catch (e) {
    console.error("Failed to download vocab data:", e);
    loadProgress = null;
    throw e;
  }
}

export async function loadVocabData(): Promise<void> {
  if (isLoading || vocabIndex.length > 0) return;

  isLoading = true;
  error = null;

  try {
    const hasLocalData = await tryLoadFromIndexedDB();

    if (!hasLocalData) {
      await downloadAndBuildIndex();
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
  error = null;

  try {
    await downloadAndBuildIndex();
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
  isLoadingDetail = true;

  try {
    const entry = await getEntry(lemma);
    selectedEntry = entry ?? null;

    if (entry) {
      const definitions = entry.senses.map((s) => s.zh_def);
      const examples = entry.senses
        .flatMap((s) => s.examples?.map((ex) => ex.text) ?? [])
        .filter((text) => text.length > 0);

      updateWordStructuredData({
        lemma: entry.lemma,
        pos: entry.pos,
        definitions,
        examples,
      });
    } else {
      updateWordStructuredData(null);
    }
  } catch (e) {
    console.error("Failed to load word detail:", e);
    selectedEntry = null;
    updateWordStructuredData(null);
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
      openMobileDetail();
    }
  }
}

export function clearSelectedWord(): void {
  selectedEntry = null;
  selectedLemma = null;
  updateWordStructuredData(null);
}

export function setSearchTerm(term: string): void {
  searchTerm = term.toLowerCase();
}

export function setPosFilter(p: PosFilter): void {
  pos = p;
}

export function setVocabTypeFilter(t: VocabTypeFilter): void {
  vocabType = t;
}

export function setTierFilter(t: TierFilter): void {
  tier = t;
}

export function setLevels(l: number[]): void {
  levels = l;
}

export function toggleLevel(level: number): void {
  if (levels.includes(level)) {
    levels = levels.filter((l) => l !== level);
  } else {
    levels = [...levels, level];
  }
}

export function setOfficialOnly(v: boolean): void {
  officialOnly = v;
}

export function setTestedOnly(v: boolean): void {
  testedOnly = v;
}

export function setSortBy(s: SortOption): void {
  sortBy = s;
}

export function resetFilters(): void {
  searchTerm = "";
  pos = "all";
  vocabType = "all";
  tier = "all";
  levels = [];
  officialOnly = false;
  testedOnly = false;
  sortBy = "importance_desc";
}
