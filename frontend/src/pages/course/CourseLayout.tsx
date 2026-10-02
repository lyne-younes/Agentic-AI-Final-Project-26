import {
  ChevronRight,
  FolderOpen,
  Layers,
  MessageSquare,
  NotepadText,
} from "lucide-react";
import { Link, NavLink, Outlet, useLocation, useNavigate, useParams } from "react-router";
import { ApiError } from "../../api/client";
import { useCourse } from "../../api/courses";
import type { Course } from "../../api/types";
import { CourseIcon } from "../../components/CourseIcon";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState";
import { Menu } from "../../components/ui/Menu";
import { useCourseActions } from "../courses/useCourseActions";
import "./course.css";

// Course areas are sub-routes, shown as a tab bar.
const SECTIONS = [
  { path: "materials", label: "Materials", icon: <FolderOpen size={17} /> },
  { path: "notes", label: "Notes", icon: <NotepadText size={17} /> },
  { path: "study-tools", label: "Study Tools", icon: <Layers size={17} /> },
  { path: "chat", label: "Chat", icon: <MessageSquare size={17} /> },
];

export function CourseLayout() {
  const courseId = Number(useParams().courseId);
  const { data: course, isPending, error, refetch } = useCourse(courseId);

  if (!Number.isInteger(courseId) || (error instanceof ApiError && error.status === 404)) {
    return (
      <EmptyState
        icon={<FolderOpen size={30} />}
        tone="slate"
        title="Course not found"
        description="It may have been deleted, or the link is wrong."
        actions={
          <Link to="/courses" className="btn btn-primary">
            Back to My Library
          </Link>
        }
      />
    );
  }
  if (error) return <ErrorState message={error.message} onRetry={() => void refetch()} />;
  if (isPending) return <CourseHeaderSkeleton />;
  return <CourseView course={course} />;
}

function CourseView({ course }: { course: Course }) {
  const navigate = useNavigate();
  // /courses/:courseId/chat[/:sessionId]: the chat fills the viewport instead of scrolling the page.
  const onChat = useLocation().pathname.split("/")[3] === "chat";
  const actions = useCourseActions(course, {
    onDeleted: () => navigate("/courses", { replace: true }),
  });
  const completed = course.status === "completed";

  return (
    <div className={`page course-page${onChat ? " course-page-chat fill-viewport" : ""}`}>
      <div className="course-top">
        <nav className="breadcrumb" aria-label="Breadcrumb">
          <Link to="/courses">My Library</Link>
          <ChevronRight size={14} aria-hidden="true" />
          <span aria-current="page" className="truncate">
            {course.name}
          </span>
        </nav>

        <header className="course-header">
          <CourseIcon courseId={course.id} name={course.name} />
          <div className="course-title-row">
            <h1 className="page-title course-title">{course.name}</h1>
            <span className="badge">
              {course.semester} {course.year}
            </span>
            <span className={`badge ${completed ? "" : "badge-teal"}`}>
              {completed ? "Completed" : "Active"}
            </span>
          </div>
          <Menu label="Course actions" items={actions.items} />
        </header>
        {/* The description gives way to the conversation on the Chat tab. */}
        {course.description && !onChat && (
          <p className="course-description">{course.description}</p>
        )}
        {actions.error && (
          <p className="form-error" role="alert">
            {actions.error}
          </p>
        )}

        <nav className="tabs" aria-label="Course sections">
          {SECTIONS.map((section) => (
            <NavLink key={section.path} to={section.path} className="tab">
              {section.icon}
              {section.label}
            </NavLink>
          ))}
        </nav>
      </div>

      <Outlet context={course} />

      {actions.dialogs}
    </div>
  );
}

function CourseHeaderSkeleton() {
  return (
    <div className="page course-page" aria-busy="true" aria-label="Loading course">
      <div className="course-top">
        <div className="skeleton" style={{ height: 16, width: 140 }} />
        <div className="course-header">
          <div className="skeleton course-icon" />
          <div className="skeleton" style={{ height: 32, width: "40%" }} />
        </div>
        <div className="skeleton" style={{ height: 44, width: "100%" }} />
      </div>
    </div>
  );
}
