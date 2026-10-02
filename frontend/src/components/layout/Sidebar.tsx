import {
  CalendarDays,
  GraduationCap,
  Library,
  LogOut,
  Monitor,
  Moon,
  PanelLeftClose,
  Sun,
  Trophy,
} from "lucide-react";
import type { ReactNode, Ref } from "react";
import { Link, NavLink } from "react-router";
import { useCourses } from "../../api/courses";
import { useAuth } from "../../auth/AuthContext";
import { initials } from "../../lib/format";
import { useTheme, type ThemePreference } from "../../theme/ThemeProvider";
import { courseColor } from "../../lib/courseColor";
import { Button } from "../ui/Button";
import { SegmentedControl } from "../ui/SegmentedControl";

export function Brand() {
  return (
    <Link to="/courses" className="brand">
      <span className="brand-mark">
        <GraduationCap size={18} />
      </span>
      <span className="brand-name">Study Assistant</span>
    </Link>
  );
}

const THEME_OPTIONS: { value: ThemePreference; label: ReactNode; ariaLabel: string }[] = [
  { value: "light", label: <Sun size={16} />, ariaLabel: "Light theme" },
  { value: "system", label: <Monitor size={16} />, ariaLabel: "Match system theme" },
  { value: "dark", label: <Moon size={16} />, ariaLabel: "Dark theme" },
];

interface SidebarProps {
  ref?: Ref<HTMLElement>;
  onHide: () => void;
  inert?: boolean; // hidden (wide) or a closed overlay (narrow)
}

export function Sidebar({ ref, onHide, inert }: SidebarProps) {
  const { user, logout } = useAuth();
  const { preference, setPreference } = useTheme();
  const { data: courses } = useCourses();
  const activeCourses = courses?.filter((course) => course.status === "active") ?? [];

  return (
    <aside ref={ref} className="sidebar" inert={inert}>
      <div className="sidebar-header">
        <Brand />
        <Button
          variant="ghost"
          size="sm"
          iconOnly
          className="sidebar-hide"
          aria-label="Hide sidebar"
          title="Hide sidebar (Ctrl+B)"
          onClick={onHide}
        >
          <PanelLeftClose size={18} />
        </Button>
      </div>

      <nav className="sidebar-nav" aria-label="Main">
        <NavLink to="/courses" end className="sidebar-link">
          <span className="nav-icon">
            <Library size={18} />
          </span>
          My Library
        </NavLink>
        <NavLink to="/planner" className="sidebar-link">
          <span className="nav-icon">
            <CalendarDays size={18} />
          </span>
          Study Planner
        </NavLink>
        <NavLink to="/leaderboard" className="sidebar-link">
          <span className="nav-icon">
            <Trophy size={18} />
          </span>
          Leaderboard
        </NavLink>
      </nav>

      <nav className="sidebar-section" aria-label="Active courses">
        <p className="sidebar-heading">Active courses</p>
        {activeCourses.length === 0 ? (
          <p className="sidebar-empty">No active courses yet</p>
        ) : (
          activeCourses.map((course) => (
            <NavLink key={course.id} to={`/courses/${course.id}`} className="sidebar-link">
              <span className="nav-icon">
                <span className="course-dot" style={{ background: courseColor(course.id) }} />
              </span>
              <span className="truncate">{course.name}</span>
            </NavLink>
          ))
        )}
      </nav>

      <div className="sidebar-footer">
        <SegmentedControl
          label="Theme"
          value={preference}
          options={THEME_OPTIONS}
          onChange={setPreference}
          className="theme-switcher"
        />
        <div className="user-row">
          <span className="avatar" aria-hidden="true">
            {initials(user?.name)}
          </span>
          <div className="user-meta">
            <span className="truncate">{user?.name}</span>
            <span className="truncate text-subtle">{user?.email}</span>
          </div>
          <Button
            variant="ghost"
            iconOnly
            aria-label="Sign out"
            title="Sign out"
            onClick={() => void logout()}
          >
            <LogOut size={16} />
          </Button>
        </div>
      </div>
    </aside>
  );
}
