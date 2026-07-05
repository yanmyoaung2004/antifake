import axios from "axios";

import { API_BASE_URL } from "../utils/constants";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
});

export interface ScanPayload {
  serial: string;
  batch_id: string;
  lat: number;
  lng: number;
  timestamp: string;
  role: "consumer" | "wholesaler" | "regulator";
  crypto_image?: string;
}

export interface ScanResult {
  status: "verified" | "flagged" | "prompt" | "error";
  confidence: number;
  message: string;
  cached: boolean;
  last_verified: string | null;
}

export async function postScan(payload: ScanPayload): Promise<ScanResult> {
  const resp = await client.post<ScanResult>("/api/v1/scan", payload);
  return resp.data;
}

export async function getHealth(): Promise<boolean> {
  try {
    const resp = await client.get("/api/v1/health");
    return resp.data?.status === "ok";
  } catch {
    return false;
  }
}
