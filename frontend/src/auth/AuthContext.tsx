import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { ApiError, apiFetch, UNAUTHORIZED_EVENT } from "../api/client";

export interface User {
  id: number;
  email: string;
  name: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // The session cookie is HTTP-only, so asking the backend is the only way to know who's signed in.
    apiFetch<User>("/auth/me")
      .then(setUser)
      .catch((error: unknown) => {
        if (!(error instanceof ApiError && error.status === 401)) console.error(error);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null);
      queryClient.clear();
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, [queryClient]);

  const logout = useCallback(async () => {
    await apiFetch<void>("/auth/logout", { method: "POST" });
    setUser(null);
    queryClient.clear(); // never show one student's cached data to the next
  }, [queryClient]);

  return <AuthContext value={{ user, loading, logout }}>{children}</AuthContext>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
