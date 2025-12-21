import type { WorkerRequest, WorkerResponse } from "./kokoro-worker";
import {
  setKokoroStatus,
  setKokoroDownloadProgress,
  setKokoroError,
} from "./stores/tts-settings.svelte";

let worker: Worker | null = null;
let loadingPromise: Promise<Worker> | null = null;
let requestId = 0;
const pendingRequests = new Map<
  number,
  { resolve: (blob: Blob) => void; reject: (err: Error) => void }
>();

function handleWorkerMessage(e: MessageEvent<WorkerResponse>) {
  const data = e.data;

  switch (data.type) {
    case "device":
      break;
    case "progress":
      setKokoroDownloadProgress(data.progress);
      break;
    case "ready":
      setKokoroStatus("ready");
      setKokoroDownloadProgress(100);
      break;
    case "error":
      setKokoroError(data.error);
      break;
    case "result": {
      const pending = pendingRequests.get(data.id);
      if (pending) {
        pendingRequests.delete(data.id);
        pending.resolve(data.blob);
      }
      break;
    }
    case "synthesize-error": {
      const pending = pendingRequests.get(data.id);
      if (pending) {
        pendingRequests.delete(data.id);
        pending.reject(new Error(data.error));
      }
      break;
    }
  }
}

export function loadKokoroModel(): Promise<Worker> {
  if (worker) {
    return Promise.resolve(worker);
  }

  if (loadingPromise) {
    return loadingPromise;
  }

  loadingPromise = new Promise((resolve, reject) => {
    setKokoroStatus("downloading");
    setKokoroDownloadProgress(0);

    const w = new Worker(new URL("./kokoro-worker.ts", import.meta.url), {
      type: "module",
    });

    const onMessage = (e: MessageEvent<WorkerResponse>) => {
      handleWorkerMessage(e);

      if (e.data.type === "ready") {
        worker = w;
        resolve(w);
      } else if (e.data.type === "error") {
        loadingPromise = null;
        w.terminate();
        reject(new Error(e.data.error));
      }
    };

    w.addEventListener("message", onMessage);

    w.addEventListener("error", (err) => {
      setKokoroError(err.message || "Worker error");
      loadingPromise = null;
      w.terminate();
      reject(new Error(err.message || "Worker error"));
    });
  });

  return loadingPromise;
}

const SYNTHESIZE_TIMEOUT_MS = 30000;

export async function synthesizeWithKokoro(text: string): Promise<Blob> {
  const w = await loadKokoroModel();
  const id = ++requestId;

  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      const pending = pendingRequests.get(id);
      if (pending) {
        pendingRequests.delete(id);
        reject(
          new Error(
            `Kokoro synthesis timeout after ${SYNTHESIZE_TIMEOUT_MS}ms`,
          ),
        );
      }
    }, SYNTHESIZE_TIMEOUT_MS);

    pendingRequests.set(id, {
      resolve: (blob) => {
        clearTimeout(timeoutId);
        resolve(blob);
      },
      reject: (err) => {
        clearTimeout(timeoutId);
        reject(err);
      },
    });
    w.postMessage({ type: "synthesize", id, text } satisfies WorkerRequest);
  });
}

export function isKokoroLoaded(): boolean {
  return worker !== null;
}

export async function unloadKokoro(): Promise<void> {
  if (worker) {
    worker.terminate();
    worker = null;
  }
  loadingPromise = null;
  pendingRequests.clear();

  try {
    const cache = await caches.open("transformers-cache");
    const keys = await cache.keys();
    const kokoroKeys = keys.filter((req) => req.url.includes("Kokoro"));
    await Promise.all(kokoroKeys.map((key) => cache.delete(key)));
  } catch {
    // Cache API may not be available
  }

  setKokoroStatus("not-downloaded");
  setKokoroDownloadProgress(0);
}
