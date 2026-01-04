import type { WordEntry, PhraseEntry, PatternEntry } from "$lib/types/vocab";
import { lookupEntry } from "./vocab-db";
import { getAppStore } from "./app.svelte";

type VocabEntry = WordEntry | PhraseEntry | PatternEntry;

interface LookupItem {
    lemma: string;
    entry: VocabEntry | null;
    isLoading: boolean;
}

interface WordLookupState {
    items: LookupItem[];
    mobileItem: LookupItem | null;
}

let state = $state<WordLookupState>({
    items: [],
    mobileItem: null,
});


export function getWordLookupStore() {
    return {
        get items() {
            return state.items;
        },
        get mobileItem() {
            return state.mobileItem;
        },
        get hasItems() {
            return state.items.length > 0;
        },
        get isMobileOpen() {
            return state.mobileItem !== null;
        },
        get position() {
            const app = getAppStore();
            return app.isMobile ? "bottom-sheet" : "sidebar";
        },
    };
}

export async function openLookup(lemma: string) {
    const app = getAppStore();

    if (app.isMobile) {
        if (state.mobileItem?.lemma === lemma) {
            return;
        }
        state.mobileItem = {
            lemma,
            entry: null,
            isLoading: true,
        };
        try {
            const entry = await lookupEntry(lemma);
            if (state.mobileItem?.lemma === lemma) {
                state.mobileItem.entry = entry ?? null;
                state.mobileItem.isLoading = false;
            }
        } catch {
            if (state.mobileItem?.lemma === lemma) {
                state.mobileItem.isLoading = false;
            }
        }
    } else {
        const existingIndex = state.items.findIndex((item) => item.lemma === lemma);
        if (existingIndex !== -1) {
            const [existing] = state.items.splice(existingIndex, 1);
            state.items.push(existing);
            return;
        }

        const newItem: LookupItem = {
            lemma,
            entry: null,
            isLoading: true,
        };

        state.items.push(newItem);

        try {
            const entry = await lookupEntry(lemma);
            const itemIndex = state.items.findIndex((item) => item.lemma === lemma);
            if (itemIndex !== -1) {
                state.items[itemIndex].entry = entry ?? null;
                state.items[itemIndex].isLoading = false;
            }
        } catch {
            const itemIndex = state.items.findIndex((item) => item.lemma === lemma);
            if (itemIndex !== -1) {
                state.items[itemIndex].isLoading = false;
            }
        }
    }
}

export function closeLookupItem(lemma: string) {
    const app = getAppStore();

    if (app.isMobile) {
        if (state.mobileItem?.lemma === lemma) {
            state.mobileItem = null;
        }
    } else {
        const index = state.items.findIndex((item) => item.lemma === lemma);
        if (index !== -1) {
            state.items.splice(index, 1);
        }
    }
}

export function closeLookup() {
    const app = getAppStore();
    if (app.isMobile) {
        state.mobileItem = null;
    } else {
        state.items = [];
    }
}

export function closeAllLookups() {
    state.items = [];
    state.mobileItem = null;
}
