import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, sendJson } from "./client";
import type { Course, CourseInput, CourseListItem, CourseStatus } from "./types";

// ["courses"] is the list; ["courses", id] is one course. Invalidating ["courses"] refreshes both.
export const courseKeys = {
  all: ["courses"] as const,
  detail: (courseId: number) => ["courses", courseId] as const,
};

export function useCourses() {
  return useQuery({
    queryKey: courseKeys.all,
    queryFn: () => apiFetch<CourseListItem[]>("/courses"),
  });
}

export function useCourse(courseId: number) {
  return useQuery({
    queryKey: courseKeys.detail(courseId),
    queryFn: () => apiFetch<Course>(`/courses/${courseId}`),
    enabled: Number.isInteger(courseId),
  });
}

export function useCreateCourse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CourseInput) => sendJson<Course>("/courses", "POST", input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: courseKeys.all }),
  });
}

export function useUpdateCourse(courseId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (changes: Partial<CourseInput> & { status?: CourseStatus }) =>
      sendJson<Course>(`/courses/${courseId}`, "PATCH", changes),
    onSuccess: (course) => {
      queryClient.setQueryData(courseKeys.detail(courseId), course);
      return queryClient.invalidateQueries({ queryKey: courseKeys.all, exact: true });
    },
  });
}

export function useDeleteCourse(courseId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<void>(`/courses/${courseId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: courseKeys.all, exact: true }),
  });
}
