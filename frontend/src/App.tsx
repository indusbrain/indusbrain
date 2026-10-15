import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BrowserRouter, Route, Routes, useLocation } from 'react-router-dom';
import { api, ApiError } from './lib/api';
import type { DashboardPayload } from './lib/types';
import { AppShell } from './components/AppShell';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AuthProvider, useAuth } from './lib/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { RequirePermission } from './components/RequirePermission';
import { OverviewPage } from './pages/OverviewPage';
import { AskPage } from './pages/AskPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { ConflictsPage } from './pages/ConflictsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SimulatorPage } from './pages/SimulatorPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ThemeProvider } from './lib/theme';
import { IntroSequence } from './components/motion/IntroSequence';
import { RouteTransition } from './components/motion/RouteTransition';
import { LogoMark } from './components/brand/Logo';
import { Backdrop } from './components/ui/Backdrop';

/** Routes need the current location so the sheet transition can key on it. */
const AnimatedRoutes: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  return (
    <RouteTransition>
      <Routes location={location}>{children}</Routes>
    </RouteTransition>
  );
};

const POLL_INTERVAL_MS = 15_000;

function AppRoutes() {
  const { requiresLogin, loading: authLoading } = useAuth();
  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const inFlight = useRef(false);

  const loadDashboard = useCallback(async (force = false) => {
    // Guard against overlapping polls, which previously stacked up whenever the
    // backend was slow and every open tab re-scanned the whole corpus.
    if (inFlight.current) return;
    inFlight.current = true;
    if (force) setLoading(true);

    try {
      const payload = await api.dashboard(force);
      setDashboard(payload);
      setConnectionError(null);
    } catch (error) {
      setConnectionError(
        error instanceof ApiError ? error.message : 'The API did not respond.',
      );
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Only poll once signed in. Without this guard every unauthenticated visit
    // fired a dashboard request that could only ever return 401.
    if (requiresLogin) return;

    // Kick the initial fetch off the synchronous effect body. Calling it directly
    // sets the loading flag during mount, forcing an immediate second render.
    // The skeleton UI already covers this window (dashboard is null until data
    // arrives), so nothing is lost visually.
    const initial = setTimeout(() => loadDashboard(true), 0);

    const interval = setInterval(() => {
      // Do not poll while the tab is hidden - it wastes server work and, with the
      // old 4-second interval, meant a backgrounded tab kept re-scanning the corpus.
      if (document.visibilityState === 'visible') loadDashboard(false);
    }, POLL_INTERVAL_MS);

    const onVisible = () => {
      if (document.visibilityState === 'visible') loadDashboard(false);
    };
    document.addEventListener('visibilitychange', onVisible);

    return () => {
      clearTimeout(initial);
      clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [loadDashboard, requiresLogin]);

  const refresh = useCallback(() => loadDashboard(true), [loadDashboard]);

  // Wait for the stored session to be validated before deciding what to show,
  // otherwise a signed-in user briefly sees the login screen on every refresh.
  if (authLoading) {
    return (
      <div data-theme="dark" className="noir flex min-h-screen items-center justify-center">
        <LogoMark size={56} title="Loading IndusBrain" className="text-[#F3F3F5]" />
      </div>
    );
  }

  // Everything behind this point requires a real, server-validated session.
  if (requiresLogin) return <LoginPage />;

  return (
    <BrowserRouter>
      <AppShell dashboard={dashboard} connectionError={connectionError}>
        <ErrorBoundary>
          <AnimatedRoutes>
            <Route
              path="/"
              element={<OverviewPage dashboard={dashboard} loading={loading} onRefresh={refresh} />}
            />
            <Route
              path="/ask"
              element={
                <ErrorBoundary label="chat">
                  <AskPage dashboard={dashboard} onDataChanged={refresh} />
                </ErrorBoundary>
              }
            />
            <Route path="/knowledge" element={<KnowledgePage dashboard={dashboard} />} />
            <Route
              path="/conflicts"
              element={<ConflictsPage dashboard={dashboard} onDataChanged={refresh} />}
            />
            <Route
              path="/analytics"
              element={<AnalyticsPage dashboard={dashboard} loading={loading} onRefresh={refresh} />}
            />
            <Route path="/simulator" element={<SimulatorPage dashboard={dashboard} />} />
            <Route
              path="/documents"
              element={
                <RequirePermission permission="view_documents" area="Documents">
                  <DocumentsPage dashboard={dashboard} onDataChanged={refresh} />
                </RequirePermission>
              }
            />
            {/* Unknown paths get an explained dead end with a way back, instead of
                silently bouncing to the overview. */}
            <Route path="*" element={<NotFoundPage />} />
          </AnimatedRoutes>
        </ErrorBoundary>
      </AppShell>
    </BrowserRouter>
  );
}

// RoleProvider must sit OUTSIDE the router so the role header is configured on
// the API client before any page issues its first request.
function App() {
  return (
    <ThemeProvider>
      {/* One background for the whole app, so route changes never recreate it. */}
      <Backdrop />
      <IntroSequence />
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
