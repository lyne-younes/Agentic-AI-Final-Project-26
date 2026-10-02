// One stable colour per course, picked by id.
const COURSE_COLORS = ["#38bdf8", "#fb923c", "#22d3ee", "#4ade80", "#818cf8", "#f87171"];

export function courseColor(courseId: number): string {
  return COURSE_COLORS[courseId % COURSE_COLORS.length];
}
