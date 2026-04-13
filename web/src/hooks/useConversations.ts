import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createConversation,
  createConversationMessage,
  getConversation,
  listConversations,
} from "../lib/api";
import { upsertConversationSummary } from "../lib/conversations";
import { upsertRunSummary } from "../lib/runs";
import { runDetailQueryKey, runsQueryKey } from "./useResearchRuns";
import type {
  ConversationTurnRequest,
  ConversationMutationResponse,
  ResearchConversationSummary,
  ResearchRunSummary,
} from "../types/research";


export const conversationsQueryKey = ["conversations"] as const;
export const conversationDetailQueryKey = (conversationId: string) => ["conversations", conversationId] as const;

export function useConversationsQuery() {
  return useQuery({
    queryKey: conversationsQueryKey,
    queryFn: listConversations,
  });
}

export function useConversationQuery(conversationId: string) {
  return useQuery({
    queryKey: conversationDetailQueryKey(conversationId),
    queryFn: () => getConversation(conversationId),
    enabled: Boolean(conversationId),
  });
}

export function useCreateConversationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ConversationTurnRequest) => createConversation(payload),
    onSuccess: (result) => {
      syncConversationMutationResult(queryClient, result);
    },
  });
}

export function useCreateConversationMessageMutation(conversationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ConversationTurnRequest) => createConversationMessage(conversationId, payload),
    onSuccess: (result) => {
      syncConversationMutationResult(queryClient, result);
    },
  });
}

function syncConversationMutationResult(queryClient: ReturnType<typeof useQueryClient>, result: ConversationMutationResponse) {
  queryClient.setQueryData(conversationDetailQueryKey(result.conversation.conversation_id), result.conversation);
  queryClient.setQueryData<ResearchConversationSummary[] | undefined>(conversationsQueryKey, (current) =>
    upsertConversationSummary(current, result.conversation),
  );
  queryClient.setQueryData(runDetailQueryKey(result.run.run_id), result.run);
  queryClient.setQueryData<ResearchRunSummary[] | undefined>(runsQueryKey, (current) => upsertRunSummary(current, result.run));
}
