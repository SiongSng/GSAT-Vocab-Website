import type { DailyStats } from "$lib/types/srs";
import type { SRSCard } from "$lib/types/srs";
import { State } from "ts-fsrs";

export interface StreakInfo {
  currentStreak: number;
  longestStreak: number;
  lastStudyDate: string | null;
  isActiveToday: boolean;
}

export interface MasteryProgress {
  new: number;
  learning: number;
  review: number;
  mastered: number;
  total: number;
}

export interface WeeklyPattern {
  dayOfWeek: number;
  totalCards: number;
  sessionCount: number;
}

export interface HeatmapCell {
  date: string;
  count: number;
  level: 0 | 1 | 2 | 3 | 4;
}

function getTodayDateKey(): string {
  const now = new Date();
  return formatDateKey(now);
}

function formatDateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function getPreviousDay(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  date.setDate(date.getDate() - 1);
  return formatDateKey(date);
}

function hasActivity(stat: DailyStats): boolean {
  return stat.new_cards + stat.reviews > 0;
}

export function calculateStreak(dailyStats: DailyStats[]): StreakInfo {
  if (dailyStats.length === 0) {
    return {
      currentStreak: 0,
      longestStreak: 0,
      lastStudyDate: null,
      isActiveToday: false,
    };
  }

  const activeDates = new Set(
    dailyStats.filter(hasActivity).map((s) => s.date),
  );

  if (activeDates.size === 0) {
    return {
      currentStreak: 0,
      longestStreak: 0,
      lastStudyDate: null,
      isActiveToday: false,
    };
  }

  const sortedDates = Array.from(activeDates).sort((a, b) =>
    b.localeCompare(a),
  );
  const lastStudyDate = sortedDates[0];
  const today = getTodayDateKey();
  const yesterday = getPreviousDay(today);
  const isActiveToday = activeDates.has(today);

  let currentStreak = 0;
  let checkDate = isActiveToday ? today : yesterday;

  if (!isActiveToday && !activeDates.has(yesterday)) {
    currentStreak = 0;
  } else {
    while (activeDates.has(checkDate)) {
      currentStreak++;
      checkDate = getPreviousDay(checkDate);
    }
  }

  let longestStreak = 0;
  let tempStreak = 0;
  let prevDate: string | null = null;

  for (const date of sortedDates) {
    if (prevDate === null || getPreviousDay(prevDate) === date) {
      tempStreak++;
    } else {
      longestStreak = Math.max(longestStreak, tempStreak);
      tempStreak = 1;
    }
    prevDate = date;
  }
  longestStreak = Math.max(longestStreak, tempStreak);

  return {
    currentStreak,
    longestStreak,
    lastStudyDate,
    isActiveToday,
  };
}

export function getLast7DaysStats(dailyStats: DailyStats[]): DailyStats[] {
  const today = new Date();
  const result: DailyStats[] = [];
  const statsMap = new Map(dailyStats.map((s) => [s.date, s]));

  for (let i = 6; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    const dateKey = formatDateKey(date);

    const stat = statsMap.get(dateKey);
    if (stat) {
      result.push(stat);
    } else {
      result.push({
        date: dateKey,
        new_cards: 0,
        reviews: 0,
        again: 0,
        hard: 0,
        good: 0,
        easy: 0,
        study_time_ms: 0,
        updated_at: 0,
      });
    }
  }

  return result;
}

export function getMasteryProgress(cards: SRSCard[]): MasteryProgress {
  const progress: MasteryProgress = {
    new: 0,
    learning: 0,
    review: 0,
    mastered: 0,
    total: cards.length,
  };

  const MASTERY_STABILITY_THRESHOLD = 21;

  for (const card of cards) {
    switch (card.state) {
      case State.New:
        progress.new++;
        break;
      case State.Learning:
      case State.Relearning:
        progress.learning++;
        break;
      case State.Review:
        if (card.stability >= MASTERY_STABILITY_THRESHOLD) {
          progress.mastered++;
        } else {
          progress.review++;
        }
        break;
    }
  }

  return progress;
}

export function getWeeklyPattern(dailyStats: DailyStats[]): WeeklyPattern[] {
  const patterns: WeeklyPattern[] = Array.from({ length: 7 }, (_, i) => ({
    dayOfWeek: i,
    totalCards: 0,
    sessionCount: 0,
  }));

  for (const stat of dailyStats) {
    if (!hasActivity(stat)) continue;

    const date = new Date(stat.date + "T00:00:00");
    const dayOfWeek = date.getDay();

    patterns[dayOfWeek].totalCards += stat.new_cards + stat.reviews;
    patterns[dayOfWeek].sessionCount++;
  }

  return patterns;
}

export function getHeatmapData(dailyStats: DailyStats[]): HeatmapCell[][] {
  const statsMap = new Map(
    dailyStats.map((s) => [s.date, s.new_cards + s.reviews]),
  );

  // Last 6 months from today
  const endDate = new Date();
  const endDayOfWeek = endDate.getDay();
  if (endDayOfWeek !== 6) {
    endDate.setDate(endDate.getDate() + (6 - endDayOfWeek));
  }

  const startDate = new Date(endDate);
  startDate.setMonth(startDate.getMonth() - 6);
  const startDayOfWeek = startDate.getDay();
  if (startDayOfWeek !== 0) {
    startDate.setDate(startDate.getDate() - startDayOfWeek);
  }

  const allCounts: number[] = [];
  const cells: { date: string; count: number }[] = [];

  const current = new Date(startDate);
  while (current <= endDate) {
    const dateKey = formatDateKey(current);
    const count = statsMap.get(dateKey) ?? 0;
    cells.push({ date: dateKey, count });
    if (count > 0) {
      allCounts.push(count);
    }
    current.setDate(current.getDate() + 1);
  }

  const thresholds = calculateThresholds(allCounts);

  const weeks: HeatmapCell[][] = [];
  let currentWeek: HeatmapCell[] = [];

  for (const cell of cells) {
    const level = getLevel(cell.count, thresholds);
    currentWeek.push({ ...cell, level });

    if (currentWeek.length === 7) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
  }

  if (currentWeek.length > 0) {
    weeks.push(currentWeek);
  }

  return weeks;
}

function calculateThresholds(
  counts: number[],
): [number, number, number, number] {
  if (counts.length === 0) {
    return [1, 5, 10, 20];
  }

  const sorted = [...counts].sort((a, b) => a - b);
  const percentile = (p: number) => {
    const index = Math.ceil((p / 100) * sorted.length) - 1;
    return sorted[Math.max(0, index)];
  };

  return [1, percentile(25), percentile(50), percentile(75)];
}

function getLevel(
  count: number,
  thresholds: [number, number, number, number],
): 0 | 1 | 2 | 3 | 4 {
  if (count === 0) return 0;
  if (count < thresholds[1]) return 1;
  if (count < thresholds[2]) return 2;
  if (count < thresholds[3]) return 3;
  return 4;
}

export function formatDayOfWeek(dayIndex: number, short = true): string {
  const days = short
    ? ["日", "一", "二", "三", "四", "五", "六"]
    : ["週日", "週一", "週二", "週三", "週四", "週五", "週六"];
  return days[dayIndex];
}

export function formatStudyTime(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  if (minutes < 60) {
    return `${minutes} 分鐘`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (remainingMinutes === 0) {
    return `${hours} 小時`;
  }
  return `${hours} 小時 ${remainingMinutes} 分鐘`;
}

export function getTotalCardsFromStats(stats: DailyStats[]): number {
  return stats.reduce((sum, s) => sum + s.new_cards + s.reviews, 0);
}
