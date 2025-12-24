# SRS Sense-Aware Upgrade Spec (Breaking Change OK)

## Goals
- Track forgetting curves per sense (`lemma + sense_id`) instead of per lemma only.
- Prioritize and unlock senses in line with UI redesign: primary meaning first, secondary meanings when the primary is stable.
- Persist learning history (per-day aggregates and session spans) in IndexedDB to power long-term charts.
- Keep smart ordering ML-driven while respecting sense priority.

## Constraints & Breaking Changes
- No backward compatibility required. Clearing existing SRS data is acceptable.
- IndexedDB schema will bump to version 2 and wipe old SRS data during upgrade.
- `localStorage` daily counters are optional cache only; IndexedDB is the sole source of truth.

## Sense Priority Rules
1. Compute a prioritized sense list per lemma:
   - Descending by real-exam example count (`examples.length`).
   - Then `tested_in_exam = true`.
   - Then original order as tiebreaker.
2. Define `primary_sense_id` = first in the prioritized list.
3. When a card has an unknown/missing `sense_id`, map it to `primary_sense_id`.

## Sense Creation & Unlocking
- When adding a lemma to SRS, create cards for all senses (`lemma + sense_id`). At minimum, ensure `primary_sense_id` exists.
- Unlocking secondary senses:
  - Default rule: primary card `stability >= 10` **and** `state === Review`.
  - Allow a feature flag for “all senses mode” that skips the unlock gate.
- Session queue includes:
  - Learning/Relearning/Review cards due now (any sense).
  - New cards: only senses allowed by unlock rules. Order senses per priority list; avoid enqueuing multiple senses of the same lemma in the same session unless unlocked.

## Flashcard Rendering
- Resolve the displayed sense using the priority list; fall back to `primary_sense_id` if the card’s `sense_id` is missing.
- The “涵義 X/Y” indicator reflects the prioritized order, not raw array order.
- Examples: prefer real exam examples; randomize within the sense as now.

## Smart Ordering
- New card pool continues to sort by `importance_score` (ML score fallback).
- When multiple senses of a lemma are eligible, order lemmas by importance, then senses by priority (example count/tested flag).

## Data Persistence for Charts
- Extend IndexedDB (version 2) with two stores:
  - `daily_stats`: key `YYYY-MM-DD`; value `{ new_cards, reviews, again, hard, good, easy, study_time_ms, updated_at }`.
  - `session_logs` (optional): auto-increment key; value `{ session_id, start, end, studied }`.
- Review logs remain per sense. Append `{ lemma, sense_id, rating, state_before, state_after, review }`.
- Provide read helpers:
  - `getDailyStats(rangeStart?, rangeEnd?)`
  - `getReviewLogs({ lemma?, sense_id?, rangeStart?, rangeEnd? })`
  - `getSessions(rangeStart?, rangeEnd?)`
- Write helpers update `daily_stats` on each review and `session_logs` on session end.

## Reset Steps (no compatibility)
- Bump DB version to 2; drop/clear prior SRS stores.
- Seed cards from vocab index with full sense creation (per rules above).
- Start fresh aggregates/logs; optionally set a meta flag to show a one-time “SRS reset” notice.

## Validation Checklist
- Start session with a multi-sense lemma: only primary appears before unlock; secondary appears after primary stability threshold.
- Flashcard shows the correct sense and accurate “涵義 X/Y” based on priority.
- Daily stats survive reload and match the number of reviews/new cards performed.
- New card pool ordering remains ML-driven; toggling smart mode still works.
