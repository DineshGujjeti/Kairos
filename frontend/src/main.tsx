import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ToastProvider } from "./components/Toast";
import "./index.css";

// ── Zustand storage migration ─────────────────────────────────────
// Earlier builds persisted a different store shape (accessToken instead
// of token).  If the localStorage entry has the old shape, wipe it so
// Zustand starts fresh and the user is prompted to log in again rather
// than being stuck in a permanently broken state.
try {
  const raw = localStorage.getItem("kairos-auth");
  if (raw) {
    const parsed = JSON.parse(raw);
    const state = parsed?.state ?? parsed;
    // Old shape had `accessToken`; new shape has `token`.
    if ("accessToken" in state && !("token" in state)) {
      localStorage.removeItem("kairos-auth");
      localStorage.removeItem("kairos_token");
    }
  }
} catch {
  // Malformed JSON — clear to be safe
  localStorage.removeItem("kairos-auth");
  localStorage.removeItem("kairos_token");
}

// ── QueryClient ───────────────────────────────────────────────────
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // Never throw to the global boundary — let each page handle errors
      throwOnError: false,
    },
    mutations: {
      throwOnError: false,
    },
  },
});

// ── React root ────────────────────────────────────────────────────
const root = document.getElementById("root");
if (!root) throw new Error("Root element #root not found in index.html");

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    {/* Outermost -- catches render-time crashes anywhere below,
        completely outside BrowserRouter/App's own Suspense+auth-guard
        structure so it can never interfere with that routing logic. */}
    <ErrorBoundary>
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <App />
          </ToastProvider>
        </QueryClientProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
);
