import type { PosFilter, VocabTypeFilter, SortOption } from "$lib/types";
import type {
  WordEntry,
  PhraseEntry,
  PatternEntry,
  VocabIndexItem,
} from "$lib/types/vocab";
import {
  createWordIndexItem,
  createPhraseIndexItem,
  createPatternIndexItem,
  isWordIndexItem,
  isPhraseIndexItem,
  isWordEntry,
  isPhraseEntry,
  isPatternEntry,
} from "$lib/types/vocab";
import { openMobileDetail } from "./app.svelte";
import { goto } from "$app/navigation";
import { base } from "$app/paths";
import {
  initVocabDB,
  buildIndex,
  lookupEntry,
  getSRSEligibleEntry,
  getWord,
  getPhrase,
} from "./vocab-db";
import { loadVocabWithVersionCheck, type LoadProgress } from "./vocab-loader";
import { updateWordStructuredData } from "$lib/utils/seo";
import { runSRSSenseMigration, runSRSEntryTypeFix } from "./srs.svelte";

export type SelectedEntry = WordEntry | PhraseEntry | PatternEntry | null;
export type SelectedEntryType = "word" | "phrase" | "pattern" | null;

let vocabIndex: VocabIndexItem[] = $state.raw([]);
let selectedEntry: SelectedEntry = $state.raw(null);
let selectedEntryType: SelectedEntryType = $state(null);
let selectedLemma: string | null = $state(null);
let isLoading = $state(false);
let isLoadingDetail = $state(false);
let error: string | null = $state(null);

let loadProgress: LoadProgress | null = $state(null);

let lemmaSet: Set<string> = $state.raw(new Set());

let searchTerm = $state("");
let pos: PosFilter = $state("all");
let vocabType: VocabTypeFilter = $state("all");
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
    result = result.filter((w) => {
      if (isWordIndexItem(w)) {
        return w.pos.includes(pos);
      }
      return false;
    });
  }

  if (vocabType !== "all") {
    result = result.filter((w) => w.type === vocabType);
  }

  if (levels.length > 0) {
    result = result.filter((w) => {
      if (isWordIndexItem(w)) {
        return w.level !== null && levels.includes(w.level);
      }
      return false;
    });
  }

  if (officialOnly) {
    result = result.filter((w) => {
      if (isWordIndexItem(w)) {
        return w.in_official_list;
      }
      return false;
    });
  }

  if (testedOnly) {
    result = result.filter((w) => {
      if (isWordIndexItem(w) || isPhraseIndexItem(w)) {
        return w.tested_count > 0;
      }
      return false;
    });
  }

  switch (sortBy) {
    case "importance_desc":
      result = [...result].sort((a, b) => {
        const aScore = "importance_score" in a ? a.importance_score : 0;
        const bScore = "importance_score" in b ? b.importance_score : 0;
        return bScore - aScore;
      });
      break;
    case "importance_asc":
      result = [...result].sort((a, b) => {
        const aScore = "importance_score" in a ? a.importance_score : 0;
        const bScore = "importance_score" in b ? b.importance_score : 0;
        return aScore - bScore;
      });
      break;
    case "count_desc":
      result = [...result].sort((a, b) => {
        const aCount = "total_appearances" in a ? a.total_appearances : 0;
        const bCount = "total_appearances" in b ? b.total_appearances : 0;
        return bCount - aCount;
      });
      break;
    case "count_asc":
      result = [...result].sort((a, b) => {
        const aCount = "total_appearances" in a ? a.total_appearances : 0;
        const bCount = "total_appearances" in b ? b.total_appearances : 0;
        return aCount - bCount;
      });
      break;
    case "year_spread_desc":
      result = [...result].sort((a, b) => {
        const aSpread = "year_spread" in a ? a.year_spread : 0;
        const bSpread = "year_spread" in b ? b.year_spread : 0;
        return bSpread - aSpread;
      });
      break;
    case "alphabetical_asc":
      result = [...result].sort((a, b) => a.lemma.localeCompare(b.lemma));
      break;
    case "alphabetical_desc":
      result = [...result].sort((a, b) => b.lemma.localeCompare(a.lemma));
      break;
    case "level_asc":
      result = [...result].sort((a, b) => {
        const aLevel = isWordIndexItem(a) ? (a.level ?? 99) : 99;
        const bLevel = isWordIndexItem(b) ? (b.level ?? 99) : 99;
        return aLevel - bLevel;
      });
      break;
    case "level_desc":
      result = [...result].sort((a, b) => {
        const aLevel = isWordIndexItem(a) ? (a.level ?? 0) : 0;
        const bLevel = isWordIndexItem(b) ? (b.level ?? 0) : 0;
        return bLevel - aLevel;
      });
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
    get selectedEntryType() {
      return selectedEntryType;
    },
    get selectedLemma() {
      return selectedLemma;
    },
    get isLoading() {
      return isLoading;
    },
    get isLoaded() {
      return vocabIndex.length > 0;
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

async function downloadAndBuildIndex(): Promise<{ isOffline: boolean }> {
  loadProgress = {
    phase: "checking",
    current: 0,
    total: 100,
    message: "正在檢查更新...",
  };

  try {
    const result = await loadVocabWithVersionCheck((progress) => {
      loadProgress = progress;
    });

    const index = await buildIndex(
      createWordIndexItem,
      createPhraseIndexItem,
      createPatternIndexItem,
    );
    vocabIndex = index;
    lemmaSet = new Set(index.map((item) => item.lemma.toLowerCase()));
    loadProgress = null;
    return { isOffline: result.isOffline };
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
  document.getElementById("initial-loader")?.remove();

  try {
    await initVocabDB();
    await downloadAndBuildIndex();

    runSRSSenseMigration(getSRSEligibleEntry).catch((e) => {
      console.warn("SRS sense migration failed:", e);
    });

    runSRSEntryTypeFix(getWord, getPhrase).then((fixedCount) => {
      if (fixedCount > 0) {
        console.log(`Fixed entry_type for ${fixedCount} cards`);
      }
    }).catch((e) => {
      console.warn("SRS entry type fix failed:", e);
    });
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load vocabulary data";
    console.error("Failed to load vocab data:", e);
  } finally {
    isLoading = false;
    loadProgress = null;
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

function determineEntryType(
  entry: WordEntry | PhraseEntry | PatternEntry,
): SelectedEntryType {
  if (isPatternEntry(entry)) {
    return "pattern";
  }
  if (isWordEntry(entry)) {
    return "word";
  }
  if (isPhraseEntry(entry)) {
    return "phrase";
  }
  return null;
}

export async function selectWord(
  lemma: string,
  typeHint?: "word" | "phrase" | "pattern",
): Promise<void> {
  if (selectedLemma === lemma) return;

  selectedLemma = lemma;
  isLoadingDetail = true;

  try {
    const entry = await lookupEntry(lemma, typeHint);
    if (entry) {
      selectedEntry = entry;
      selectedEntryType = determineEntryType(entry);

      if (selectedEntryType === "word" || selectedEntryType === "phrase") {
        const wordOrPhrase = entry as WordEntry | PhraseEntry;
        const definitions = wordOrPhrase.senses.map((s) => s.zh_def);
        const examples = wordOrPhrase.senses
          .flatMap((s) => s.examples?.map((ex) => ex.text) ?? [])
          .filter((text) => text.length > 0);

        updateWordStructuredData({
          lemma: wordOrPhrase.lemma,
          pos: selectedEntryType === "word" ? (entry as WordEntry).pos : [],
          definitions,
          examples,
        });
      } else {
        updateWordStructuredData(null);
      }
    } else {
      selectedEntry = null;
      selectedEntryType = null;
      updateWordStructuredData(null);
    }
  } catch (e) {
    console.error("Failed to load word detail:", e);
    selectedEntry = null;
    selectedEntryType = null;
    updateWordStructuredData(null);
  } finally {
    isLoadingDetail = false;
  }
}

export async function selectWordAndNavigate(
  lemma: string,
  typeHint?: "word" | "phrase" | "pattern",
): Promise<void> {
  const isMobile = window.matchMedia("(max-width: 1023px)").matches;

  if (isMobile) {
    await goto(`${base}/word/${encodeURIComponent(lemma)}`, { replaceState: false });
  } else {
    history.replaceState({}, "", `${base}/word/${encodeURIComponent(lemma)}`);
  }

  await selectWord(lemma, typeHint);
}

export function syncWordFromRoute(lemma: string | null): void {
  if (lemma && lemma !== selectedLemma) {
    selectWord(lemma);
    openMobileDetail();
  }
}

export function clearSelectedWord(): void {
  selectedEntry = null;
  selectedEntryType = null;
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
  levels = [];
  officialOnly = false;
  testedOnly = false;
  sortBy = "importance_desc";
}
