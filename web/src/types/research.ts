export type OutputLanguage = "zh-CN" | "en";
export type RunStatus = "queued" | "running" | "interrupted" | "completed" | "failed";
export type RunEventType =
  | "run.created"
  | "run.status_changed"
  | "run.progress"
  | "run.interrupted"
  | "run.completed"
  | "run.failed"
  | "run.resumed";

export interface RunRequest {
  question: string;
  scope?: string;
  output_language: OutputLanguage;
  max_iterations: number;
  max_parallel_tasks: number;
}

export interface ResumeRequest {
  approved: boolean;
  edited_report?: string;
}

export interface ResearchRun {
  run_id: string;
  status: RunStatus;
  request: RunRequest;
  result: Record<string, unknown> | null;
  warnings: string[];
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface RunDetailResponse {
  run: ResearchRun;
}

export interface RunListResponse {
  runs: ResearchRunSummary[];
}

export type ResearchRunSummary = Omit<ResearchRun, "result" | "warnings">;

export interface ResearchRunEvent {
  type: RunEventType;
  run_id: string;
  status: RunStatus;
  timestamp: string;
  data: {
    message?: string;
    resume_payload?: ResumeRequest;
    run?: ResearchRun;
  };
}
