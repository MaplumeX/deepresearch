import { useParams } from "react-router-dom";

import { ConversationComposer } from "../components/ConversationComposer";
import { ConversationThread } from "../components/ConversationThread";
import { useConversationQuery, useCreateConversationMessageMutation } from "../hooks/useConversations";
import { useRunEvents } from "../hooks/useRunEvents";
import { useResumeRunMutation } from "../hooks/useResearchRuns";
import { formatDateTime } from "../lib/format";
import { latestConversationRun } from "../lib/conversations";


export function ConversationPage() {
  const { conversationId = "" } = useParams();
  const conversationQuery = useConversationQuery(conversationId);
  const createMessageMutation = useCreateConversationMessageMutation(conversationId);
  const conversation = conversationQuery.data;
  const latestRun = latestConversationRun(conversation);
  const resumeMutation = useResumeRunMutation(latestRun?.run_id ?? "");
  const { events, streamState } = useRunEvents({
    runId: latestRun?.run_id ?? "",
    status: latestRun?.status ?? "completed",
  });

  if (conversationQuery.isLoading) {
    return <div className="workspace-screen workspace-loading">正在加载会话...</div>;
  }

  if (conversationQuery.isError || !conversation) {
    return <div className="workspace-screen workspace-error">无法加载会话。</div>;
  }

  const latestRequest = latestRun?.request;
  const canSendFollowUp = !latestRun || !["queued", "running"].includes(latestRun.status);

  return (
    <section className="workspace-screen workspace-screen-conversation">
      <header className="conversation-header">
        <div>
          <h1>{conversation.title}</h1>
          <p>
            共 {conversation.messages.length} 条消息，最后更新于 {formatDateTime(conversation.updated_at)}
          </p>
        </div>
      </header>

      {createMessageMutation.isError ? <div className="inline-error">发送追问失败，请稍后重试。</div> : null}
      {resumeMutation.isError ? <div className="inline-error">提交审核失败，请重试。</div> : null}

      <ConversationThread
        conversation={conversation}
        activeRunId={latestRun?.run_id ?? null}
        events={events}
        streamState={streamState}
        isSubmittingReview={resumeMutation.isPending}
        onSubmitReview={(runId, payload) => {
          if (runId !== latestRun?.run_id) {
            return;
          }
          resumeMutation.mutate(payload);
        }}
      />

      <div className="composer-dock">
        {canSendFollowUp ? (
          <ConversationComposer
            isSubmitting={createMessageMutation.isPending}
            submitLabel="继续追问"
            placeholder="继续追问，或基于当前结果发起下一轮研究"
            parentRunId={latestRun?.run_id}
            initialRequest={latestRequest}
            onSubmit={(payload) => createMessageMutation.mutate(payload)}
          />
        ) : (
          <div className="composer-disabled-note">当前研究仍在执行，完成后再继续追问。</div>
        )}
      </div>
    </section>
  );
}
