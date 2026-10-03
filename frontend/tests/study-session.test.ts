import 'fake-indexeddb/auto';
import { afterAll, beforeAll, beforeEach, expect, test } from 'bun:test';
import { createServer, type ViteDevServer } from 'vite';
import type { WordEntry, PhraseEntry } from '../src/lib/types/vocab';

let server: ViteDevServer;
let db: typeof import('../src/lib/stores/vocab-db');
let srs: typeof import('../src/lib/stores/srs.svelte');
let storage: typeof import('../src/lib/stores/srs-storage');

const shared = {
  frequency: {
    total_appearances: 1, tested_count: 1, active_tested_count: 1,
    year_spread: 1, years: [2025], by_role: {}, by_section: {},
    by_exam_type: {}, ml_score: null, importance_score: 1,
  },
  senses: [{
    sense_id: 'primary', pos: 'NOUN', zh_def: '測試', en_def: 'test',
    examples: [], generated_example: '',
  }],
  confusion_notes: [], synonyms: null, antonyms: null, derived_forms: null,
};
const word: WordEntry = {
  ...shared, lemma: 'apple', pos: ['NOUN'], level: 1,
  in_official_list: true, root_info: null,
};
const phrase: PhraseEntry = { ...shared, lemma: 'as usual' };

beforeAll(async () => {
  server = await createServer({
    server: { middlewareMode: true, watch: null, hmr: false },
    optimizeDeps: { noDiscovery: true, include: [] },
  });
  db = await server.ssrLoadModule('/src/lib/stores/vocab-db.ts');
  srs = await server.ssrLoadModule('/src/lib/stores/srs.svelte.ts');
  storage = await server.ssrLoadModule('/src/lib/stores/srs-storage.ts');
  await srs.initSRS();
  await db.bulkInsertWords([word, { ...word, lemma: 'banana' }, { ...word, lemma: 'empty', senses: [] }]);
  await db.bulkInsertPhrases([phrase]);
});

beforeEach(async () => {
  await srs.endStudySession();
  await storage.setAllCards([]);
  await db.closeDB();
});

afterAll(async () => {
  await srs?.endStudySession();
  await db?.closeDB();
  await server?.close();
});

test('starts words and phrases from persisted vocabulary with an empty cache', async () => {
  expect(db.getWordCached('apple')).toBeUndefined();
  const options = { newLimit: 2, selectionPool: ['apple', 'as usual'], isCustomDeck: true };
  expect(srs.getSessionCardCounts(options).newCount).toBe(2);
  await srs.startStudySession(options);
  expect(srs.getSRSStore().studyQueue.map(card => card.lemma).sort())
    .toEqual(['apple', 'as usual']);
  expect(srs.getSRSStore().currentCard).not.toBeNull();
  expect(storage.getCardsByLemma('as usual')[0].entry_type).toBe('phrase');
});

test('crams a saved deck with new entries and future reviews without including other cards', async () => {
  srs.ensureEntryCard({ ...word, lemma: 'banana' });
  const card = srs.ensureEntryCard(word)!;
  storage.updateCard({ ...card, state: srs.State.Review, due: new Date('2099-01-01'), reps: 3 });
  await srs.startStudySession({
    newLimit: 0, selectionPool: ['apple', 'as usual'], cramMode: true,
  });
  expect(srs.getSRSStore().studyQueue.map(card => card.lemma).sort())
    .toEqual(['apple', 'as usual']);
  expect(storage.getCardsByLemma('apple')[0].reps).toBe(3);
  expect(srs.getSRSStore().cramMode).toBe(true);
});

test('does not treat an explicit empty pool as all stored new cards', async () => {
  srs.ensureEntryCard(word);
  await srs.startStudySession({ newLimit: 20, selectionPool: [] });
  expect(srs.getSessionCardCounts({ newLimit: 20, selectionPool: [] }).total).toBe(0);
  expect(srs.getSRSStore().studyQueue).toHaveLength(0);
});

test('applies exclusions and deduplicates the pool before applying the new-card limit', async () => {
  await srs.startStudySession({
    newLimit: 2, selectionPool: ['missing', 'apple', 'apple', 'as usual'],
    excludeLemmas: new Set(['missing']),
  });
  expect(srs.getSRSStore().studyQueue.map(card => card.lemma).sort())
    .toEqual(['apple', 'as usual']);
});

test('rejects missing vocabulary without partially creating cards', async () => {
  await expect(srs.startStudySession({
    newLimit: 2, selectionPool: ['apple', 'missing'],
  })).rejects.toThrow();
  expect(storage.getAllCards()).toHaveLength(0);
  expect(srs.getSRSStore().isStudying).toBe(false);
});

test('rejects entries without senses instead of silently dropping them', async () => {
  await expect(srs.startStudySession({
    newLimit: 1, selectionPool: ['empty'],
  })).rejects.toThrow();
  expect(storage.getAllCards()).toHaveLength(0);
});

test('keeps due reviews when the daily new-card limit is zero', async () => {
  const card = srs.ensureEntryCard(word)!;
  storage.updateCard({ ...card, state: srs.State.Review, due: new Date(0) });
  await srs.startStudySession({ newLimit: 0, selectionPool: ['missing'] });
  expect(srs.getSRSStore().studyQueue.map(card => card.lemma)).toEqual(['apple']);
});

test('does not reintroduce future reviews as new cards', async () => {
  const card = srs.ensureEntryCard(word)!;
  storage.updateCard({ ...card, state: srs.State.Review, due: new Date('2099-01-01') });
  await srs.startStudySession({ newLimit: 1, selectionPool: ['apple', 'as usual'] });
  expect(srs.getSRSStore().studyQueue.map(card => card.lemma)).toEqual(['as usual']);
});

test('cancels a pending start without creating cards or activating a session', async () => {
  const controller = new AbortController();
  const pending = srs.startStudySession({ newLimit: 1, selectionPool: ['apple'] }, controller.signal);
  controller.abort();
  await expect(pending).rejects.toThrow();
  expect(storage.getAllCards()).toHaveLength(0);
  expect(srs.getSRSStore().isStudying).toBe(false);
});
