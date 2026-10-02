import type { CSSProperties } from "react";
import { courseColor } from "../lib/courseColor";

/** The course's own colour in a small dose: a tinted tile with its initial. */
export function CourseIcon({
  courseId,
  name,
  size = "md",
}: {
  courseId: number;
  name: string;
  size?: "sm" | "md";
}) {
  const style = { "--course-color": courseColor(courseId) } as CSSProperties;
  return (
    <span className={`course-icon course-icon-${size}`} style={style} aria-hidden="true">
      {name.trim().charAt(0).toUpperCase() || "?"}
    </span>
  );
}
