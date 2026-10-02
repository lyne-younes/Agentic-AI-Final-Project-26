import "@fontsource-variable/inter";
import "@fontsource-variable/source-serif-4";
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { ApiError, UNAUTHORIZED_EVENT } from "./api/client";
import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import "./index.css";
import { ThemeProvider } from "./theme/ThemeProvider";

// An expired session surfaces as a 401 from any request; AuthProvider listens and signs out.
function notifyIfUnauthorized(error: Error) {
  if (error instanceof ApiError && error.status === 401) {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: notifyIfUnauthorized }),
  mutationCache: new MutationCache({ onError: notifyIfUnauthorized }),
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      // Client errors (404, 401, ...) won't fix themselves on retry.
      retry: (failureCount, error) =>
        !(error instanceof ApiError && error.status < 500) && failureCount < 2,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
