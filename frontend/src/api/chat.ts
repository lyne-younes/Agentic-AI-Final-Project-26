import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, sendJson } from "./client";
import { courseKeys } from "./courses";
import { flashcardKeys } from "./flashcards";
import { leaderboardKeys } from "./leaderboard";
import type { AgentReply, ChatMessage, ChatSession, ChatSource } from "./types";

/** Why a chat was opened, when a page opens it for a quiz attempt. */
export interface ChatOrigin {
  attemptId: number;
  kind: ChatSource;
}

export const chatKeys = {
  sessions: (courseId: number) => ["chat", "sessions", courseId] as const,
  messages: (sessionId: number) => ["chat", "messages", sessionId] as const,
};

export function useChatSessions(courseId: number) {
  return useQuery({
    queryKey: chatKeys.sessions(courseId),
    queryFn: () => apiFetch<ChatSession[]>(`/courses/${courseId}/chat/sessions`),
  });
}

export function useChatMessages(sessionId: number | null) {
  return useQuery({
    queryKey: chatKeys.messages(sessionId ?? -1),
    queryFn: () => apiFetch<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`),
    enabled: sessionId !== null,
  });
}

export function useCreateChatSession(courseId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (origin?: ChatOrigin) =>
      origin
        ? sendJson<ChatSession>(`/courses/${courseId}/chat/sessions`, "POST", {
            source_quiz_attempt_id: origin.attemptId,
            source_kind: origin.kind,
          })
        : apiFetch<ChatSession>(`/courses/${courseId}/chat/sessions`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: chatKeys.sessions(courseId) }),
  });
}

export interface SendMessageInput {
  sessionId: number;
  content: string;
}

/** Sends a message through the agent endpoint, then refetches the history. */
export function useSendMessage(courseId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, content }: SendMessageInput) =>
      sendJson<AgentReply>(`/chat/sessions/${sessionId}/messages`, "POST", { content }),
    onSuccess: (_reply, { sessionId }) =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: chatKeys.messages(sessionId) }),
        queryClient.invalidateQueries({ queryKey: chatKeys.sessions(courseId) }),
        // A turn may have generated a quiz, which joins the leaderboard as unranked.
        queryClient.invalidateQueries({ queryKey: leaderboardKeys.all }),
        // Library cards show the last chat and the quiz/flashcard counts.
        queryClient.invalidateQueries({ queryKey: courseKeys.all, exact: true }),
        // Study Tools lists any newly generated quiz or flashcard set.
        queryClient.invalidateQueries({ queryKey: ["quizzes"] }),
        queryClient.invalidateQueries({ queryKey: flashcardKeys.forCourse(courseId) }),
      ]),
  });
}
