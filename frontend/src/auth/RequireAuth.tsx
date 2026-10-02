import { Navigate, Outlet } from "react-router";
import { useAuth } from "./AuthContext";

/** Layout route guarding every page except /login. */
export function RequireAuth() {
  const { user, loading } = useAuth();

  if (loading) return <div className="page-status">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}
