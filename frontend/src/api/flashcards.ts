import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { FlashcardSetDetail, FlashcardSetListItem } from "./types";

export const flashcardKeys = {
  forCourse: (courseId: number) => ["flashcard-sets", "course", courseId] as const,
  detail: (setId: number) => ["flashcard-sets", setId] as const,
};

export function useFlashcardSets(courseId: number) {
  return useQuery({
    queryKey: flashcardKeys.forCourse(courseId),
    queryFn: () => apiFetch<FlashcardSetListItem[]>(`/courses/${courseId}/flashcard-sets`),
  });
}

export function useFlashcardSet(setId: number) {
  return useQuery({
    queryKey: flashcardKeys.detail(setId),
    queryFn: () => apiFetch<FlashcardSetDetail>(`/flashcard-sets/${setId}`),
  });
}
