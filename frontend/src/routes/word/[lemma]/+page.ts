import type { PageLoad, EntryGenerator } from './$types';
import { error } from '@sveltejs/kit';
import { base } from '$app/paths';

function safeFilename(lemma: string): string {
    return encodeURIComponent(lemma).replace(/%/g, '_');
}

export const load: PageLoad = async ({ params, fetch }) => {
    const { lemma } = params;
    const filename = safeFilename(lemma);

    try {
        const res = await fetch(`${base}/data/words/${filename}.json`);

        if (!res.ok) {
            throw error(404, `找不到單字: ${lemma}`);
        }

        const word = await res.json();
        return { word, lemma };
    } catch (e) {
        if ((e as { status?: number }).status === 404) {
            throw e;
        }
        throw error(500, `載入單字資料失敗: ${lemma}`);
    }
};

export const entries: EntryGenerator = async () => {
    const wordEntries = await import('$lib/data/word-entries.json');
    return (wordEntries.default as string[]).map((lemma) => ({ lemma }));
};

export const prerender = true;
