import { useMutation, useQuery } from "@tanstack/react-query";

import { createRun, getRun, listRuns, resumeRun } from "../lib/api";
import type { ResumeRequest, RunRequest } from "../types/research";

export const runsQueryKey = ["runs"] as const;
export const runDetailQueryKey = (runId: string) => ["runs", runId] as const;

export function useRunsQuery() {
  return useQuery({
    queryKey: runsQueryKey,
    queryFn: listRuns,
  });
}

export function useRunQuery(runId: string) {
  return useQuery({
    queryKey: runDetailQueryKey(runId),
    queryFn: () => getRun(runId),
    enabled: Boolean(runId),
  });
}

export function useCreateRunMutation() {
  return useMutation({
    mutationFn: (payload: RunRequest) => createRun(payload),
  });
}

export function useResumeRunMutation(runId: string) {
  return useMutation({
    mutationFn: (payload: ResumeRequest) => resumeRun(runId, payload),
  });
}
