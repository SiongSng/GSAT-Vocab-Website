export const STORAGE_KEYS = {
  STUDY_SETTINGS: "gsat_srs_study_settings",
  CUSTOM_DECKS: "gsat_srs_custom_decks",
  DAILY_LIMITS: "gsat_srs_limits",
  LAST_SYNC_TIME: "gsat_last_sync_time",
  DAILY_STUDIED: (date: string) => `gsat_srs_daily_${date}`,
} as const;
