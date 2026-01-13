import { EdgeTTS } from "edge-tts-universal/browser";
import {
  getTTSSettingsStore,
  isKokoroAvailable,
} from "./stores/tts-settings.svelte";
import { synthesizeWithKokoro } from "./kokoro-tts";

const VOICE = "en-US-JennyNeural";
const PARALLEL_ATTEMPTS = 3;
const STAGGER_DELAY_MS = 100;

function getSynthesisTimeout(): number {
  const nav = navigator as Navigator & {
    connection?: {
      effectiveType?: string;
      saveData?: boolean;
    };
  };

  const conn = nav.connection;
  if (!conn) return 5000;

  if (conn.saveData) return 10000;

  switch (conn.effectiveType) {
    case "slow-2g":
    case "2g":
      return 10000;
    case "3g":
      return 6000;
    case "4g":
      return 1500;
    default:
      return 2500;
  }
}

const audioCache = new Map<string, string>();
const pendingRequests = new Map<string, Promise<string>>();

const HF_TTS_DATASET_REPO = "TCabbage/gsat-vocab-sentences-tts";
const HF_TTS_AUDIO_BASE_URL = `https://huggingface.co/datasets/${HF_TTS_DATASET_REPO}/resolve/main/audio`;
const HF_TTS_CHECK_TIMEOUT_MS = 1500;

const ttsHashCache = new Map<string, string>();
const hfAvailabilityCache = new Map<string, boolean>();

function normalizeTTSText(text: string): string {
  return text.normalize("NFKC").replace(/\s+/g, " ").trim();
}

async function sha256Hex(text: string): Promise<string> {
  const normalized = normalizeTTSText(text);
  const cached = ttsHashCache.get(normalized);
  if (cached) return cached;

  const data = new TextEncoder().encode(normalized);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const bytes = new Uint8Array(digest);
  const hash = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  ttsHashCache.set(normalized, hash);
  return hash;
}

async function getHFAudioUrlIfExists(text: string): Promise<string | null> {
  const normalized = normalizeTTSText(text);
  if (!normalized) return null;

  const hash = await sha256Hex(normalized);
  const known = hfAvailabilityCache.get(hash);
  if (known === false) return null;

  const url = `${HF_TTS_AUDIO_BASE_URL}/${hash.slice(0, 2)}/${hash}.mp3`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), HF_TTS_CHECK_TIMEOUT_MS);

  try {
    const res = await fetch(url, {
      method: "GET",
      headers: { Range: "bytes=0-0" },
      signal: controller.signal,
    });
    if (!res.ok) {
      hfAvailabilityCache.set(hash, false);
      return null;
    }
    hfAvailabilityCache.set(hash, true);
    return url;
  } catch {
    return url;
  } finally {
    clearTimeout(timeoutId);
  }
}

export type AudioState = "idle" | "loading" | "playing" | "error";

let globalAudio: HTMLAudioElement | null = null;
let currentController: AudioController | null = null;
let currentPlayingText: string | null = null;
let globalStateSubscribers: Set<
  (text: string | null, state: AudioState) => void
> = new Set();

function notifyGlobalState(text: string | null, state: AudioState) {
  currentPlayingText = text;
  for (const cb of globalStateSubscribers) {
    cb(text, state);
  }
}

export function subscribeToGlobalAudioState(
  callback: (text: string | null, state: AudioState) => void,
): () => void {
  globalStateSubscribers.add(callback);
  callback(currentPlayingText, currentController?.getState() ?? "idle");
  return () => {
    globalStateSubscribers.delete(callback);
  };
}

function getGlobalAudio(): HTMLAudioElement {
  if (!globalAudio) {
    globalAudio = new Audio();
  }
  return globalAudio;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function withTimeout<T>(
  promise: Promise<T>,
  ms: number,
  message: string,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(message));
    }, ms);

    promise
      .then((result) => {
        clearTimeout(timer);
        resolve(result);
      })
      .catch((err) => {
        clearTimeout(timer);
        reject(err);
      });
  });
}

async function synthesizeWithEdgeTTS(text: string): Promise<Blob> {
  const timeout = getSynthesisTimeout();

  let result;
  try {
    const tts = new EdgeTTS(text, VOICE);
    result = await withTimeout(
      tts.synthesize(),
      timeout,
      `TTS synthesis timeout after ${timeout}ms`,
    );
  } catch (err) {
    throw err instanceof Error ? err : new Error(String(err));
  }

  if (!result.audio || result.audio.size === 0) {
    throw new Error("Empty audio response");
  }

  return result.audio;
}

function shouldUseKokoro(): boolean {
  const settings = getTTSSettingsStore();
  return settings.engine === "kokoro" && isKokoroAvailable();
}


async function synthesizeOnce(text: string): Promise<Blob> {
  if (shouldUseKokoro()) {
    return synthesizeWithKokoro(text);
  }
  return synthesizeWithEdgeTTS(text);
}

function jitteredDelay(baseMs: number, jitterRatio: number = 0.5): number {
  const jitter = baseMs * jitterRatio * (Math.random() * 2 - 1);
  return Math.max(0, baseMs + jitter);
}

async function synthesizeWithRace(
  text: string,
  options: { allowRemote: boolean },
): Promise<string> {
  if (shouldUseKokoro()) {
    const audioBlob = await synthesizeOnce(text);
    return URL.createObjectURL(audioBlob);
  }

  if (options.allowRemote) {
    const hfUrl = await getHFAudioUrlIfExists(text);
    if (hfUrl) {
      return hfUrl;
    }
  }

  const errors: Error[] = [];
  let resolved = false;

  const raceAttempt = async (index: number): Promise<Blob> => {
    if (index > 0) {
      await sleep(STAGGER_DELAY_MS * index);
    }
    if (resolved) {
      throw new Error("Already resolved");
    }
    return synthesizeOnce(text);
  };

  const attempts = Array.from({ length: PARALLEL_ATTEMPTS }, (_, i) =>
    raceAttempt(i).catch((err) => {
      errors.push(err instanceof Error ? err : new Error(String(err)));
      throw err;
    }),
  );

  try {
    const audioBlob = await Promise.any(attempts);
    resolved = true;
    return URL.createObjectURL(audioBlob);
  } catch {
    throw errors[0] || new Error("TTS synthesis failed");
  }
}

async function speakTextInternal(
  text: string,
  options: { allowRemote?: boolean; bypassCache?: boolean } = {},
): Promise<string> {
  const engine = getTTSSettingsStore().engine;
  const allowRemote =
    options.allowRemote ?? (engine === "prebuilt" ? true : false);

  if (!options.bypassCache) {
    const cached = audioCache.get(text);
    if (cached) {
      return cached;
    }

    const pending = pendingRequests.get(text);
    if (pending) {
      return pending;
    }
  }

  const request = synthesizeWithRace(text, { allowRemote })
    .then((url) => {
      audioCache.set(text, url);
      pendingRequests.delete(text);
      return url;
    })
    .catch((err) => {
      pendingRequests.delete(text);
      throw err;
    });

  if (!options.bypassCache) {
    pendingRequests.set(text, request);
  }
  return request;
}

export async function speakText(text: string): Promise<string> {
  return speakTextInternal(text);
}

const PRELOAD_RETRY_DELAY_MS = 3000;
const failedPreloads = new Set<string>();

export async function preloadAudio(texts: string[]): Promise<void> {
  if (texts.length === 0) return;

  const toPreload = texts.filter(
    (t) => !audioCache.has(t) && !pendingRequests.has(t),
  );
  if (toPreload.length === 0) return;

  const results = await Promise.allSettled(
    toPreload.map((text) => speakText(text)),
  );

  const failed: string[] = [];
  for (let i = 0; i < results.length; i++) {
    if (results[i].status === "rejected") {
      failed.push(toPreload[i]);
    }
  }

  if (failed.length > 0) {
    const retryTargets = failed.filter((t) => !failedPreloads.has(t));
    for (const t of failed) {
      failedPreloads.add(t);
    }

    if (retryTargets.length > 0) {
      setTimeout(
        () => {
          for (const t of retryTargets) {
            failedPreloads.delete(t);
          }
          preloadAudio(retryTargets);
        },
        jitteredDelay(PRELOAD_RETRY_DELAY_MS, 0.3),
      );
    }
  }
}

export function isAudioCached(text: string): boolean {
  return audioCache.has(text);
}

export function clearAudioCache(): void {
  for (const url of audioCache.values()) {
    if (url.startsWith("blob:")) {
      URL.revokeObjectURL(url);
    }
  }
  audioCache.clear();
}

export interface AudioController {
  play: () => Promise<void>;
  stop: () => void;
  getState: () => AudioState;
  subscribe: (callback: (state: AudioState) => void) => () => void;
}

export function createAudioController(getText: () => string): AudioController {
  let state: AudioState = "idle";
  let subscribers: Set<(state: AudioState) => void> = new Set();
  let aborted = false;
  let currentText: string | null = null;

  function setState(newState: AudioState) {
    state = newState;
    for (const cb of subscribers) {
      cb(newState);
    }
    if (currentController === controller) {
      notifyGlobalState(currentText, newState);
    }
  }

  const controller: AudioController = {
    async play() {
      if (state === "loading" || state === "playing") return;

      if (currentController && currentController !== controller) {
        currentController.stop();
      }
      currentController = controller;

      aborted = false;
      currentText = getText();
      setState("loading");

      let url: string;
      try {
        url = await speakText(currentText);
      } catch (err) {
        console.error("[TTS] Synthesis failed:", err);
        if (!aborted) {
          setState("error");
          currentController = null;
          setTimeout(() => {
            if (state === "error") setState("idle");
          }, 2000);
        }
        return;
      }

      if (aborted) {
        setState("idle");
        return;
      }

      const audio = getGlobalAudio();

      let attemptedRemoteFallback = false;

      audio.onended = null;
      audio.onerror = null;
      audio.pause();

      audio.src = url;

      audio.onended = () => {
        if (currentController === controller) {
          setState("idle");
          currentController = null;
        }
      };

      audio.onerror = () => {
        if (
          currentController === controller &&
          !aborted &&
          !attemptedRemoteFallback &&
          url.startsWith(HF_TTS_AUDIO_BASE_URL)
        ) {
          attemptedRemoteFallback = true;
          const textForRetry = currentText;
          if (!textForRetry) return;

          void (async () => {
            setState("loading");
            audioCache.delete(textForRetry);
            try {
              const fallbackUrl = await speakTextInternal(textForRetry, {
                allowRemote: false,
                bypassCache: true,
              });
              if (aborted || currentController !== controller) return;
              audio.onended = null;
              audio.onerror = null;
              audio.pause();
              audio.src = fallbackUrl;
              audio.onended = () => {
                if (currentController === controller) {
                  setState("idle");
                  currentController = null;
                }
              };
              audio.onerror = () => {
                if (currentController === controller) {
                  setState("error");
                  currentController = null;
                  setTimeout(() => {
                    if (state === "error") setState("idle");
                  }, 2000);
                }
              };

              await audio.play();
              if (!aborted && currentController === controller) {
                setState("playing");
              }
            } catch {
              if (currentController === controller) {
                setState("error");
                currentController = null;
                setTimeout(() => {
                  if (state === "error") setState("idle");
                }, 2000);
              }
            }
          })();
          return;
        }

        if (currentController === controller) {
          setState("error");
          currentController = null;
          setTimeout(() => {
            if (state === "error") setState("idle");
          }, 2000);
        }
      };

      try {
        await audio.play();
        if (!aborted) {
          setState("playing");
        }
      } catch (err) {
        console.error("[TTS] Audio play failed:", err);
        if (!aborted) {
          setState("error");
          currentController = null;
          setTimeout(() => {
            if (state === "error") setState("idle");
          }, 2000);
        }
      }
    },

    stop() {
      aborted = true;
      const wasCurrentController = currentController === controller;
      if (wasCurrentController) {
        const audio = getGlobalAudio();
        audio.pause();
        audio.onended = null;
        audio.onerror = null;
        currentController = null;
        notifyGlobalState(null, "idle");
      }
      setState("idle");
    },

    getState() {
      return state;
    },

    subscribe(callback: (state: AudioState) => void) {
      subscribers.add(callback);
      callback(state);
      return () => {
        subscribers.delete(callback);
      };
    },
  };

  return controller;
}

export function stopAllAudio(): void {
  if (currentController) {
    currentController.stop();
  }
}
