import type { VocabDatabase, VersionInfo } from "$lib/types/vocab";
import {
  getStoredVersion,
  setStoredVersion,
  getStoredMetadata,
  setStoredMetadata,
  clearAllStores,
  bulkInsertEntries,
  bulkInsertDistractorGroups,
  getEntriesCount,
} from "./vocab-db";

const VERSION_URL = `${import.meta.env.BASE_URL}data/version.json`;
const VOCAB_URL = `${import.meta.env.BASE_URL}data/vocab.json.gz`;

export interface LoadProgress {
  phase: "checking" | "downloading" | "decompressing" | "storing" | "ready";
  current: number;
  total: number;
  message: string;
}

export async function fetchVersionInfo(): Promise<VersionInfo> {
  const response = await fetch(VERSION_URL, { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`Failed to fetch version info: ${response.status}`);
  }
  return response.json();
}

export async function checkForUpdate(): Promise<{
  needsUpdate: boolean;
  remoteVersion: VersionInfo;
}> {
  const remoteVersion = await fetchVersionInfo();
  const localVersion = await getStoredVersion();
  const localMetadata = await getStoredMetadata();

  const needsUpdate =
    !localVersion ||
    localVersion !== remoteVersion.version ||
    (remoteVersion.vocab_hash && localMetadata?.vocab_hash !== remoteVersion.vocab_hash) ||
    (await getEntriesCount()) === 0;

  return { needsUpdate, remoteVersion };
}

async function decompressGzipStream(
  response: Response
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
  response: Response
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
  onProgress?: (progress: LoadProgress) => void
): Promise<void> {
  onProgress?.({
    phase: "downloading",
    current: 0,
    total: 100,
    message: "正在下載詞彙資料...",
  });

  const response = await fetch(VOCAB_URL);
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
  try {
    const clonedResponse = response.clone();
    vocabData = await decompressGzipStream(clonedResponse);
  } catch {
    vocabData = await decompressGzipFallback(response);
  }

  const entries = vocabData.entries;
  const distractorGroups = vocabData.distractor_groups ?? [];
  const total = entries.length;
  const distractorTotal = distractorGroups.length;

  onProgress?.({
    phase: "storing",
    current: 0,
    total,
    message: `正在儲存詞彙資料 (0 / ${total})...`,
  });

  await clearAllStores();

  await bulkInsertEntries(entries, (current, entriesTotal) => {
    onProgress?.({
      phase: "storing",
      current,
      total: entriesTotal,
      message: `正在儲存詞彙資料 (${current} / ${entriesTotal})...`,
    });
  });

  if (distractorGroups.length > 0) {
    onProgress?.({
      phase: "storing",
      current: 0,
      total: distractorTotal,
      message: `正在儲存考古題資料 (0 / ${distractorTotal})...`,
    });

    await bulkInsertDistractorGroups(distractorGroups);
  }

  await setStoredVersion(vocabData.version);
  await setStoredMetadata(vocabData.metadata);

  onProgress?.({
    phase: "ready",
    current: total,
    total,
    message: "載入完成",
  });
}

export async function loadVocabWithVersionCheck(
  onProgress?: (progress: LoadProgress) => void
): Promise<boolean> {
  onProgress?.({
    phase: "checking",
    current: 0,
    total: 100,
    message: "正在檢查更新...",
  });

  const { needsUpdate } = await checkForUpdate();

  if (needsUpdate) {
    await downloadAndStoreVocab(onProgress);
    return true;
  }

  onProgress?.({
    phase: "ready",
    current: 100,
    total: 100,
    message: "載入完成",
  });

  return false;
}
