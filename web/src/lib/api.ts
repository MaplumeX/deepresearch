import type {
  ResearchRun,
  ResumeRequest,
  RunDetailResponse,
  RunListResponse,
  RunRequest,
} from "../types/research";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function buildApiUrl(path: string): string {
  if (!apiBaseUrl) {
    return path;
  }
  return `${apiBaseUrl}${path}`;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    return data.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

export async function createRun(payload: RunRequest): Promise<ResearchRun> {
  const response = await requestJson<RunDetailResponse>("/api/research/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.run;
}

export async function listRuns(): Promise<RunListResponse["runs"]> {
  const response = await requestJson<RunListResponse>("/api/research/runs");
  return response.runs;
}

export async function getRun(runId: string): Promise<ResearchRun> {
  const response = await requestJson<RunDetailResponse>(`/api/research/runs/${runId}`);
  return response.run;
}

export async function resumeRun(runId: string, payload: ResumeRequest): Promise<ResearchRun> {
  const response = await requestJson<RunDetailResponse>(`/api/research/runs/${runId}/resume`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.run;
}

export function createRunEventSource(runId: string): EventSource {
  return new EventSource(buildApiUrl(`/api/research/runs/${runId}/events`));
}
