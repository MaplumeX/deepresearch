import { Link, useLocation } from "react-router-dom";

import { formatDateTime } from "../lib/format";
import { StatusPill } from "./StatusPill";
import type { ResearchConversationSummary } from "../types/research";


interface ConversationListProps {
  conversations: ResearchConversationSummary[];
  emptyText: string;
  variant?: "sidebar" | "page";
}

export function ConversationList({ conversations, emptyText, variant = "sidebar" }: ConversationListProps) {
  const location = useLocation();

  if (conversations.length === 0) {
    return <div className={variant === "sidebar" ? "sidebar-empty" : "list-empty-panel"}>{emptyText}</div>;
  }

  return (
    <div className={variant === "sidebar" ? "conversation-list" : "conversation-list conversation-list-page"}>
      {conversations.map((conversation) => {
        const href = `/conversations/${conversation.conversation_id}`;
        const isActive = location.pathname === href;

        return (
          <Link
            key={conversation.conversation_id}
            to={href}
            aria-current={isActive ? "page" : undefined}
            className={isActive ? "conversation-list-item is-active" : "conversation-list-item"}
          >
            <div className="conversation-list-item-row">
              <strong>{conversation.title}</strong>
              {conversation.latest_run_status ? <StatusPill status={conversation.latest_run_status} /> : null}
            </div>
            <p>{conversation.latest_message_preview}</p>
            <span>{formatDateTime(conversation.updated_at)}</span>
          </Link>
        );
      })}
    </div>
  );
}
