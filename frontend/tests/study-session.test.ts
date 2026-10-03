import 'fake-indexeddb/auto';
import { afterAll, beforeAll, expect, test } from 'bun:test';
import { createServer, type ViteDevServer } from 'vite';

let server: ViteDevServer;
let db: typeof import('../src/lib/stores/vocab-db');
let srs: typeof import('../src/lib/stores/srs.svelte');
let storage: typeof import('../src/lib/stores/srs-storage');

beforeAll(async () => {
  server = await createServer({
    server: { middlewareMode: true, watch: null, hmr: false },
    optimizeDeps: { noDiscovery: true, include: [] },
  });
  db = await server.ssrLoadModule('/src/lib/stores/vocab-db.ts');
  srs = await server.ssrLoadModule('/src/lib/stores/srs.svelte.ts');
  storage = await server.ssrLoadModule('/src/lib/stores/srs-storage.ts');
  await srs.initSRS();
});

afterAll(async () => {
  await srs?.endStudySession();
  await db?.closeDB();
  await server?.close();
});

test('starts a new deck from persisted vocabulary after the memory cache is cleared', async () => {
  const frequency = {
    total_appearances: 1, tested_count: 1, active_tested_count: 1,
    year_spread: 1, years: [2025], by_role: {}, by_section: {},
    by_exam_type: {}, ml_score: null, importance_score: 1,
  };
  const senses = [{
    sense_id: 'primary', pos: 'NOUN', zh_def: '測試', en_def: 'test',
    examples: [], generated_example: '',
  }];
  const shared = {
    frequency, senses, confusion_notes: [], synonyms: null,
    antonyms: null, derived_forms: null,
  };
  await db.bulkInsertWords([{
    ...shared, lemma: 'apple', pos: ['NOUN'], level: 1,
    in_official_list: true, root_info: null,
  }]);
  await db.bulkInsertPhrases([{ ...shared, lemma: 'as usual' }]);
  await db.closeDB();
  expect(db.getSRSEligibleEntryCached('apple')).toBeUndefined();
  expect(db.getSRSEligibleEntryCached('as usual')).toBeUndefined();

  const options = await srs.prepareStudySession({
    newLimit: 2, selectionPool: ['apple', 'as usual'], isCustomDeck: true,
  });
  srs.startStudySession(options);
  expect(srs.getSRSStore().studyQueue.map(card => card.lemma).sort())
    .toEqual(['apple', 'as usual']);
  expect(srs.getSRSStore().currentCard).not.toBeNull();
  expect(storage.getCardsByLemma('as usual')[0].entry_type).toBe('phrase');
  await srs.endStudySession();

  const limited = await srs.prepareStudySession({
    newLimit: 1, selectionPool: ['apple', 'as usual'],
  });
  srs.startStudySession(limited);
  expect(srs.getSRSStore().studyQueue.map(card => card.lemma)).toEqual(['apple']);
  await srs.endStudySession();
});

test('fails explicitly when a requested entry is missing instead of starting an empty session', async () => {
  await expect(srs.prepareStudySession({
    newLimit: 1, selectionPool: ['missing-entry'], isCustomDeck: true,
  })).rejects.toThrow();
  expect(srs.getSRSStore().isStudying).toBe(false);
});

test('keeps due reviews when the daily new-card limit is zero', async () => {
  const card = storage.getCardsByLemma('apple')[0];
  storage.updateCard({ ...card, state: srs.State.Review, due: new Date(0) });
  const options = await srs.prepareStudySession({
    newLimit: 0, selectionPool: ['missing-entry'],
  });
  srs.startStudySession(options);
  expect(srs.getSRSStore().studyQueue.map(card => card.lemma)).toEqual(['apple']);
  await srs.endStudySession();
});
