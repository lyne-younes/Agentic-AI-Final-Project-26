import { GraduationCap } from "lucide-react";
import { Navigate, useSearchParams } from "react-router";
import { LOGIN_URL } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import "./LoginPage.css";

// Error codes set by the backend's /auth/callback redirect.
const ERROR_MESSAGES: Record<string, string> = {
  oauth_failed: "Sign-in with Google didn't complete. Please try again.",
  calendar_access_required:
    "Study Assistant needs access to your Google Calendar to plan study sessions. " +
    "Please sign in again and allow Calendar access.",
};

function GoogleLogo() {
  return (
    <span className="google-logo" aria-hidden="true">
      <svg viewBox="0 0 48 48" width="18" height="18">
        <path
          fill="#FFC107"
          d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.2-.1-2.4-.4-3.5z"
        />
        <path
          fill="#FF3D00"
          d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"
        />
        <path
          fill="#4CAF50"
          d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z"
        />
        <path
          fill="#1976D2"
          d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 38.2 44 33 44 24c0-1.2-.1-2.4-.4-3.5z"
        />
      </svg>
    </span>
  );
}

export function LoginPage() {
  const { user, loading } = useAuth();
  const [searchParams] = useSearchParams();

  if (loading) return <div className="page-status">Loading…</div>;
  if (user) return <Navigate to="/courses" replace />;

  const error = searchParams.get("error");

  return (
    <div className="login-page">
      <div className="login-card">
        <span className="brand-mark login-mark">
          <GraduationCap size={28} />
        </span>
        <h1 className="serif">Study Assistant</h1>
        <p className="text-muted">
          Turn your course materials into answers, summaries, quizzes and study plans.
        </p>
        {error && (
          <p className="form-error" role="alert">
            {ERROR_MESSAGES[error] ?? ERROR_MESSAGES.oauth_failed}
          </p>
        )}
        <a className="btn btn-primary btn-lg login-button" href={LOGIN_URL}>
          <GoogleLogo />
          Sign in with Google
        </a>
        <p className="login-footnote">
          Google will also ask for Calendar access, so the study planner can find free time and add
          study sessions for you.
        </p>
      </div>
    </div>
  );
}
