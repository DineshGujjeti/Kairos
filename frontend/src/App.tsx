import { lazy, Suspense } from "react";
import { Route, Routes, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { PageLoading } from "@/components/ui/loading";
import { useAuthStore } from "@/store/auth";

// ── Lazy page imports ──────────────────────────────────────────────
const LoginPage    = lazy(() => import("@/features/auth/LoginPage"));
const RegisterPage = lazy(() => import("@/features/auth/RegisterPage"));

const DashboardPage  = lazy(() => import("@/features/dashboard/DashboardPage"));
const DatasetsPage   = lazy(() => import("@/features/datasets/DatasetsPage"));
const EdaPage        = lazy(() => import("@/features/eda/EdaPage"));
const KpiPage        = lazy(() => import("@/features/kpi/KpiPage"));
const ForecastPage   = lazy(() => import("@/features/forecasting/ForecastPage"));
const RootCausePage  = lazy(() => import("@/features/ai/RootCausePage"));
const SimulationPage = lazy(() => import("@/features/simulation/SimulationPage"));
const DecisionPage   = lazy(() => import("@/features/decision/DecisionPage"));
const ExecutivePage  = lazy(() => import("@/features/decision/ExecutivePage"));
const HistoryPage    = lazy(() => import("@/features/decision/HistoryPage"));
const SettingsPage   = lazy(() => import("@/features/settings/SettingsPage"));

// ── Auth guard ────────────────────────────────────────────────────
// Must render OUTSIDE any Suspense boundary so the guard always runs
// synchronously — Suspense inside the guard used to cause the blank
// screen on first navigation after login.
function RequireAuth({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

// ── Route-level Suspense wrapper ──────────────────────────────────
// Placed INSIDE the guard so the fallback is only shown when the
// user is already authenticated (never on the redirect path).
function PageWrap({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<PageLoading />}>{children}</Suspense>;
}

// ── App ───────────────────────────────────────────────────────────
export default function App() {
  return (
    // Top-level Suspense catches the initial lazy load of auth pages
    // before RequireAuth has a chance to run.
    <Suspense fallback={<PageLoading />}>
      <Routes>
        {/* ── Public routes ──────────────────────────────────── */}
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* ── Protected routes ───────────────────────────────── */}
        {/*
          AppLayout renders the sidebar + <Outlet />.
          RequireAuth wraps AppLayout so unauthenticated users are
          redirected before AppLayout (and any child Suspense) mounts.
          Each child page is individually wrapped in PageWrap so the
          sidebar stays visible while the page chunk loads.
        */}
        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route path="/"            element={<PageWrap><DashboardPage /></PageWrap>} />
          <Route path="/datasets"    element={<PageWrap><DatasetsPage /></PageWrap>} />
          <Route path="/eda"         element={<PageWrap><EdaPage /></PageWrap>} />
          <Route path="/kpi"         element={<PageWrap><KpiPage /></PageWrap>} />
          <Route path="/forecasting" element={<PageWrap><ForecastPage /></PageWrap>} />
          <Route path="/root-cause"  element={<PageWrap><RootCausePage /></PageWrap>} />
          <Route path="/simulation"  element={<PageWrap><SimulationPage /></PageWrap>} />
          <Route path="/decision"    element={<PageWrap><DecisionPage /></PageWrap>} />
          <Route path="/executive"   element={<PageWrap><ExecutivePage /></PageWrap>} />
          <Route path="/history"     element={<PageWrap><HistoryPage /></PageWrap>} />
          <Route path="/settings"    element={<PageWrap><SettingsPage /></PageWrap>} />
          {/* Catch-all → dashboard */}
          <Route path="*"            element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
