import type { ViewMode } from "$lib/types";

interface AppStore {
  mode: ViewMode;
  isSidebarOpen: boolean;
  isGridMode: boolean;
  isMobile: boolean;
  isMobileDetailOpen: boolean;
}

const store: AppStore = $state({
  mode: "browse",
  isSidebarOpen: false,
  isGridMode: false,
  isMobile: false,
  isMobileDetailOpen: false,
});

export function getAppStore() {
  return {
    get mode() {
      return store.mode;
    },
    get isSidebarOpen() {
      return store.isSidebarOpen;
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
  store.mode = mode;
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

export function toggleGridMode(): void {
  store.isGridMode = !store.isGridMode;
}

export function setMobile(isMobile: boolean): void {
  store.isMobile = isMobile;
  if (!isMobile) {
    store.isSidebarOpen = false;
    store.isMobileDetailOpen = false;
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
