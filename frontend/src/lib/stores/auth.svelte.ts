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

// Detect in-app browsers that don't support popup well
// Note: Electron is NOT included here - redirect doesn't work in Electron either
// For Electron, popup is preferred as it can be configured to work
function isInAppBrowser(): boolean {
  const ua = navigator.userAgent || "";
  // LINE, Facebook, Instagram, WeChat, etc.
  return /Line|FBAN|FBAV|Instagram|MicroMessenger|WebView/i.test(ua);
}

function shouldUseRedirect(): boolean {
  return isInAppBrowser();
}

function isElectron(): boolean {
  const ua = navigator.userAgent || "";
  return /Electron/i.test(ua);
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
    get isElectron() {
      return isElectron();
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
        // Popup blocked: fallback to redirect (but not in Electron)
        if (code === "auth/popup-blocked") {
          if (isElectron()) {
            state.loginError =
              "無法開啟登入視窗。請在一般瀏覽器中開啟此網站進行登入。";
            state.loading = false;
            return;
          }
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
