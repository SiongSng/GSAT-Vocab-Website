import { auth, googleProvider, authReady } from "$lib/firebase";
import {
  onAuthStateChanged,
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
    } catch (error: any) {
      console.error("Redirect sign-in error:", error);
      state.loginError = error?.message || "登入失敗";
    }
  })();

  return initPromise;
}

// Initialize auth listener
onAuthStateChanged(auth, (user) => {
  state.user = user;
  state.loading = false;
  state.initialized = true;
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

    async login() {
      state.loading = true;
      state.loginError = null;
      try {
        await authReady;
        await signInWithRedirect(auth, googleProvider);
      } catch (error: any) {
        const code = error?.code || "";
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
