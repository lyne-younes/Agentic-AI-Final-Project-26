import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiUrl, sendJson } from "./client";
import { courseKeys } from "./courses";
import type { Material, MaterialDetail, MaterialUpdate } from "./types";

export const materialKeys = {
  forCourse: (courseId: number) => ["materials", "course", courseId] as const,
  detail: (materialId: number) => ["materials", materialId] as const,
};

// Chunking + embedding runs in the background after an upload; poll until it settles.
const INDEXING_POLL_MS = 2000;

export function materialFileUrl(materialId: number): string {
  return apiUrl(`/materials/${materialId}/file`);
}

export function useMaterials(courseId: number) {
  return useQuery({
    queryKey: materialKeys.forCourse(courseId),
    queryFn: () => apiFetch<Material[]>(`/courses/${courseId}/materials`),
    refetchInterval: (query) =>
      query.state.data?.some((material) => material.indexing_status === "pending")
        ? INDEXING_POLL_MS
        : false,
  });
}

export function useMaterial(materialId: number | null) {
  return useQuery({
    queryKey: materialKeys.detail(materialId ?? -1),
    queryFn: () => apiFetch<MaterialDetail>(`/materials/${materialId}`),
    enabled: materialId !== null,
    refetchInterval: (query) =>
      query.state.data?.indexing_status === "pending" ? INDEXING_POLL_MS : false,
  });
}

/** Refresh the course's material list and the course counts that include it. */
function useInvalidateCourseMaterials(courseId: number) {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: materialKeys.forCourse(courseId) }),
      queryClient.invalidateQueries({ queryKey: courseKeys.all }),
    ]);
}

export interface UploadInput {
  file: File;
  title: string;
  tags: string[];
}

export function useUploadMaterial(courseId: number) {
  const invalidate = useInvalidateCourseMaterials(courseId);
  return useMutation({
    mutationFn: ({ file, title, tags }: UploadInput) => {
      const form = new FormData();
      form.append("file", file);
      if (title.trim()) form.append("title", title.trim());
      for (const tag of tags) form.append("tags", tag);
      return apiFetch<Material>(`/courses/${courseId}/materials`, { method: "POST", body: form });
    },
    onSuccess: () => invalidate(),
  });
}

export interface NoteInput {
  title: string;
  content: string;
  tags: string[];
}

export function useCreateNote(courseId: number) {
  const invalidate = useInvalidateCourseMaterials(courseId);
  return useMutation({
    mutationFn: (input: NoteInput) =>
      sendJson<Material>(`/courses/${courseId}/materials/note`, "POST", input),
    onSuccess: () => invalidate(),
  });
}

export function useUpdateMaterial(courseId: number, materialId: number) {
  const queryClient = useQueryClient();
  const invalidate = useInvalidateCourseMaterials(courseId);
  return useMutation({
    mutationFn: (changes: MaterialUpdate) =>
      sendJson<MaterialDetail>(`/materials/${materialId}`, "PATCH", changes),
    onSuccess: (material) => {
      queryClient.setQueryData(materialKeys.detail(materialId), material);
      return invalidate();
    },
  });
}

export function useDeleteMaterial(courseId: number) {
  const invalidate = useInvalidateCourseMaterials(courseId);
  return useMutation({
    mutationFn: (materialId: number) =>
      apiFetch<void>(`/materials/${materialId}`, { method: "DELETE" }),
    onSuccess: () => invalidate(),
  });
}

export function useReindexMaterial(courseId: number) {
  const queryClient = useQueryClient();
  const invalidate = useInvalidateCourseMaterials(courseId);
  return useMutation({
    mutationFn: (materialId: number) =>
      apiFetch<Material>(`/materials/${materialId}/reindex`, { method: "POST" }),
    onSuccess: (_material, materialId) =>
      Promise.all([
        invalidate(),
        queryClient.invalidateQueries({ queryKey: materialKeys.detail(materialId) }),
      ]),
  });
}
