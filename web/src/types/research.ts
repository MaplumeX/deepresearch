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

export interface ConversationTurnRequest extends RunRequest {
  parent_run_id?: string;
}

export interface ResumeRequest {
  approved: boolean;
  edited_report?: string;
}

export interface ResearchRun {
  run_id: string;
  conversation_id: string;
  origin_message_id: string;
  assistant_message_id: string;
  parent_run_id: string | null;
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

export interface ConversationMessage {
  message_id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  run_id: string | null;
  parent_message_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResearchConversationSummary {
  conversation_id: string;
  title: string;
  latest_message_preview: string;
  latest_run_status: RunStatus | null;
  created_at: string;
  updated_at: string;
}

export interface ResearchConversationDetail extends ResearchConversationSummary {
  messages: ConversationMessage[];
  runs: ResearchRun[];
}

export interface ConversationDetailResponse {
  conversation: ResearchConversationDetail;
}

export interface ConversationListResponse {
  conversations: ResearchConversationSummary[];
}

export interface ConversationMutationResponse {
  conversation: ResearchConversationDetail;
  run: ResearchRun;
}

export interface ResearchRunEvent {
  type: RunEventType;
  run_id: string;
  status: RunStatus;
  timestamp: string;
  data: {
    message?: string;
    resume_payload?: ResumeRequest;
    run?: ResearchRun;
    conversation?: ResearchConversationSummary;
    assistant_message?: ConversationMessage;
  };
}
