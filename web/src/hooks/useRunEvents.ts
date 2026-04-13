import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { createRunEventSource } from "../lib/api";
import { upsertConversationMessage, upsertConversationRun, upsertConversationSummary } from "../lib/conversations";
import { eventMessage, isTerminalStatus, upsertRunSummary } from "../lib/runs";
import { conversationDetailQueryKey, conversationsQueryKey } from "./useConversations";
import { runDetailQueryKey, runsQueryKey } from "./useResearchRuns";
import type {
  ResearchConversationDetail,
  ResearchConversationSummary,
  ResearchRunEvent,
  ResearchRunSummary,
  RunStatus,
} from "../types/research";

interface EventLogEntry {
  id: string;
  message: string;
  timestamp: string;
}

interface UseRunEventsOptions {
  runId: string;
  status: RunStatus;
}

export function useRunEvents({ runId, status }: UseRunEventsOptions) {
  const queryClient = useQueryClient();
  const [events, setEvents] = useState<EventLogEntry[]>([]);
  const [streamState, setStreamState] = useState<"idle" | "connecting" | "open" | "error">("idle");

  useEffect(() => {
    setEvents([]);
  }, [runId]);

  useEffect(() => {
    if (!runId || isTerminalStatus(status)) {
      setStreamState("idle");
      return undefined;
    }

    const source = createRunEventSource(runId);
    setStreamState("connecting");

    const applyEvent = (event: ResearchRunEvent) => {
      const run = event.data.run;
      if (run) {
        queryClient.setQueryData(runDetailQueryKey(runId), run);
        queryClient.setQueryData<ResearchRunSummary[] | undefined>(runsQueryKey, (current) =>
          upsertRunSummary(current, run),
        );
        queryClient.setQueryData<ResearchConversationDetail | undefined>(
          conversationDetailQueryKey(run.conversation_id),
          (current) => {
            if (!current) {
              return current;
            }
            let next = upsertConversationRun(current, run);
            if (event.data.assistant_message) {
              next = upsertConversationMessage(next, event.data.assistant_message);
            }
            return next;
          },
        );
      }

      if (event.data.conversation) {
        const nextConversation = event.data.conversation;
        queryClient.setQueryData<ResearchConversationSummary[] | undefined>(conversationsQueryKey, (current) =>
          upsertConversationSummary(current, nextConversation),
        );
      }

      setEvents((current) => {
        const next = [
          {
            id: `${event.timestamp}-${event.type}`,
            message: eventMessage(event),
            timestamp: event.timestamp,
          },
          ...current,
        ];
        return next.slice(0, 12);
      });
    };

    source.onopen = () => setStreamState("open");
    source.onerror = () => setStreamState("error");

    const eventTypes: ResearchRunEvent["type"][] = [
      "run.created",
      "run.status_changed",
      "run.progress",
      "run.interrupted",
      "run.completed",
      "run.failed",
      "run.resumed",
    ];

    for (const eventType of eventTypes) {
      source.addEventListener(eventType, (messageEvent: MessageEvent<string>) => {
        const event = JSON.parse(messageEvent.data) as ResearchRunEvent;
        applyEvent(event);
        if (isTerminalStatus(event.status)) {
          source.close();
        }
      });
    }

    return () => {
      source.close();
    };
  }, [queryClient, runId, status]);

  return {
    events,
    streamState,
  };
}
