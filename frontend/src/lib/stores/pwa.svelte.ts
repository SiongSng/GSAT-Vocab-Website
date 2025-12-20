type BeforeInstallPromptEvent = Event & {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

interface PWAStore {
  canInstall: boolean;
  isIOS: boolean;
  isStandalone: boolean;
  showIOSGuide: boolean;
  showInstallBanner: boolean;
}

let deferredPrompt: BeforeInstallPromptEvent | null = null;

const store: PWAStore = $state({
  canInstall: false,
  isIOS: false,
  isStandalone: false,
  showIOSGuide: false,
  showInstallBanner: false,
});

function detectPlatform(): void {
  const ua = navigator.userAgent;
  const isIOSDevice = /iPad|iPhone|iPod/.test(ua) && !("MSStream" in window);
  const isIPadOS =
    navigator.platform === "MacIntel" &&
    navigator.maxTouchPoints > 1 &&
    !("MSStream" in window);
  store.isIOS = isIOSDevice || isIPadOS;
  store.isStandalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    ("standalone" in navigator &&
      (navigator as { standalone: boolean }).standalone);
}

function shouldShowBanner(): boolean {
  if (store.isStandalone) return false;

  const dismissCount = parseInt(
    localStorage.getItem("pwa-dismiss-count") || "0",
  );
  if (dismissCount >= 5) return false;

  const lastDismiss = localStorage.getItem("pwa-last-dismiss");
  if (lastDismiss) {
    const daysSinceLastDismiss =
      (Date.now() - parseInt(lastDismiss)) / (1000 * 60 * 60 * 24);
    const waitDays = Math.min(dismissCount * 2, 14);
    if (daysSinceLastDismiss < waitDays) return false;
  }

  return true;
}

export function initPWA(): void {
  detectPlatform();

  if (store.isStandalone) return;

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e as BeforeInstallPromptEvent;
    store.canInstall = true;

    if (shouldShowBanner()) {
      setTimeout(() => {
        store.showInstallBanner = true;
      }, 3000);
    }
  });

  window.addEventListener("appinstalled", () => {
    store.canInstall = false;
    store.showInstallBanner = false;
    store.showIOSGuide = false;
    deferredPrompt = null;
    localStorage.removeItem("pwa-dismiss-count");
    localStorage.removeItem("pwa-last-dismiss");
  });

  if (store.isIOS && shouldShowBanner()) {
    setTimeout(() => {
      store.showInstallBanner = true;
    }, 5000);
  }
}

export function getPWAStore() {
  return {
    get canInstall() {
      return store.canInstall;
    },
    get isIOS() {
      return store.isIOS;
    },
    get isStandalone() {
      return store.isStandalone;
    },
    get showIOSGuide() {
      return store.showIOSGuide;
    },
    get showInstallBanner() {
      return store.showInstallBanner;
    },
  };
}

export async function installPWA(): Promise<boolean> {
  if (!deferredPrompt) return false;

  await deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;

  if (outcome === "accepted") {
    store.canInstall = false;
    store.showInstallBanner = false;
  } else {
    recordDismiss();
  }

  deferredPrompt = null;
  return outcome === "accepted";
}

export function showIOSInstallGuide(): void {
  store.showIOSGuide = true;
}

export function hideIOSInstallGuide(): void {
  store.showIOSGuide = false;
}

function recordDismiss(): void {
  const dismissCount = parseInt(
    localStorage.getItem("pwa-dismiss-count") || "0",
  );
  localStorage.setItem("pwa-dismiss-count", (dismissCount + 1).toString());
  localStorage.setItem("pwa-last-dismiss", Date.now().toString());
}

export function dismissInstallBanner(): void {
  store.showInstallBanner = false;
  recordDismiss();
}
