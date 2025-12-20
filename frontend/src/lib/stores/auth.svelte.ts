import { auth, googleProvider } from "$lib/firebase";
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
}

const state = $state<AuthState>({
  user: null,
  loading: true,
  initialized: false,
});

// Handle redirect result on page load (for in-app browsers that can't use popup)
getRedirectResult(auth).catch((error) => {
  console.error("Redirect sign-in error:", error);
});

// Initialize auth listener
onAuthStateChanged(auth, (user) => {
  state.user = user;
  state.loading = false;
  state.initialized = true;
});

// Detect in-app browsers that don't support popup well
function shouldUseRedirect(): boolean {
  const ua = navigator.userAgent || "";
  // LINE, Facebook, Instagram, WeChat, etc.
  return /Line|FBAN|FBAV|Instagram|MicroMessenger|WebView/i.test(ua);
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

    async login() {
      state.loading = true;
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
