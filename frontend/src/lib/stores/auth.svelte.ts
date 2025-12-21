import { auth, googleProvider, authReady } from "$lib/firebase";
import {
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  signOut,
  type User,
} from "firebase/auth";

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
  loginError: string | null;
}

const state = $state<AuthState>({
  user: null,
  loading: true,
  initialized: false,
  loginError: null,
});

let initPromise: Promise<void> | null = null;

export async function initAuth(): Promise<void> {
  if (initPromise) return initPromise;

  initPromise = (async () => {
    await authReady;
    try {
      const result = await getRedirectResult(auth);
      if (result?.user) {
        state.user = result.user;
      }
      if (!state.user && auth.currentUser) {
        state.user = auth.currentUser;
      }
    } catch (error: any) {
      console.error("Redirect sign-in error:", error);
      state.loginError = error?.message || "登入失敗";
    }
  })();

  return initPromise;
}

void authReady
  .catch(() => undefined)
  .finally(() => {
    onAuthStateChanged(auth, (user) => {
      state.user = user;
      state.loading = false;
      state.initialized = true;
    });
  });

void initAuth();

export function getAuthStore() {
  return {
    get user() {
      return state.user;
    },
    get loading() {
      return state.loading;
    },
    get initialized() {
      return state.initialized;
    },
    get loginError() {
      return state.loginError;
    },

    clearError() {
      state.loginError = null;
    },

    async login(options?: { method?: "popup" | "redirect" }) {
      state.loading = true;
      state.loginError = null;
      try {
        await authReady;
        const method = options?.method ?? "redirect";
        if (method === "redirect") {
          await signInWithRedirect(auth, googleProvider);
        } else {
          await signInWithPopup(auth, googleProvider);
        }
      } catch (error: any) {
        const code = error?.code || "";
        if (code === "auth/popup-blocked") {
          state.loginError = "登入視窗被阻擋（請允許彈出視窗，或改用導向登入）。";
          state.loading = false;
          return;
        }
        if (
          code === "auth/popup-closed-by-user" ||
          code === "auth/cancelled-popup-request"
        ) {
          state.loading = false;
          return;
        }
        if (
          code === "auth/operation-not-supported-in-this-environment" ||
          code === "auth/web-storage-unsupported"
        ) {
          state.loginError =
            "此環境無法完成 Google 登入（可能是 WebView 限制了必要的儲存/導向流程）。";
          state.loading = false;
          return;
        }
        state.loginError = error?.message || "登入失敗";
        state.loading = false;
        throw error;
      }
      state.loading = false;
    },

    async logout() {
      state.loading = true;
      try {
        await signOut(auth);
      } catch (error) {
        console.error("Logout failed:", error);
        throw error;
      } finally {
        state.loading = false;
      }
    },
  };
}
