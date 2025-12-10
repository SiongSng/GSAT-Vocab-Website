const API_BASE = "https://gsat-vocab-api.vic0407lu.workers.dev";

export interface VocabIndexItem {
  lemma: string;
  count: number;
  primary_pos: string;
  meaning_count: number;
  zh_preview?: string;
}

export interface SearchIndex {
  by_pos: Record<string, string[]>;
}

export interface WordMeaning {
  pos: string;
  en_def: string;
  zh_def: string;
  usage_note?: string;
}

export interface SentencePreview {
  text: string;
  source: string;
  audio_file?: string;
  variants?: string[];
}

export interface WordDetail {
  lemma: string;
  count: number;
  meanings: WordMeaning[];
  pos_distribution: Record<string, number>;
  sentences: {
    preview: SentencePreview[];
    total_count: number;
    next_offset: number;
  };
}

interface ApiWordDetailResponse {
  lemma: string;
  count: number;
  pos_dist?: Record<string, number>;
  definition?: {
    zh_def: string;
    en_def: string;
    example?: string;
  };
  meanings?: WordMeaning[];
  sentences_preview?: SentencePreview[];
  sentences_total?: number;
  sentences_next_offset?: number;
}

export interface QuizQuestion {
  type: string;
  lemma: string;
  prompt: string;
  options?: { label: string; value: string }[];
  correct: string;
  sentence?: string;
}

const cache = new Map<string, { data: unknown; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000;

function getCached<T>(key: string): T | null {
  const entry = cache.get(key);
  if (entry && Date.now() - entry.timestamp < CACHE_TTL) {
    return entry.data as T;
  }
  cache.delete(key);
  return null;
}

export function getCachedWordDetail(lemma: string): WordDetail | null {
  return getCached<WordDetail>(`word-${lemma}`);
}

function setCache(key: string, data: unknown): void {
  cache.set(key, { data, timestamp: Date.now() });
}

function transformApiResponse(data: ApiWordDetailResponse): WordDetail {
  let meanings: WordMeaning[] = [];

  if (data.meanings && data.meanings.length > 0) {
    meanings = data.meanings;
  } else if (data.definition) {
    const primaryPos = data.pos_dist
      ? Object.entries(data.pos_dist).sort((a, b) => b[1] - a[1])[0]?.[0] ||
        "NOUN"
      : "NOUN";

    meanings = [
      {
        pos: primaryPos,
        zh_def: data.definition.zh_def || "",
        en_def: data.definition.en_def || "",
        usage_note: data.definition.example,
      },
    ];
  }

  return {
    lemma: data.lemma,
    count: data.count,
    meanings,
    pos_distribution: data.pos_dist || {},
    sentences: {
      preview: data.sentences_preview || [],
      total_count: data.sentences_total || 0,
      next_offset: data.sentences_next_offset || 0,
    },
  };
}

export async function fetchVocabIndex(): Promise<VocabIndexItem[]> {
  const cacheKey = "vocab-index";
  const cached = getCached<VocabIndexItem[]>(cacheKey);
  if (cached) return cached;

  const response = await fetch(`${API_BASE}/api/vocab/index`);
  if (!response.ok) {
    throw new Error(`Failed to fetch vocab index: ${response.status}`);
  }
  const data = await response.json();
  setCache(cacheKey, data);
  return data;
}

export async function fetchSearchIndex(): Promise<SearchIndex> {
  const cacheKey = "search-index";
  const cached = getCached<SearchIndex>(cacheKey);
  if (cached) return cached;

  const response = await fetch(`${API_BASE}/api/search-index`);
  if (!response.ok) {
    throw new Error(`Failed to fetch search index: ${response.status}`);
  }
  const data = await response.json();
  setCache(cacheKey, data);
  return data;
}

export async function fetchWordDetail(lemma: string): Promise<WordDetail> {
  const cacheKey = `word-${lemma}`;
  const cached = getCached<WordDetail>(cacheKey);
  if (cached) return cached;

  const response = await fetch(
    `${API_BASE}/api/vocab/detail/${encodeURIComponent(lemma)}`,
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch word detail: ${response.status}`);
  }
  const rawData: ApiWordDetailResponse = await response.json();
  const data = transformApiResponse(rawData);
  setCache(cacheKey, data);
  return data;
}

export async function fetchRandomWord(params?: {
  freqMin?: number;
  freqMax?: number;
  pos?: string;
}): Promise<WordDetail> {
  const url = new URL(`${API_BASE}/api/vocab/random`);
  if (params?.freqMin) url.searchParams.set("freq_min", String(params.freqMin));
  if (params?.freqMax) url.searchParams.set("freq_max", String(params.freqMax));
  if (params?.pos && params.pos !== "all")
    url.searchParams.set("pos", params.pos);

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to fetch random word: ${response.status}`);
  }
  const rawData: ApiWordDetailResponse = await response.json();
  return transformApiResponse(rawData);
}

export async function fetchMoreSentences(
  lemma: string,
  offset: number,
  limit: number = 5,
): Promise<{
  items: SentencePreview[];
  next_offset: number;
  total_count: number;
}> {
  const url = `${API_BASE}/api/vocab/${encodeURIComponent(lemma)}/sentences?offset=${offset}&limit=${limit}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch sentences: ${response.status}`);
  }
  return response.json();
}

export async function generateQuiz(params: {
  type: string;
  count: number;
  freqMin?: number;
  freqMax?: number;
  pos?: string[];
  excludePropn?: boolean;
  lemmas?: string[];
  choiceDirection?: string;
}): Promise<QuizQuestion[]> {
  const url = new URL(`${API_BASE}/api/quiz/generate`);
  url.searchParams.set("type", params.type);
  url.searchParams.set("count", String(params.count));
  if (params.freqMin) url.searchParams.set("freq_min", String(params.freqMin));
  if (params.freqMax) url.searchParams.set("freq_max", String(params.freqMax));
  if (params.pos?.length) url.searchParams.set("pos", params.pos.join(","));
  if (params.excludePropn) url.searchParams.set("exclude_propn", "true");
  if (params.lemmas?.length)
    url.searchParams.set("lemmas", params.lemmas.join(","));
  if (params.choiceDirection)
    url.searchParams.set("choice_direction", params.choiceDirection);

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to generate quiz: ${response.status}`);
  }
  const data = await response.json();
  return data.questions || data;
}

export function getAudioUrl(lemma: string): string {
  return `${API_BASE}/audio/${encodeURIComponent(lemma)}.mp3`;
}

export function getSentenceAudioUrl(audioFile: string): string {
  const base = (audioFile || "").split("/").pop() || audioFile;
  return `${API_BASE}/audio/sentences/${encodeURIComponent(base)}`;
}
