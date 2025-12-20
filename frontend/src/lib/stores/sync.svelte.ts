import { db } from "$lib/firebase";
import { doc, getDoc, setDoc } from "firebase/firestore";
import { getAuthStore } from "./auth.svelte";
import {
  getAllCards,
  setAllCards,
  getLastUpdated,
  setLastUpdated,
} from "./srs-storage";
import type { SRSCard } from "$lib/types/srs";

interface SyncState {
  status: "idle" | "syncing" | "success" | "error" | "conflict";
  lastSyncError: string | null;
  lastSyncTime: number;
}

const STORAGE_KEY = "gsat_last_sync_time";

const state = $state<SyncState>({
  status: "idle",
  lastSyncError: null,
  lastSyncTime: Number(localStorage.getItem(STORAGE_KEY)) || 0,
});

const auth = getAuthStore();
const SYNC_COOLDOWN_MS = 30000; // 30 seconds cooldown

function updateLastSyncTime(ts: number) {
  state.lastSyncTime = ts;
  localStorage.setItem(STORAGE_KEY, String(ts));
}

function compressCard(card: SRSCard) {
  // NOTE: `elapsed_days` is deprecated in ts-fsrs v6 and will be removed in the future.
  // To minimize payload and avoid future incompatibilities we do NOT include it in the cloud payload.
  return {
    lm: card.lemma,
    sid: card.sense_id,
    du:
      card.due instanceof Date
        ? card.due.getTime()
        : new Date(card.due).getTime(),
    s: card.stability,
    d: card.difficulty,
    sc: card.scheduled_days,
    r: card.reps,
    l: card.lapses,
    st: card.state,
    ls: card.learning_steps,
    lr: card.last_review
      ? card.last_review instanceof Date
        ? card.last_review.getTime()
        : new Date(card.last_review).getTime()
      : null,
  };
}

function decompressCard(c: any): SRSCard {
  return {
    lemma: c.lm,
    sense_id: c.sid,
    due: new Date(c.du),
    stability: c.s,
    difficulty: c.d,
    // `elapsed_days` is deprecated; do NOT use cloud value. Default to 0.
    elapsed_days: 0,
    scheduled_days: c.sc,
    reps: c.r,
    lapses: c.l,
    state: c.st,
    learning_steps: c.ls || [],
    last_review: c.lr ? new Date(c.lr) : undefined,
  };
}

export function getSyncStore() {
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

      // Rate limiting: prevent sync if last sync was too recent
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
        const localCards = getAllCards();

        if (docSnap.exists()) {
          const cloudData = docSnap.data();
          const cloudLastUpdated = cloudData.last_updated || 0;

          if (cloudLastUpdated > localLastUpdated && !forceOverwriteLocal) {
            state.status = "conflict";
            return {
              conflict: true,
              cloudTime: cloudLastUpdated,
              localTime: localLastUpdated,
            };
          }

          if (cloudLastUpdated > localLastUpdated && forceOverwriteLocal) {
            // Overwrite local with cloud
            const cloudCards = (cloudData.cards || []).map(decompressCard);
            await setAllCards(cloudCards);
            await setLastUpdated(cloudLastUpdated);
            updateLastSyncTime(Date.now());
            state.status = "success";
            return { success: true };
          }
        }

        // Local is newer or cloud doesn't exist: Upload local to cloud
        const compressedCards = localCards.map(compressCard);
        const newTimestamp = Date.now();

        await setDoc(userDocRef, {
          cards: compressedCards,
          last_updated: newTimestamp,
        });

        await setLastUpdated(newTimestamp);
        updateLastSyncTime(Date.now());
        state.status = "success";
        return { success: true };
      } catch (error: any) {
        console.error("Sync failed:", error);
        // Friendly messages for common blocking issues
        const msg = String(error?.message || "");
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
