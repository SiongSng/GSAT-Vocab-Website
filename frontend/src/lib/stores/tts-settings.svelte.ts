export type TTSEngine = "edge-tts" | "kokoro";

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

function loadFromStorage(): TTSSettingsStore {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        engine: parsed.engine ?? "edge-tts",
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
  return {
    engine: "edge-tts",
    kokoro: {
      status: "not-downloaded",
      downloadProgress: 0,
      error: null,
    },
  };
}

function saveToStorage(store: TTSSettingsStore): void {
  try {
    localStorage.setItem(
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

const store: TTSSettingsStore = $state(loadFromStorage());

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
