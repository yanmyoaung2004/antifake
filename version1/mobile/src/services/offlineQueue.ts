import { getItem, pushToArray, setItem, clearKey } from "../utils/storage";
import { STORAGE_KEYS } from "../utils/constants";
import { postScan, ScanPayload, ScanResult } from "./api";

export async function enqueue(payload: ScanPayload): Promise<void> {
  await pushToArray(STORAGE_KEYS.OFFLINE_QUEUE, payload);
}

export async function getQueueLength(): Promise<number> {
  const queue = await getItem<ScanPayload[]>(STORAGE_KEYS.OFFLINE_QUEUE);
  return queue?.length ?? 0;
}

export async function flushQueue(): Promise<ScanResult[]> {
  const queue = await getItem<ScanPayload[]>(STORAGE_KEYS.OFFLINE_QUEUE);
  if (!queue || queue.length === 0) return [];

  const results: ScanResult[] = [];
  const failed: ScanPayload[] = [];

  for (const payload of queue) {
    try {
      const result = await postScan(payload);
      results.push(result);
    } catch {
      failed.push(payload);
    }
  }

  if (failed.length > 0) {
    await setItem(STORAGE_KEYS.OFFLINE_QUEUE, failed);
  } else {
    await clearKey(STORAGE_KEYS.OFFLINE_QUEUE);
  }

  return results;
}
