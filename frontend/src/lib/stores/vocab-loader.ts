import type { VocabDatabase, VersionInfo, WordEntry, PhraseEntry } from "$lib/types/vocab";
import {
  setStoredVersion,
  getStoredMetadata,
  setStoredMetadata,
  getStoredVersionInfo,
  setStoredVersionInfo,
  clearAllStores,
  bulkInsertWords,
  bulkInsertPhrases,
  bulkInsertPatterns,
  getTotalEntriesCount,
} from "./vocab-db";
import { base } from "$app/paths";

function getDataUrl(path: string): string {
  return `${base}/data/${path}`;
}

function createGenerationFingerprint(versionInfo: VersionInfo): string {
  const generation = versionInfo.generated_at ?? versionInfo.version;
  return [generation, versionInfo.vocab_hash, versionInfo.entry_count].join(
    "|",
  );
}

export interface LoadProgress {
  phase: "checking" | "downloading" | "decompressing" | "storing" | "ready";
  current: number;
  total: number;
  message: string;
}

const VERSION_CHECK_TIMEOUT_MS = 5000;

export async function fetchVersionInfo(): Promise<VersionInfo> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), VERSION_CHECK_TIMEOUT_MS);

  try {
    const response = await fetch(`${getDataUrl('version.json')}?t=${Date.now()}`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch version info: ${response.status}`);
    }
    return response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export interface UpdateCheckResult {
  needsUpdate: boolean;
  remoteVersion: VersionInfo | null;
  isOffline: boolean;
  hasLocalData: boolean;
}

export async function checkForUpdate(): Promise<UpdateCheckResult> {
  const [localVersionInfo, localMetadata, totalEntries] = await Promise.all([
    getStoredVersionInfo(),
    getStoredMetadata(),
    getTotalEntriesCount(),
  ]);

  const hasLocalData = totalEntries > 0;

  let remoteVersion: VersionInfo | null = null;
  try {
    remoteVersion = await fetchVersionInfo();
  } catch {
    return {
      needsUpdate: !hasLocalData,
      remoteVersion: null,
      isOffline: true,
      hasLocalData,
    };
  }

  const remoteFingerprint = createGenerationFingerprint(remoteVersion);
  const localFingerprint = localVersionInfo
    ? createGenerationFingerprint(localVersionInfo)
    : null;

  const remoteGeneration = remoteVersion.generated_at ?? remoteVersion.version;
  const localGeneration =
    localVersionInfo?.generated_at ?? localVersionInfo?.version;
  const generationChanged =
    !localGeneration || localGeneration !== remoteGeneration;

  const fingerprintChanged =
    !localFingerprint || localFingerprint !== remoteFingerprint;
  const hashChanged =
    localMetadata?.vocab_hash !== remoteVersion.vocab_hash;
  const entriesMismatch =
    totalEntries === 0 || totalEntries !== remoteVersion.entry_count;

  const needsUpdate =
    generationChanged || fingerprintChanged || hashChanged || entriesMismatch;

  return { needsUpdate, remoteVersion, isOffline: false, hasLocalData };
}

async function decompressGzipStream(
  response: Response,
): Promise<VocabDatabase> {
  if (!response.body) {
    throw new Error("Response body is null");
  }

  const decompressionStream = new DecompressionStream("gzip");
  const decompressedStream = response.body.pipeThrough(decompressionStream);

  const reader = decompressedStream.getReader();
  const chunks: Uint8Array[] = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
  }

  const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
  const combined = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.length;
  }

  const text = new TextDecoder().decode(combined);
  return JSON.parse(text);
}

async function decompressGzipFallback(
  response: Response,
): Promise<VocabDatabase> {
  const arrayBuffer = await response.arrayBuffer();
  const blob = new Blob([arrayBuffer]);
  const ds = new DecompressionStream("gzip");
  const decompressedStream = blob.stream().pipeThrough(ds);
  const decompressedResponse = new Response(decompressedStream);
  const text = await decompressedResponse.text();
  return JSON.parse(text);
}

export async function downloadAndStoreVocab(
  onProgress?: (progress: LoadProgress) => void,
  versionInfo?: VersionInfo,
): Promise<void> {
  const resolvedVersionInfo = versionInfo ?? (await fetchVersionInfo());

  onProgress?.({
    phase: "downloading",
    current: 0,
    total: 100,
    message: "正在下載詞彙資料...",
  });

  const vocabUrl = resolvedVersionInfo?.vocab_hash
    ? `${getDataUrl('vocab.json.gz')}?hash=${resolvedVersionInfo.vocab_hash}`
    : `${getDataUrl('vocab.json.gz')}?t=${Date.now()}`;

  const response = await fetch(vocabUrl, { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`Failed to download vocab data: ${response.status}`);
  }

  onProgress?.({
    phase: "decompressing",
    current: 0,
    total: 100,
    message: "正在解壓縮資料...",
  });

  let vocabData: VocabDatabase;
  const contentEncoding = response.headers.get("Content-Encoding");

  if (contentEncoding === "gzip") {
    vocabData = await response.json();
  } else {
    try {
      const clonedResponse = response.clone();
      vocabData = await decompressGzipStream(clonedResponse);
    } catch {
      try {
        vocabData = await decompressGzipFallback(response);
      } catch {
        const text = await response.text();
        vocabData = JSON.parse(text);
      }
    }
  }

  const words = vocabData.words ?? [];
  const phrases = vocabData.phrases ?? [];
  const patterns = vocabData.patterns ?? [];

  normalizeImportanceScores(words, phrases);

  const total = words.length + phrases.length + patterns.length;

  onProgress?.({
    phase: "storing",
    current: 0,
    total,
    message: `正在儲存詞彙資料 (0 / ${total})...`,
  });

  await clearAllStores();

  let processed = 0;

  await bulkInsertWords(words, (current, wordsTotal) => {
    processed = current;
    onProgress?.({
      phase: "storing",
      current: processed,
      total,
      message: `正在儲存單字資料 (${current} / ${wordsTotal})...`,
    });
  });

  processed = words.length;

  if (phrases.length > 0) {
    onProgress?.({
      phase: "storing",
      current: processed,
      total,
      message: `正在儲存片語資料...`,
    });
    await bulkInsertPhrases(phrases);
    processed += phrases.length;
  }

  if (patterns.length > 0) {
    onProgress?.({
      phase: "storing",
      current: processed,
      total,
      message: `正在儲存句型資料...`,
    });
    await bulkInsertPatterns(patterns);
    processed += patterns.length;
  }

  await setStoredVersion(
    resolvedVersionInfo.generated_at ?? resolvedVersionInfo.version,
  );
  await setStoredVersionInfo(resolvedVersionInfo);
  await setStoredMetadata({
    ...vocabData.metadata,
    vocab_hash: resolvedVersionInfo.vocab_hash,
  });

  onProgress?.({
    phase: "ready",
    current: total,
    total,
    message: "載入完成",
  });
}

export async function loadVocabWithVersionCheck(
  onProgress?: (progress: LoadProgress) => void,
): Promise<{ downloaded: boolean; isOffline: boolean }> {
  onProgress?.({
    phase: "checking",
    current: 0,
    total: 100,
    message: "正在檢查更新...",
  });

  const { needsUpdate, remoteVersion, isOffline, hasLocalData } = await checkForUpdate();

  if (isOffline) {
    if (hasLocalData) {
      onProgress?.({
        phase: "ready",
        current: 100,
        total: 100,
        message: "離線模式：使用本機資料",
      });
      return { downloaded: false, isOffline: true };
    }
    throw new Error("無法載入資料：沒有網路連線且沒有本機快取");
  }

  if (needsUpdate && remoteVersion) {
    await downloadAndStoreVocab(onProgress, remoteVersion);
    return { downloaded: true, isOffline: false };
  }

  onProgress?.({
    phase: "ready",
    current: 100,
    total: 100,
    message: "載入完成",
  });

  return { downloaded: false, isOffline: false };
}

function normalizeImportanceScores(
  words: WordEntry[],
  phrases: PhraseEntry[],
): void {
  const allScores: number[] = [];

  for (const word of words) {
    if (word.frequency?.ml_score != null) {
      allScores.push(word.frequency.ml_score);
    }
  }
  for (const phrase of phrases) {
    if (phrase.frequency?.ml_score != null) {
      allScores.push(phrase.frequency.ml_score);
    }
  }

  if (allScores.length === 0) {
    for (const word of words) {
      if (word.frequency) {
        word.frequency.importance_score = Math.min(
          word.frequency.total_appearances / 100,
          1,
        );
      }
    }
    for (const phrase of phrases) {
      if (phrase.frequency) {
        phrase.frequency.importance_score = Math.min(
          phrase.frequency.total_appearances / 100,
          1,
        );
      }
    }
    return;
  }

  const sortedScores = [...allScores].sort((a, b) => a - b);
  const n = sortedScores.length;

  const scoreToPercentile = new Map<number, number>();
  for (let i = 0; i < n; i++) {
    const score = sortedScores[i];
    if (!scoreToPercentile.has(score)) {
      let j = i;
      while (j < n && sortedScores[j] === score) j++;
      const avgRank = (i + j - 1) / 2;
      scoreToPercentile.set(score, n > 1 ? avgRank / (n - 1) : 0.5);
    }
  }

  for (const word of words) {
    if (word.frequency) {
      word.frequency.importance_score =
        word.frequency.ml_score != null
          ? (scoreToPercentile.get(word.frequency.ml_score) ?? 0)
          : Math.min(word.frequency.total_appearances / 100, 1);
    }
  }

  for (const phrase of phrases) {
    if (phrase.frequency) {
      phrase.frequency.importance_score =
        phrase.frequency.ml_score != null
          ? (scoreToPercentile.get(phrase.frequency.ml_score) ?? 0)
          : Math.min(phrase.frequency.total_appearances / 100, 1);
    }
  }
}
