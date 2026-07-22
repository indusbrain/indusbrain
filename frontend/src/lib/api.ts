/**
 * Single API client for the IndusBrain backend.
 *
 * Replaces the two conflicting modules that previously existed: an axios client
 * reading `process.env` (a Node API that is undefined in the browser, so it would
 * have thrown) and a fetch wrapper calling ingestion endpoints (/parse, /chunk,
 * /embed, /graph) that the backend does not implement.
 */

import type {
  ChatHistory,
  ConflictScanResult,
  DashboardPayload,
  IngestionStatus,
  QueryResponse,
  RolesResponse,
  SimulationResult,
  UploadResponse,
} from './types';

// Vite exposes env vars on import.meta.env, not process.env.
const API_ROOT = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');
const API_BASE = `${API_ROOT}/api/v1`;

// ---------------------------------------------------------------------------
// Active role
//
// Every request carries the selected role so the backend can authorise it. The
// server is the authority: if the UI ever shows a control it should not, the API
// still returns 403.
// ---------------------------------------------------------------------------
let activeRole = 'engineer';

export function setActiveRole(role: string): void {
  activeRole = role;
}

export function getActiveRole(): string {
  return activeRole;
}

function withRole(init?: RequestInit): RequestInit {
  const headers = new Headers(init?.headers ?? {});
  headers.set('X-IndusBrain-Role', activeRole);
  return { ...init, headers };
}

export class ApiError extends Error {
  // Declared as fields rather than constructor parameter properties: this project
  // builds with `erasableSyntaxOnly`, which forbids TypeScript-only syntax that
  // emits runtime code.
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = 300_000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...withRole(init),
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail: string | undefined;
      try {
        const body = await response.json();
        detail = body?.detail ?? body?.message;
      } catch {
        detail = undefined;
      }
      throw new ApiError(detail ?? `Request failed (HTTP ${response.status})`, response.status, detail);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The request timed out.', 408);
    }
    throw new ApiError(`Cannot reach the IndusBrain API at ${API_ROOT}. Is the backend running?`, 0);
  } finally {
    clearTimeout(timer);
  }
}

function jsonBody(payload: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  };
}

export const api = {
  apiRoot: API_ROOT,

  roles: () => request<RolesResponse>('/auth/roles', undefined, 20_000),

  dashboard: (refresh = false) =>
    request<DashboardPayload>(
      `/telemetry/dashboard${refresh ? '?refresh=true' : ''}`,
      undefined,
      60_000,
    ),

  scanConflicts: () => request<ConflictScanResult>('/ingestion/scan-conflicts', { method: 'POST' }),

  reindexGraph: () =>
    request<{ status: string; documents_processed: number }>('/ingestion/reindex-graph', {
      method: 'POST',
    }),

  submitQuery: (query: string, routingMode: string, sessionId: string) =>
    request<QueryResponse>(
      '/query/submit',
      jsonBody({ query, routing_mode: routingMode, session_id: sessionId }),
    ),

  history: (sessionId: string) =>
    request<ChatHistory>(`/query/history/${encodeURIComponent(sessionId)}`),

  purgeSession: (sessionId: string) =>
    request<{ status: string; messages_deleted: number }>(
      `/telemetry/session/${encodeURIComponent(sessionId)}`,
      { method: 'DELETE' },
    ),

  simulate: (scenario: string, assetTag: string) =>
    request<SimulationResult>('/simulator/simulate', jsonBody({ scenario, asset_tag: assetTag })),

  ingestionStatus: (documentId: number) =>
    request<IngestionStatus>(`/ingestion/status/${documentId}`, undefined, 30_000),

  deleteDocument: (documentId: number) =>
    request<{ status: string; filename: string; warnings: string[] }>(
      `/telemetry/document/${documentId}`,
      { method: 'DELETE' },
    ),

  async upload(files: File[]): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    return request<UploadResponse>('/ingestion/upload', { method: 'POST', body: formData }, 600_000);
  },

  /**
   * Streams an answer over SSE.
   *
   * Parsed manually because the browser EventSource API cannot issue POST
   * requests. The backend emits named events: session / status / metadata /
   * token / done / error, each carrying a JSON payload.
   */
  async streamQuery(
    query: string,
    routingMode: string,
    sessionId: string,
    handlers: {
      onSession?: (sessionId: string) => void;
      onStatus?: (message: string) => void;
      onMetadata?: (payload: QueryResponse) => void;
      onToken?: (text: string) => void;
      onDone?: () => void;
      onError?: (message: string) => void;
    },
    signal?: AbortSignal,
  ): Promise<void> {
    let response: Response;
    try {
      response = await fetch(`${API_BASE}/query/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-IndusBrain-Role': activeRole,
        },
        body: JSON.stringify({ query, routing_mode: routingMode, session_id: sessionId }),
        signal,
      });
    } catch {
      handlers.onError?.(`Cannot reach the IndusBrain API at ${API_ROOT}.`);
      return;
    }

    if (!response.ok || !response.body) {
      handlers.onError?.(`The server rejected the request (HTTP ${response.status}).`);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';

      for (const frame of frames) {
        let eventName = 'message';
        let dataLine = '';

        for (const line of frame.split('\n')) {
          if (line.startsWith('event:')) eventName = line.slice(6).trim();
          else if (line.startsWith('data:')) dataLine += line.slice(5).trim();
        }
        if (!dataLine) continue;

        let payload: any;
        try {
          payload = JSON.parse(dataLine);
        } catch {
          continue;
        }

        switch (eventName) {
          case 'session':
            handlers.onSession?.(payload.session_id);
            break;
          case 'status':
            handlers.onStatus?.(payload.message);
            break;
          case 'metadata':
            handlers.onMetadata?.(payload as QueryResponse);
            break;
          case 'token':
            handlers.onToken?.(payload.text);
            break;
          case 'done':
            handlers.onDone?.();
            break;
          case 'error':
            handlers.onError?.(payload.message ?? 'Unknown streaming error');
            break;
        }
      }
    }
  },
};
