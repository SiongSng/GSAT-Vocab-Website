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

// Handle redirect result on page load after persistence is ready
authReady.then(() => {
  getRedirectResult(auth)
    .then((result) => {
      if (result?.user) {
        state.user = result.user;
      }
    })
    .catch((error) => {
      console.error("Redirect sign-in error:", error);
      state.loginError = error?.message || "登入失敗";
    });
});

// Initialize auth listener
onAuthStateChanged(auth, (user) => {
  state.user = user;
  state.loading = false;
  state.initialized = true;
});

// Detect environments that need redirect flow instead of popup
function isInAppBrowser(): boolean {
  const ua = navigator.userAgent || "";
  // LINE, Facebook, Instagram, WeChat, etc.
  return /Line|FBAN|FBAV|Instagram|MicroMessenger|WebView/i.test(ua);
}

function isElectron(): boolean {
  const ua = navigator.userAgent || "";
  // Check UA for Electron
  if (/Electron/i.test(ua)) return true;
  // Detect Electron webview: check for Electron-specific APIs or process object
  if (typeof window !== "undefined") {
    // Electron exposes process in renderer with nodeIntegration or via preload
    if ((window as any).process?.versions?.electron) return true;
    // Some Electron apps set this
    if ((window as any).electronAPI) return true;
  }
  return false;
}

function isEmbedded(): boolean {
  try {
    // Detect if running inside iframe or webview (window !== top)
    return window.self !== window.top;
  } catch {
    // Cross-origin iframe will throw, which means we're embedded
    return true;
  }
}

function shouldUseRedirect(): boolean {
  return isInAppBrowser() || isElectron() || isEmbedded();
}

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
        if (shouldUseRedirect()) {
          await signInWithRedirect(auth, googleProvider);
        } else {
          await signInWithPopup(auth, googleProvider);
        }
      } catch (error: any) {
        const code = error?.code || "";
        // Popup blocked: fallback to redirect
        if (code === "auth/popup-blocked") {
          await signInWithRedirect(auth, googleProvider);
          return;
        }
        // User closed popup: silently ignore
        if (
          code === "auth/popup-closed-by-user" ||
          code === "auth/cancelled-popup-request"
        ) {
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
