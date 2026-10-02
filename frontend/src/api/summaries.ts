import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, sendJson } from "./client";
import type { Summary, SummaryHistoryEntry } from "./types";

export const summaryKeys = {
  detail: (courseId: number) => ["summary", courseId] as const,
  history: (courseId: number) => ["summary", courseId, "history"] as const,
};

export function useSummary(courseId: number) {
  return useQuery({
    queryKey: summaryKeys.detail(courseId),
    queryFn: () => apiFetch<Summary>(`/courses/${courseId}/summary`),
  });
}

export function useSummaryHistory(courseId: number) {
  return useQuery({
    queryKey: summaryKeys.history(courseId),
    queryFn: () => apiFetch<SummaryHistoryEntry[]>(`/courses/${courseId}/summary/history`),
  });
}

export function useUpdateSummary(courseId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) =>
      sendJson<Summary>(`/courses/${courseId}/summary`, "PATCH", { content }),
    onSuccess: (summary) => queryClient.setQueryData(summaryKeys.detail(courseId), summary),
  });
}
