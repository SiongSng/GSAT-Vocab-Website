import { STORAGE_KEYS } from "$lib/storage-keys";

export interface NotificationSettings {
  enabled: boolean;
  dailyReminderTime: string;
  streakWarningEnabled: boolean;
  dueCardReminderEnabled: boolean;
}

const DEFAULT_SETTINGS: NotificationSettings = {
  enabled: false,
  dailyReminderTime: "20:00",
  streakWarningEnabled: true,
  dueCardReminderEnabled: true,
};

interface NotificationStore {
  settings: NotificationSettings;
  permission: NotificationPermission | "unsupported";
  isSupported: boolean;
  serviceWorkerReady: boolean;
}

let store = $state<NotificationStore>({
  settings: { ...DEFAULT_SETTINGS },
  permission: "default",
  isSupported: false,
  serviceWorkerReady: false,
});

export function getNotificationStore(): NotificationStore {
  return store;
}

export async function initNotifications(): Promise<void> {
  loadSettings();

  store.isSupported = "Notification" in window && "serviceWorker" in navigator;
  if ("Notification" in window) {
    store.permission = Notification.permission;
  } else {
    store.permission = "unsupported";
  }

  if ("serviceWorker" in navigator) {
    try {
      const registration = await navigator.serviceWorker.ready;
      store.serviceWorkerReady = !!registration;
    } catch {
      store.serviceWorkerReady = false;
    }
  }

  if (store.settings.enabled && store.permission === "granted") {
    scheduleNotifications();
  }
}

function loadSettings(): void {
  try {
    const saved = localStorage.getItem(STORAGE_KEYS.NOTIFICATION_SETTINGS);
    if (saved) {
      const parsed = JSON.parse(saved);
      store.settings = { ...DEFAULT_SETTINGS, ...parsed };
    }
  } catch {
    store.settings = { ...DEFAULT_SETTINGS };
  }
}

function saveSettings(): void {
  try {
    localStorage.setItem(
      STORAGE_KEYS.NOTIFICATION_SETTINGS,
      JSON.stringify(store.settings),
    );
  } catch {
    // ignore
  }
}

export async function requestNotificationPermission(): Promise<boolean> {
  if (!store.isSupported) {
    return false;
  }

  if (Notification.permission === "granted") {
    store.permission = "granted";
    return true;
  }

  if (Notification.permission === "denied") {
    store.permission = "denied";
    return false;
  }

  const permission = await Notification.requestPermission();
  store.permission = permission;
  return permission === "granted";
}

export function updateNotificationSettings(
  updates: Partial<NotificationSettings>,
): void {
  store.settings = { ...store.settings, ...updates };
  saveSettings();

  if (store.settings.enabled && store.permission === "granted") {
    scheduleNotifications();
  } else {
    cancelAllNotifications();
  }
}

export async function toggleNotifications(enabled: boolean): Promise<boolean> {
  if (enabled) {
    const granted = await requestNotificationPermission();
    if (!granted) {
      return false;
    }
  }

  updateNotificationSettings({ enabled });
  return enabled;
}

let scheduledTimeoutId: ReturnType<typeof setTimeout> | null = null;

export function scheduleNotifications(): void {
  cancelAllNotifications();

  if (!store.settings.enabled || store.permission !== "granted") {
    return;
  }

  const [hours, minutes] = store.settings.dailyReminderTime
    .split(":")
    .map(Number);
  const now = new Date();
  const nextTime = new Date(now);
  nextTime.setHours(hours, minutes, 0, 0);

  if (nextTime <= now) {
    nextTime.setDate(nextTime.getDate() + 1);
  }

  const delay = nextTime.getTime() - now.getTime();

  localStorage.setItem(
    STORAGE_KEYS.NOTIFICATION_SCHEDULED,
    JSON.stringify({ nextTime: nextTime.toISOString() }),
  );

  scheduledTimeoutId = setTimeout(() => {
    showDailyReminder();
    scheduleNotifications();
  }, delay);
}

export function cancelAllNotifications(): void {
  if (scheduledTimeoutId) {
    clearTimeout(scheduledTimeoutId);
    scheduledTimeoutId = null;
  }
  localStorage.removeItem(STORAGE_KEYS.NOTIFICATION_SCHEDULED);
}

async function showNotificationViaServiceWorker(
  title: string,
  options: NotificationOptions,
): Promise<void> {
  if (!store.serviceWorkerReady) {
    new Notification(title, options);
    return;
  }

  try {
    const registration = await navigator.serviceWorker.ready;
    await registration.showNotification(title, options);
  } catch {
    new Notification(title, options);
  }
}

function showDailyReminder(): void {
  if (!store.isSupported || store.permission !== "granted") {
    return;
  }

  showNotificationViaServiceWorker("學測高頻單字", {
    body: "今天還沒學習喔！快來複習單字吧",
    icon: "/pwa-192x192.png",
    badge: "/pwa-192x192.png",
    tag: "daily-reminder",
    requireInteraction: false,
  });
}

export function showStreakWarning(streakCount: number): void {
  if (
    !store.isSupported ||
    store.permission !== "granted" ||
    !store.settings.streakWarningEnabled
  ) {
    return;
  }

  showNotificationViaServiceWorker("學測高頻單字", {
    body: `連續學習 ${streakCount} 天了！別讓紀錄中斷`,
    icon: "/pwa-192x192.png",
    badge: "/pwa-192x192.png",
    tag: "streak-warning",
    requireInteraction: false,
  });
}

export function showDueCardReminder(count: number): void {
  if (
    !store.isSupported ||
    store.permission !== "granted" ||
    !store.settings.dueCardReminderEnabled
  ) {
    return;
  }

  showNotificationViaServiceWorker("學測高頻單字", {
    body: `有 ${count} 張卡片到期，複習一下吧`,
    icon: "/pwa-192x192.png",
    badge: "/pwa-192x192.png",
    tag: "due-reminder",
    requireInteraction: false,
  });
}

export function testNotification(): void {
  if (!store.isSupported || store.permission !== "granted") {
    return;
  }

  showNotificationViaServiceWorker("學測高頻單字", {
    body: "通知設定成功！",
    icon: "/pwa-192x192.png",
    badge: "/pwa-192x192.png",
    tag: "test",
    requireInteraction: false,
  });
}
