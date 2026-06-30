export const API_BASE_URL = __DEV__
  ? "http://10.0.2.2:8000"
  : "https://api.antifake.io";

export const STORAGE_KEYS = {
  OFFLINE_QUEUE: "antifake:offline_queue",
  HISTORY: "antifake:history",
  BATCH_ROOTS: "antifake:batch_roots",
} as const;
