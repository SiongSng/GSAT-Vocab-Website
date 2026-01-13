import { browser } from '$app/environment';
import { safeGetItem, safeSetItem } from '$lib/utils/safe-storage';

export type TTSEngine = "prebuilt" | "edge-tts" | "kokoro";

export type KokoroModelStatus =
  | "not-downloaded"
  | "downloading"
  | "ready"
  | "error";

export interface KokoroState {
  status: KokoroModelStatus;
  downloadProgress: number;
  error: string | null;
}

interface TTSSettingsStore {
  engine: TTSEngine;
  kokoro: KokoroState;
}

const STORAGE_KEY = "tts-settings";

function getDefaultState(): TTSSettingsStore {
  return {
    engine: "prebuilt",
    kokoro: {
      status: "not-downloaded",
      downloadProgress: 0,
      error: null,
    },
  };
}

function loadFromStorage(): TTSSettingsStore {
  if (!browser) return getDefaultState();
  try {
    const stored = safeGetItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        engine:
          parsed.engine === "kokoro" || parsed.engine === "edge-tts" || parsed.engine === "prebuilt"
            ? parsed.engine
            : "prebuilt",
        kokoro: {
          status:
            parsed.kokoro?.status === "ready" ? "ready" : "not-downloaded",
          downloadProgress: 0,
          error: null,
        },
      };
    }
  } catch {
    // ignore
  }
  return getDefaultState();
}

function saveToStorage(store: TTSSettingsStore): void {
  if (!browser) return;
  try {
    safeSetItem(
      STORAGE_KEY,
      JSON.stringify({
        engine: store.engine,
        kokoro: { status: store.kokoro.status },
      }),
    );
  } catch {
    // ignore
  }
}

const store: TTSSettingsStore = $state(getDefaultState());
let initialized = false;

export function initTTSSettings(): void {
  if (!browser || initialized) return;
  initialized = true;
  const loaded = loadFromStorage();
  store.engine = loaded.engine;
  store.kokoro = loaded.kokoro;
}

export function getTTSSettingsStore() {
  return {
    get engine() {
      return store.engine;
    },
    get kokoro() {
      return store.kokoro;
    },
  };
}

export function setEngine(engine: TTSEngine): void {
  store.engine = engine;
  saveToStorage(store);
}

export function setKokoroStatus(status: KokoroModelStatus): void {
  store.kokoro.status = status;
  if (status === "not-downloaded") {
    saveToStorage(store);
  }
}

export function setKokoroDownloadProgress(progress: number): void {
  store.kokoro.downloadProgress = progress;
}

export function setKokoroError(error: string | null): void {
  store.kokoro.error = error;
  store.kokoro.status = "error";
}

export function isKokoroAvailable(): boolean {
  return store.kokoro.status === "ready";
}
