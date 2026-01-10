import { browser } from '$app/environment';

export function safeGetItem(key: string): string | null {
    if (!browser) return null;
    return localStorage.getItem(key);
}

export function safeSetItem(key: string, value: string): void {
    if (!browser) return;
    localStorage.setItem(key, value);
}

export function safeRemoveItem(key: string): void {
    if (!browser) return;
    localStorage.removeItem(key);
}
