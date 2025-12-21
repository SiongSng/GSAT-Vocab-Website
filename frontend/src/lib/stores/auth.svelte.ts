import { auth, googleProvider, authReady } from "$lib/firebase";
import {
  onAuthStateChanged,
  signInWithPopup,
  signInWithCredential,
  GoogleAuthProvider,
  signOut,
  type User,
} from "firebase/auth";

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
  loginError: string | null;
  loginErrorCode: string | null;
}

const state = $state<AuthState>({
  user: null,
  loading: true,
  initialized: false,
  loginError: null,
  loginErrorCode: null,
});

void authReady
  .catch(() => undefined)
  .finally(() => {
    onAuthStateChanged(auth, (user) => {
      state.user = user;
      state.loading = false;
      state.initialized = true;
    });
  });

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
    get loginErrorCode() {
      return state.loginErrorCode;
    },

    clearError() {
      state.loginError = null;
      state.loginErrorCode = null;
    },

    async login() {
      state.loading = true;
      state.loginError = null;
      state.loginErrorCode = null;
      try {
        await authReady;
        await signInWithPopup(auth, googleProvider);
      } catch (error: any) {
        const code = error?.code || "";
        state.loginErrorCode = code || null;
        if (code === "auth/popup-blocked") {
          state.loginError = "登入視窗被阻擋，請點擊「手動登入」。";
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
          state.loginError = "此環境無法完成登入，請點擊「手動登入」。";
          state.loading = false;
          return;
        }
        state.loginError = error?.message || "登入失敗，請點擊「手動登入」。";
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

    async loginWithToken(idToken: string) {
      state.loading = true;
      state.loginError = null;
      state.loginErrorCode = null;
      try {
        await authReady;
        const credential = GoogleAuthProvider.credential(idToken);
        await signInWithCredential(auth, credential);
      } catch (error: any) {
        const code = error?.code || "";
        state.loginErrorCode = code || null;
        if (
          code === "auth/invalid-credential" ||
          code === "auth/invalid-id-token"
        ) {
          state.loginError = "驗證碼無效或已過期，請重新取得。";
        } else {
          state.loginError = error?.message || "驗證失敗";
        }
        state.loading = false;
        throw error;
      }
      state.loading = false;
    },
  };
}
