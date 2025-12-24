import type { ViewMode } from "$lib/types";
import { getRouterStore, navigate } from "./router.svelte";

interface AppStore {
  isSidebarOpen: boolean;
  isFilterCollapsed: boolean;
  isGridMode: boolean;
  isMobile: boolean | null;
  isMobileDetailOpen: boolean;
}

const store: AppStore = $state({
  isSidebarOpen: false,
  isFilterCollapsed: false,
  isGridMode: false,
  isMobile: null,
  isMobileDetailOpen: false,
});

function deriveMode(): ViewMode {
  const router = getRouterStore();
  const routeName = router.route.name;

  if (routeName === "browse" || routeName === "word") {
    return "browse";
  }
  if (routeName === "flashcard" || routeName === "flashcard-session") {
    return "flashcard";
  }
  if (routeName === "quiz" || routeName === "quiz-session") {
    return "quiz";
  }
  if (routeName === "stats") {
    return "stats";
  }
  return "browse";
}

export function getAppStore() {
  return {
    get mode() {
      return deriveMode();
    },
    get isSidebarOpen() {
      return store.isSidebarOpen;
    },
    get isFilterCollapsed() {
      return store.isFilterCollapsed;
    },
    get isGridMode() {
      return store.isGridMode;
    },
    get isMobile() {
      return store.isMobile;
    },
    get isMobileDetailOpen() {
      return store.isMobileDetailOpen;
    },
  };
}

export function setMode(mode: ViewMode): void {
  switch (mode) {
    case "browse":
      navigate({ name: "browse" });
      break;
    case "flashcard":
      navigate({ name: "flashcard" });
      break;
    case "quiz":
      navigate({ name: "quiz" });
      break;
  }
  if (mode !== "browse") {
    store.isMobileDetailOpen = false;
  }
}

export function toggleSidebar(): void {
  store.isSidebarOpen = !store.isSidebarOpen;
}

export function closeSidebar(): void {
  store.isSidebarOpen = false;
}

export function toggleFilterCollapsed(): void {
  store.isFilterCollapsed = !store.isFilterCollapsed;
}

export function setFilterCollapsed(collapsed: boolean): void {
  store.isFilterCollapsed = collapsed;
}

export function toggleGridMode(): void {
  store.isGridMode = !store.isGridMode;
}

export function setMobile(isMobile: boolean): void {
  store.isMobile = isMobile;
  if (!isMobile) {
    store.isSidebarOpen = false;
    store.isMobileDetailOpen = false;
  } else {
    const router = getRouterStore();
    if (router.route.name === "word") {
      store.isMobileDetailOpen = true;
    }
  }
}

export function openMobileDetail(): void {
  if (store.isMobile) {
    store.isMobileDetailOpen = true;
  }
}

export function closeMobileDetail(): void {
  store.isMobileDetailOpen = false;
}
