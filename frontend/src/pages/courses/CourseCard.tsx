import {
  FileText,
  Layers,
  LoaderCircle,
  MessageSquare,
  SquareStack,
  TriangleAlert,
  Trophy,
} from "lucide-react";
import type { CSSProperties } from "react";
import { Link } from "react-router";
import type { CourseListItem } from "../../api/types";
import { courseColor } from "../../lib/courseColor";
import { CourseIcon } from "../../components/CourseIcon";
import { Menu } from "../../components/ui/Menu";
import { formatRelative, pluralize } from "../../lib/format";
import { useCourseActions } from "./useCourseActions";

interface CourseCardProps {
  course: CourseListItem;
  bestScore: number | null; // best quiz score in this course, from the leaderboard
}

/** A library card. The title link covers the card; the other controls sit above it. */
export function CourseCard({ course, bestScore }: CourseCardProps) {
  const actions = useCourseActions(course);
  const base = `/courses/${course.id}`;
  const completed = course.status === "completed";
  const style = { "--course-color": courseColor(course.id) } as CSSProperties;
  const chatPath = course.last_chat_session_id
    ? `${base}/chat/${course.last_chat_session_id}`
    : `${base}/chat`;

  return (
    <article className={`course-card${completed ? " course-card-completed" : ""}`} style={style}>
      <div className="course-card-head">
        <CourseIcon courseId={course.id} name={course.name} />
        <div className="course-card-heading">
          <h2 className="course-card-title">
            <Link to={`${base}/materials`} className="course-card-link">
              {course.name}
            </Link>
          </h2>
          <p className="course-card-meta">
            {course.semester} {course.year}
            {completed && <span className="badge">Completed</span>}
          </p>
        </div>
        <div className="course-card-raised">
          <Menu label={`Actions for ${course.name}`} items={actions.items} />
        </div>
      </div>

      {course.description && <p className="course-card-description">{course.description}</p>}

      {course.material_count === 0 ? (
        <p className="course-card-hint">No materials yet. Add some so the assistant can help.</p>
      ) : (
        <ul className="course-card-stats" aria-label="Course contents">
          <li>
            <FileText size={14} aria-hidden="true" />
            {pluralize(course.material_count, "material")}
          </li>
          <li>
            <Layers size={14} aria-hidden="true" />
            {course.quiz_count} {course.quiz_count === 1 ? "quiz" : "quizzes"}
          </li>
          <li>
            <SquareStack size={14} aria-hidden="true" />
            {pluralize(course.flashcard_set_count, "flashcard set")}
          </li>
          {bestScore !== null && (
            <li>
              <Trophy size={14} aria-hidden="true" />
              Best {Math.round(bestScore)}%
            </li>
          )}
        </ul>
      )}

      {course.materials_failed > 0 && (
        <Link to={`${base}/materials`} className="course-card-alert course-card-alert-danger">
          <TriangleAlert size={14} aria-hidden="true" />
          {pluralize(course.materials_failed, "material")} failed to index · Fix
        </Link>
      )}
      {course.materials_pending > 0 && (
        <p className="course-card-alert" role="status">
          <LoaderCircle size={14} className="spin" aria-hidden="true" />
          Indexing {pluralize(course.materials_pending, "material")}…
        </p>
      )}
      {actions.error && (
        <p className="form-error course-card-raised" role="alert">
          {actions.error}
        </p>
      )}

      <footer className="course-card-footer">
        <span className="course-card-activity">
          {course.last_activity_at
            ? `Active ${formatRelative(course.last_activity_at)}`
            : `Created ${formatRelative(course.created_at)}`}
        </span>
        <div className="course-card-shortcuts course-card-raised">
          <Link
            to={chatPath}
            className="btn btn-sm btn-ghost"
            title={course.last_chat_session_id ? "Resume your latest chat" : "Start a chat"}
          >
            <MessageSquare size={15} />
            Chat
          </Link>
          <Link to={`${base}/study-tools`} className="btn btn-sm btn-ghost">
            <Layers size={15} />
            Study
          </Link>
        </div>
      </footer>

      {actions.dialogs}
    </article>
  );
}
