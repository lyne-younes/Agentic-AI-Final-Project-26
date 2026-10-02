import { BookOpen, Plus } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router";
import { useCourses } from "../../api/courses";
import { useLeaderboard } from "../../api/leaderboard";
import type { CourseStatus } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState";
import { SegmentedControl } from "../../components/ui/SegmentedControl";
import { ContinueStudying } from "./ContinueStudying";
import { CourseCard } from "./CourseCard";
import { CourseFormModal } from "./CourseFormModal";
import "./courses.css";

export function CoursesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: courses, isPending, error, refetch } = useCourses();
  // Quiz scores for the cards and the "Continue studying" row. Optional: the page works without it.
  const leaderboard = useLeaderboard();
  const [filter, setFilter] = useState<CourseStatus>("active");
  const [creating, setCreating] = useState(false);

  const firstName = user?.name.split(" ")[0];
  const countWith = (status: CourseStatus) =>
    courses?.filter((course) => course.status === status).length ?? 0;
  const visibleCourses = courses?.filter((course) => course.status === filter) ?? [];
  const hasCourses = (courses?.length ?? 0) > 0;
  const bestByCourse = useMemo(() => {
    const best = new Map<number, number>();
    for (const quiz of leaderboard.data ?? []) {
      for (const attempt of quiz.attempts) {
        best.set(quiz.course_id, Math.max(best.get(quiz.course_id) ?? 0, attempt.score));
      }
    }
    return best;
  }, [leaderboard.data]);

  let content: ReactNode;
  if (isPending) {
    content = <CourseGridSkeleton />;
  } else if (error) {
    content = <ErrorState message={error.message} onRetry={() => void refetch()} />;
  } else if (!hasCourses) {
    content = (
      <EmptyState
        icon={<BookOpen size={34} />}
        title="You haven't created any courses yet"
        description="Create a course, then add PDFs, Word documents, text files or your own notes for the assistant to learn from."
        actions={
          <Button variant="primary" size="lg" onClick={() => setCreating(true)}>
            Create a course
          </Button>
        }
      />
    );
  } else if (visibleCourses.length === 0) {
    content = (
      <p className="filter-empty">
        {filter === "completed"
          ? "No completed courses yet. Mark a course as completed from its page when you're done with it."
          : "No active courses. Every course is marked as completed."}
      </p>
    );
  } else {
    content = (
      <div className="course-grid">
        {visibleCourses.map((course) => (
          <CourseCard
            key={course.id}
            course={course}
            bestScore={bestByCourse.get(course.id) ?? null}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">{firstName ? `Welcome back, ${firstName}` : "Welcome back"}</p>
          <h1 className="page-title">My Library</h1>
        </div>
        {hasCourses && (
          <div className="page-header-actions">
            <SegmentedControl
              label="Show courses"
              value={filter}
              onChange={setFilter}
              options={[
                { value: "active", label: `Active · ${countWith("active")}` },
                { value: "completed", label: `Completed · ${countWith("completed")}` },
              ]}
            />
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus size={16} />
              New course
            </Button>
          </div>
        )}
      </header>

      {courses && hasCourses && leaderboard.data && (
        <ContinueStudying courses={courses} quizzes={leaderboard.data} />
      )}

      {content}

      <CourseFormModal
        open={creating}
        onClose={() => setCreating(false)}
        onSaved={(course) => navigate(`/courses/${course.id}/materials`)}
      />
    </div>
  );
}

function CourseGridSkeleton() {
  return (
    <div className="course-grid" aria-busy="true" aria-label="Loading courses">
      {[0, 1, 2].map((index) => (
        <div key={index} className="course-card course-card-skeleton">
          <div className="course-card-head">
            <div className="skeleton course-icon" />
            <div className="course-card-heading">
              <div className="skeleton" style={{ height: 18, width: "70%" }} />
              <div className="skeleton" style={{ height: 14, width: "40%", marginTop: 6 }} />
            </div>
          </div>
          <div className="skeleton" style={{ height: 14, width: "85%" }} />
          <div className="skeleton" style={{ height: 32, width: "100%" }} />
        </div>
      ))}
    </div>
  );
}
