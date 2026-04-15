from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    question: str = Field(min_length=1)
    scope: str | None = None
    output_language: Literal["zh-CN", "en"] = "zh-CN"
    max_iterations: int = Field(default=2, ge=1, le=5)
    max_parallel_tasks: int = Field(default=3, ge=1, le=5)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


class ResearchTask(BaseModel):
    task_id: str
    title: str
    question: str
    status: Literal["pending", "running", "done", "failed"] = "pending"


class ResearchPlan(BaseModel):
    tasks: list[ResearchTask]


ContentFormat = Literal["html", "text", "markdown"]
AcquisitionMethod = Literal["provider_raw_content", "http_fetch", "search_snippet"]


class SearchHit(BaseModel):
    title: str
    url: str
    snippet: str = ""
    providers: list[str] = Field(default_factory=list)
    provider_metadata: dict[str, dict[str, Any]] = Field(default_factory=dict)
    raw_content: str | None = None
    raw_content_format: ContentFormat | None = None


class AcquiredContent(BaseModel):
    url: str
    title: str
    content: str
    content_format: ContentFormat
    acquired_at: str
    providers: list[str] = Field(default_factory=list)
    acquisition_method: AcquisitionMethod
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceDocument(BaseModel):
    source_id: str
    url: str
    title: str
    content: str
    fetched_at: str
    providers: list[str] = Field(default_factory=list)
    acquisition_method: AcquisitionMethod = "http_fetch"
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    evidence_id: str
    task_id: str
    claim: str
    snippet: str
    source_id: str
    url: str
    title: str
    relevance_score: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)


class ReportSectionDraft(BaseModel):
    heading: str
    body_markdown: str


class ReportSection(BaseModel):
    section_id: str
    heading: str
    body_markdown: str
    cited_source_ids: list[str] = Field(default_factory=list)


class CitationIndexEntry(BaseModel):
    source_id: str
    title: str
    url: str
    snippet: str = ""
    providers: list[str] = Field(default_factory=list)
    acquisition_method: AcquisitionMethod | None = None
    cited_in_sections: list[str] = Field(default_factory=list)
    occurrence_count: int = Field(default=0, ge=0)
    relevance_score: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)


class SourceCard(BaseModel):
    source_id: str
    title: str
    url: str
    snippet: str = ""
    providers: list[str] = Field(default_factory=list)
    acquisition_method: AcquisitionMethod | None = None
    fetched_at: str = ""
    is_cited: bool = False


class StructuredReport(BaseModel):
    title: str
    summary: str
    markdown: str
    sections: list[ReportSection] = Field(default_factory=list)
    cited_source_ids: list[str]
    citation_index: list[CitationIndexEntry] = Field(default_factory=list)
    source_cards: list[SourceCard] = Field(default_factory=list)


class ReportDraft(BaseModel):
    title: str
    summary: str
    sections: list[ReportSectionDraft] = Field(default_factory=list)


GapType = Literal["missing_evidence", "weak_evidence", "low_source_diversity", "retrieval_failure"]
GapSeverity = Literal["low", "medium", "high"]
TaskQualityStatus = Literal["ok", "weak", "failed"]
ResearchProgressPhase = Literal[
    "queued",
    "clarifying_scope",
    "planning",
    "executing_tasks",
    "merging_evidence",
    "checking_gaps",
    "replanning",
    "synthesizing",
    "auditing",
    "awaiting_review",
    "finalizing",
    "completed",
    "failed",
]
ResearchWorkerStep = Literal[
    "rewrite_queries",
    "search_and_rank",
    "acquire_and_filter",
    "extract_and_score",
    "emit_results",
]


class ResearchTaskOutcome(BaseModel):
    task_id: str
    title: str
    quality_status: TaskQualityStatus
    query_count: int = Field(default=0, ge=0)
    search_hit_count: int = Field(default=0, ge=0)
    acquired_content_count: int = Field(default=0, ge=0)
    kept_source_count: int = Field(default=0, ge=0)
    evidence_count: int = Field(default=0, ge=0)
    host_count: int = Field(default=0, ge=0)
    failure_reasons: list[str] = Field(default_factory=list)


class ResearchGap(BaseModel):
    gap_type: GapType
    task_id: str
    title: str
    reason: str
    retry_hint: str
    severity: GapSeverity = "medium"


class QualityGateResult(BaseModel):
    passed: bool = True
    should_replan: bool = False
    requires_review: bool = False
    reasons: list[str] = Field(default_factory=list)


RunStatus = Literal["queued", "running", "interrupted", "completed", "failed"]
ChatTurnStatus = Literal["queued", "running", "completed", "failed"]
RunEventType = Literal[
    "run.created",
    "run.status_changed",
    "run.progress",
    "run.interrupted",
    "run.completed",
    "run.failed",
    "run.resumed",
]
ChatEventType = Literal[
    "chat.turn.created",
    "chat.turn.status_changed",
    "chat.turn.progress",
    "chat.turn.completed",
    "chat.turn.failed",
]


class MemoryFact(BaseModel):
    fact: str
    source_ids: list[str] = Field(default_factory=list)


class RecentTurnMemory(BaseModel):
    run_id: str
    question: str
    answer_digest: str
    status: RunStatus
    created_at: str


class ConversationMemoryPayload(BaseModel):
    rolling_summary: str = ""
    recent_turns: list[RecentTurnMemory] = Field(default_factory=list)
    key_facts: list[MemoryFact] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class PersistedConversationMemory(BaseModel):
    conversation_id: str
    rolling_summary: str = ""
    key_facts: list[MemoryFact] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    updated_at: str


class ResearchRunSummary(BaseModel):
    run_id: str
    conversation_id: str
    origin_message_id: str
    assistant_message_id: str
    parent_run_id: str | None = None
    status: RunStatus
    request: ResearchRequest
    error_message: str | None = None
    created_at: str
    updated_at: str
    completed_at: str | None = None


class ResearchRunDetail(ResearchRunSummary):
    result: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    progress_events: list["ResearchRunHistoryEvent"] = Field(default_factory=list)


ConversationMessageRole = Literal["user", "assistant"]
ConversationMode = Literal["chat", "research"]


class ConversationMessage(BaseModel):
    message_id: str
    conversation_id: str
    role: ConversationMessageRole
    content: str
    run_id: str | None = None
    parent_message_id: str | None = None
    created_at: str
    updated_at: str


class ResearchConversationSummary(BaseModel):
    conversation_id: str
    mode: ConversationMode
    title: str
    latest_message_preview: str
    latest_run_status: RunStatus | None = None
    created_at: str
    updated_at: str
    is_pinned: bool = False


class ResearchConversationDetail(ResearchConversationSummary):
    messages: list[ConversationMessage] = Field(default_factory=list)
    runs: list[ResearchRunDetail] = Field(default_factory=list)


class ResearchProgressCounts(BaseModel):
    planned_tasks: int | None = Field(default=None, ge=0)
    completed_tasks: int | None = Field(default=None, ge=0)
    search_hits: int | None = Field(default=None, ge=0)
    acquired_contents: int | None = Field(default=None, ge=0)
    kept_sources: int | None = Field(default=None, ge=0)
    evidence_count: int | None = Field(default=None, ge=0)
    warnings: int | None = Field(default=None, ge=0)


class ResearchTaskProgress(BaseModel):
    task_id: str
    title: str
    index: int = Field(ge=1)
    total: int = Field(ge=1)
    status: Literal["pending", "running", "done", "failed"] = "running"
    worker_step: ResearchWorkerStep | None = None


class ResearchReviewProgress(BaseModel):
    required: bool = False
    kind: Literal["human_review"] | None = None


class ResearchProgressPayload(BaseModel):
    phase: ResearchProgressPhase
    phase_label: str
    iteration: int | None = Field(default=None, ge=1)
    max_iterations: int | None = Field(default=None, ge=1)
    task: ResearchTaskProgress | None = None
    counts: ResearchProgressCounts = Field(default_factory=ResearchProgressCounts)
    review: ResearchReviewProgress = Field(default_factory=ResearchReviewProgress)


class ResearchRunHistoryEvent(BaseModel):
    event_type: RunEventType
    status: RunStatus
    timestamp: str
    message: str | None = None
    progress: ResearchProgressPayload | None = None


class ResearchRunEvent(BaseModel):
    type: RunEventType
    run_id: str
    status: RunStatus
    timestamp: str
    data: dict[str, Any] = Field(default_factory=dict)


class ChatTurnSummary(BaseModel):
    turn_id: str
    conversation_id: str
    origin_message_id: str
    assistant_message_id: str
    status: ChatTurnStatus
    request: ChatRequest
    error_message: str | None = None
    created_at: str
    updated_at: str
    completed_at: str | None = None


class ChatTurnDetail(ChatTurnSummary):
    pass


class ChatTurnEvent(BaseModel):
    type: ChatEventType
    turn_id: str
    status: ChatTurnStatus
    timestamp: str
    data: dict[str, Any] = Field(default_factory=dict)
