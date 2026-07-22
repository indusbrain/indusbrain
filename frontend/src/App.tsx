import { useCallback, useEffect, useRef, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { api, ApiError } from './lib/api';
import type { DashboardPayload } from './lib/types';
import { AppShell } from './components/AppShell';
import { ErrorBoundary } from './components/ErrorBoundary';
import { RoleProvider } from './lib/RoleContext';
import { RequirePermission } from './components/RequirePermission';
import { OverviewPage } from './pages/OverviewPage';
import { AskPage } from './pages/AskPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { ConflictsPage } from './pages/ConflictsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SimulatorPage } from './pages/SimulatorPage';
import { DocumentsPage } from './pages/DocumentsPage';

const POLL_INTERVAL_MS = 15_000;

function AppRoutes() {
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
  }, [loadDashboard]);

  const refresh = useCallback(() => loadDashboard(true), [loadDashboard]);

  return (
    <BrowserRouter>
      <AppShell dashboard={dashboard} connectionError={connectionError}>
        <ErrorBoundary>
          <Routes>
            <Route
              path="/"
              element={<OverviewPage dashboard={dashboard} loading={loading} onRefresh={refresh} />}
            />
            <Route
              path="/ask"
              element={
                <ErrorBoundary label="chat">
                  <AskPage assets={dashboard?.assets ?? []} onDataChanged={refresh} />
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
                <RequirePermission permission="upload_documents" area="Document management">
                  <DocumentsPage dashboard={dashboard} onDataChanged={refresh} />
                </RequirePermission>
              }
            />
            {/* Any unknown path returns to the overview rather than a blank screen. */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ErrorBoundary>
      </AppShell>
    </BrowserRouter>
  );
}

// RoleProvider must sit OUTSIDE the router so the role header is configured on
// the API client before any page issues its first request.
function App() {
  return (
    <RoleProvider>
      <AppRoutes />
    </RoleProvider>
  );
}

export default App;
