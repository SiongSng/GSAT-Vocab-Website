import { EdgeTTS } from "edge-tts-universal/browser";

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

async function synthesizeOnce(text: string): Promise<Blob> {
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

function jitteredDelay(baseMs: number, jitterRatio: number = 0.5): number {
  const jitter = baseMs * jitterRatio * (Math.random() * 2 - 1);
  return Math.max(0, baseMs + jitter);
}

async function synthesizeWithRace(text: string): Promise<string> {
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

export async function speakText(text: string): Promise<string> {
  const cached = audioCache.get(text);
  if (cached) {
    return cached;
  }

  const pending = pendingRequests.get(text);
  if (pending) {
    return pending;
  }

  const request = synthesizeWithRace(text)
    .then((url) => {
      audioCache.set(text, url);
      pendingRequests.delete(text);
      return url;
    })
    .catch((err) => {
      pendingRequests.delete(text);
      throw err;
    });

  pendingRequests.set(text, request);
  return request;
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
    URL.revokeObjectURL(url);
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
