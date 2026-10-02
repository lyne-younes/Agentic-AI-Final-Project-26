import { Archive, ArchiveRestore, Pencil, Trash } from "lucide-react";
import { useState } from "react";
import { useDeleteCourse, useUpdateCourse } from "../../api/courses";
import type { Course } from "../../api/types";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import type { MenuItem } from "../../components/ui/Menu";
import { pluralize } from "../../lib/format";
import { CourseFormModal } from "./CourseFormModal";

/**
 * The course "…" menu (edit, mark completed/active, delete), shared by the course page header and
 * the library cards. Render `dialogs` somewhere in the caller; show `error` near the menu.
 */
export function useCourseActions(course: Course, { onDeleted }: { onDeleted?: () => void } = {}) {
  const updateCourse = useUpdateCourse(course.id);
  const deleteCourse = useDeleteCourse(course.id);
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const completed = course.status === "completed";

  const items: MenuItem[] = [
    { label: "Edit course", icon: <Pencil size={16} />, onSelect: () => setEditing(true) },
    completed
      ? {
          label: "Mark as active",
          icon: <ArchiveRestore size={16} />,
          onSelect: () => updateCourse.mutate({ status: "active" }),
        }
      : {
          label: "Mark as completed",
          icon: <Archive size={16} />,
          onSelect: () => updateCourse.mutate({ status: "completed" }),
        },
    {
      label: "Delete course",
      icon: <Trash size={16} />,
      danger: true,
      onSelect: () => setConfirmingDelete(true),
    },
  ];

  const dialogs = (
    <>
      <CourseFormModal open={editing} onClose={() => setEditing(false)} course={course} />
      <ConfirmDialog
        open={confirmingDelete}
        title="Delete this course?"
        message={`"${course.name}" and its ${pluralize(course.material_count, "material")} will be permanently deleted. This can't be undone.`}
        confirmLabel="Delete course"
        loading={deleteCourse.isPending}
        error={deleteCourse.error?.message}
        onClose={() => setConfirmingDelete(false)}
        onConfirm={() =>
          deleteCourse.mutate(undefined, {
            onSuccess: () => {
              setConfirmingDelete(false);
              onDeleted?.();
            },
          })
        }
      />
    </>
  );

  return { items, dialogs, error: updateCourse.error?.message ?? null };
}
