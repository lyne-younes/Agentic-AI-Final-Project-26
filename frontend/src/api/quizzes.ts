import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, sendJson } from "./client";
import { courseKeys } from "./courses";
import { leaderboardKeys } from "./leaderboard";
import type { QuizAnswerInput, QuizAttempt, QuizAttemptResult, QuizDetail, QuizListItem } from "./types";

export const quizKeys = {
  forCourse: (courseId: number) => ["quizzes", "course", courseId] as const,
  detail: (quizId: number) => ["quizzes", quizId] as const,
  attempts: (quizId: number) => ["quizzes", quizId, "attempts"] as const,
  // A graded attempt never changes, so it sits outside the ["quizzes", ...] tree.
  attempt: (attemptId: number) => ["quiz-attempt", attemptId] as const,
};

export function useQuizzes(courseId: number) {
  return useQuery({
    queryKey: quizKeys.forCourse(courseId),
    queryFn: () => apiFetch<QuizListItem[]>(`/courses/${courseId}/quizzes`),
  });
}

export function useQuiz(quizId: number) {
  return useQuery({
    queryKey: quizKeys.detail(quizId),
    queryFn: () => apiFetch<QuizDetail>(`/quizzes/${quizId}`),
  });
}

export function useQuizAttempts(quizId: number) {
  return useQuery({
    queryKey: quizKeys.attempts(quizId),
    queryFn: () => apiFetch<QuizAttempt[]>(`/quizzes/${quizId}/attempts`),
  });
}

/** One past attempt, graded, for review. */
export function useQuizAttempt(quizId: number, attemptId: number | null) {
  return useQuery({
    queryKey: quizKeys.attempt(attemptId ?? -1),
    queryFn: () => apiFetch<QuizAttemptResult>(`/quizzes/${quizId}/attempts/${attemptId}`),
    enabled: attemptId !== null,
    staleTime: Infinity,
  });
}

export function useSubmitQuizAttempt(quizId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (answers: QuizAnswerInput[]) =>
      sendJson<QuizAttemptResult>(`/quizzes/${quizId}/attempts`, "POST", { answers }),
    onSuccess: (result) => {
      // The review page for this attempt opens straight from the response, without a fetch.
      queryClient.setQueryData(quizKeys.attempt(result.id), result);
      return Promise.all([
        queryClient.invalidateQueries({ queryKey: quizKeys.attempts(quizId) }),
        // Study Tools rows show each quiz's best and latest grade.
        queryClient.invalidateQueries({ queryKey: ["quizzes", "course"] }),
        queryClient.invalidateQueries({ queryKey: leaderboardKeys.all }),
        queryClient.invalidateQueries({ queryKey: courseKeys.all, exact: true }),
      ]);
    },
  });
}
