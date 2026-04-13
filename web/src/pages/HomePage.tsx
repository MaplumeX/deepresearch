import { useNavigate } from "react-router-dom";

import { ConversationComposer } from "../components/ConversationComposer";
import { useCreateConversationMutation } from "../hooks/useConversations";


export function HomePage() {
  const navigate = useNavigate();
  const createConversationMutation = useCreateConversationMutation();

  return (
    <section className="workspace-screen workspace-screen-home">
      <div className="empty-thread">
        <header className="screen-header">
          <h1>开始新的研究</h1>
          <p>提出问题，系统会创建一条新会话，并把后续研究过程和结果组织成连续线程。</p>
        </header>

        {createConversationMutation.isError ? <div className="inline-error">创建会话失败，请稍后重试。</div> : null}

        <ConversationComposer
          isSubmitting={createConversationMutation.isPending}
          submitLabel="开始研究"
          placeholder="例如：比较 LangGraph deep research agent 的执行模型、恢复策略和线程设计"
          defaultSettingsOpen
          onSubmit={(payload) =>
            createConversationMutation.mutate(payload, {
              onSuccess: ({ conversation }) => navigate(`/conversations/${conversation.conversation_id}`),
            })
          }
        />
      </div>
    </section>
  );
}
