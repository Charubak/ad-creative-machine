import type { ProjectInput } from "../types";

const BASE = "/api/ad-machine";

async function req<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, { credentials: "include", ...options });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`${res.status}: ${err}`);
  }
  return res.json();
}

export const adMachineApi = {
  createProject: (input: ProjectInput) =>
    req<{ project_id: string }>(`${BASE}/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  runProject: (projectId: string, voiceProfileId = "demo") =>
    req<{ job_id: string; project_id: string }>(`${BASE}/projects/${projectId}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voice_profile_id: voiceProfileId }),
    }),

  getProject: (projectId: string) =>
    req<Record<string, unknown>>(`${BASE}/projects/${projectId}`),

  getJob: (jobId: string) =>
    req<Record<string, unknown>>(`${BASE}/jobs/${jobId}`),

  getBrief: (briefId: string) =>
    req<Record<string, unknown>>(`${BASE}/briefs/${briefId}`),

  getCopyPack: (packId: string) =>
    req<Record<string, unknown>>(`${BASE}/copy-packs/${packId}`),

  getCreativePack: (packId: string) =>
    req<Record<string, unknown>>(`${BASE}/creative-packs/${packId}`),

  editCopyVariation: (variationId: string, payload: Record<string, unknown>) =>
    req<{ variation_id: string; updated: boolean }>(`${BASE}/copy-variations/${variationId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload }),
    }),

  regenerateCopy: (variationId: string) =>
    req<unknown>(`${BASE}/copy-variations/${variationId}/regenerate`, { method: "POST" }),

  regenerateVisual: (assetId: string) =>
    req<unknown>(`${BASE}/visual-assets/${assetId}/regenerate`, { method: "POST" }),

  repairPairing: (pairingId: string, visualAssetIds: string[]) =>
    req<{ pairing_id: string; updated: boolean }>(`${BASE}/pairings/${pairingId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visual_asset_ids: visualAssetIds }),
    }),

  exportZip: (packId: string) =>
    req<{ zip_url: string }>(`${BASE}/creative-packs/${packId}/export/zip`, { method: "POST" }),

  exportRsaCsv: (packId: string, params: Record<string, string>) =>
    req<{ csv_url: string }>(`${BASE}/creative-packs/${packId}/export/google-rsa-csv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    }),

  pushBuffer: (packId: string, pairingIds: string[], profileMap: Record<string, string>) =>
    req<Record<string, unknown>>(`${BASE}/creative-packs/${packId}/export/buffer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pairing_ids: pairingIds, profile_map: profileMap }),
    }),

  uploadPerformance: (packId: string, platform: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<Record<string, unknown>>(
      `${BASE}/creative-packs/${packId}/performance/upload?platform=${platform}`,
      { method: "POST", body: fd }
    );
  },

  labelPerformance: (performanceId: string, label: string | null, notes: string | null) =>
    req<{ performance_id: string; updated: boolean }>(`${BASE}/performance/${performanceId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_label: label, user_notes: notes }),
    }),

  iterate: (projectId: string, userNotes = "") =>
    req<{ job_id: string; project_id: string }>(`${BASE}/projects/${projectId}/iterate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_notes: userNotes }),
    }),

  streamJobUrl: (jobId: string) => `${BASE}/jobs/${jobId}/stream`,
};
