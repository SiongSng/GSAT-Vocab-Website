import { browser } from '$app/environment';
import { safeGetItem, safeSetItem } from '$lib/utils/safe-storage';
import { db } from "$lib/firebase";
import { doc, getDoc, setDoc } from "firebase/firestore";
import { getAuthStore } from "./auth.svelte";
import {
  exportDatabase,
  importDatabase,
  getLastUpdated,
  setLastUpdated,
  type DatabaseSnapshot,
} from "./srs-storage";
import { Packr } from "msgpackr";
import { zlibSync, unzlibSync } from "fflate";
import { STORAGE_KEYS } from "$lib/storage-keys";

const packr = new Packr({ structuredClone: true });

interface SyncState {
  status: "idle" | "syncing" | "success" | "error" | "conflict";
  lastSyncError: string | null;
  lastSyncTime: number;
}

const state = $state<SyncState>({
  status: "idle",
  lastSyncError: null,
  lastSyncTime: 0,
});

let initialized = false;

function initSyncState(): void {
  if (!browser || initialized) return;
  initialized = true;
  const saved = safeGetItem(STORAGE_KEYS.LAST_SYNC_TIME);
  state.lastSyncTime = saved ? Number(saved) : 0;
}

const auth = getAuthStore();
const SYNC_COOLDOWN_MS = 30000;

function updateLastSyncTime(ts: number) {
  state.lastSyncTime = ts;
  safeSetItem(STORAGE_KEYS.LAST_SYNC_TIME, String(ts));
}

interface SyncPayload {
  db: DatabaseSnapshot;
  decks: unknown[];
  settings: unknown | null;
  limits: unknown | null;
  ts: number;
}

function compress(data: SyncPayload): string {
  const packed = packr.pack(data);
  const compressed = zlibSync(packed, { level: 9 });
  let binary = "";
  for (let i = 0; i < compressed.length; i++) {
    binary += String.fromCharCode(compressed[i]);
  }
  return btoa(binary);
}

function decompress(base64: string): SyncPayload {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  const decompressed = unzlibSync(bytes);
  return packr.unpack(decompressed);
}

function getLocalDecks(): unknown[] {
  if (!browser) return [];
  try {
    const saved = safeGetItem(STORAGE_KEYS.CUSTOM_DECKS);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
}

function setLocalDecks(decks: unknown[]): void {
  if (!browser) return;
  safeSetItem(STORAGE_KEYS.CUSTOM_DECKS, JSON.stringify(decks));
}

function getLocalSettings(): unknown | null {
  if (!browser) return null;
  try {
    const saved = safeGetItem(STORAGE_KEYS.STUDY_SETTINGS);
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
}

function setLocalSettings(settings: unknown | null): void {
  if (!browser || !settings) return;
  safeSetItem(STORAGE_KEYS.STUDY_SETTINGS, JSON.stringify(settings));
}

function getLocalLimits(): unknown | null {
  if (!browser) return null;
  try {
    const saved = safeGetItem(STORAGE_KEYS.DAILY_LIMITS);
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
}

function setLocalLimits(limits: unknown | null): void {
  if (!browser || !limits) return;
  safeSetItem(STORAGE_KEYS.DAILY_LIMITS, JSON.stringify(limits));
}

export function getSyncStore() {
  initSyncState();
  return {
    get status() {
      return state.status;
    },
    get lastSyncError() {
      return state.lastSyncError;
    },
    get lastSyncTime() {
      return state.lastSyncTime;
    },

    async syncWithCloud(forceOverwriteLocal = false) {
      if (!auth.user) {
        state.lastSyncError = "使用者未登入";
        state.status = "error";
        return;
      }

      const now = Date.now();
      if (state.status === "syncing") return;
      if (!forceOverwriteLocal && now - state.lastSyncTime < SYNC_COOLDOWN_MS) {
        const remaining = Math.ceil(
          (SYNC_COOLDOWN_MS - (now - state.lastSyncTime)) / 1000,
        );
        state.lastSyncError = `同步過於頻繁，請稍候 ${remaining} 秒`;
        state.status = "error";
        return { rateLimited: true, remaining };
      }

      state.status = "syncing";
      state.lastSyncError = null;

      try {
        const userDocRef = doc(db, `users/${auth.user.uid}/sync/data`);
        const docSnap = await getDoc(userDocRef);

        const localLastUpdated = await getLastUpdated();

        if (docSnap.exists()) {
          const cloudData = docSnap.data();
          const cloudLastUpdated = cloudData.ts || 0;

          if (cloudLastUpdated > localLastUpdated && !forceOverwriteLocal) {
            state.status = "conflict";
            return {
              conflict: true,
              cloudTime: cloudLastUpdated,
              localTime: localLastUpdated,
            };
          }

          if (cloudLastUpdated > localLastUpdated && forceOverwriteLocal) {
            const payload = decompress(cloudData.d);
            await importDatabase(payload.db);
            if (payload.decks) {
              setLocalDecks(payload.decks);
            }
            if (payload.settings !== undefined) {
              setLocalSettings(payload.settings);
            }
            if (payload.limits !== undefined) {
              setLocalLimits(payload.limits);
            }
            await setLastUpdated(payload.ts);
            updateLastSyncTime(Date.now());
            state.status = "success";
            return { success: true };
          }
        }

        const snapshot = await exportDatabase();
        const newTimestamp = Date.now();
        const payload: SyncPayload = {
          db: snapshot,
          decks: getLocalDecks(),
          settings: getLocalSettings(),
          limits: getLocalLimits(),
          ts: newTimestamp,
        };
        const compressed = compress(payload);

        await setDoc(userDocRef, {
          d: compressed,
          ts: newTimestamp,
        });

        await setLastUpdated(newTimestamp);
        updateLastSyncTime(Date.now());
        state.status = "success";
        return { success: true };
      } catch (error: unknown) {
        console.error("Sync failed:", error);
        const msg = String((error as Error)?.message || "");
        if (
          /Cross-Origin-Opener-Policy|window\.close|window\.closed/i.test(
            msg,
          ) ||
          /ERR_BLOCKED_BY_CLIENT/i.test(msg)
        ) {
          state.lastSyncError =
            "無法連線到雲端：瀏覽器或擴充套件可能阻擋了 Firebase 請求（請關閉廣告封鎖器或允許 firestore.googleapis.com）。";
        } else {
          state.lastSyncError = msg || "同步失敗";
        }
        state.status = "error";
        throw error;
      }
    },
  };
}
