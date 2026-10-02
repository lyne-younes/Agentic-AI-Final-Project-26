import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chatKeys } from "./chat";
import { apiFetch, sendJson } from "./client";
import type { AgentReply, ChatSession } from "./types";

/**
 * Study Planner chats are global, so they have their own endpoints. Messages use the same agent
 * endpoint as course chats (hence `chatKeys.messages`).
 */
export const plannerKeys = {
  sessions: ["planner", "sessions"] as const,
};

export function usePlannerSessions() {
  return useQuery({
    queryKey: plannerKeys.sessions,
    queryFn: () => apiFetch<ChatSession[]>("/planner/sessions"),
  });
}

export function useCreatePlannerSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<ChatSession>("/planner/sessions", { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: plannerKeys.sessions }),
  });
}

export function useSendPlannerMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, content }: { sessionId: number; content: string }) =>
      sendJson<AgentReply>(`/chat/sessions/${sessionId}/messages`, "POST", { content }),
    onSuccess: (_reply, { sessionId }) =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: chatKeys.messages(sessionId) }),
        queryClient.invalidateQueries({ queryKey: plannerKeys.sessions }),
      ]),
  });
}
