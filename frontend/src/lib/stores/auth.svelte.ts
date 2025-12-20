import { auth, googleProvider } from "$lib/firebase";
import { onAuthStateChanged, signInWithPopup, signInWithRedirect, signOut, type User } from "firebase/auth";

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
}

const state = $state<AuthState>({
  user: null,
  loading: true,
  initialized: false
});

// Initialize auth listener
onAuthStateChanged(auth, (user) => {
  state.user = user;
  state.loading = false;
  state.initialized = true;
});

export function getAuthStore() {
  return {
    get user() { return state.user; },
    get loading() { return state.loading; },
    get initialized() { return state.initialized; },
    
    async login() {
      state.loading = true;
      try {
        // Try popup first for a better UX; fall back to redirect when popup is blocked
        await signInWithPopup(auth, googleProvider);
      } catch (error: any) {
        console.warn("Popup sign-in failed, falling back to redirect:", error);
        try {
          await signInWithRedirect(auth, googleProvider);
        } catch (err) {
          console.error("Redirect sign-in failed:", err);
          throw err;
        }
      } finally {
        state.loading = false;
      }
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
    }
  };
}
