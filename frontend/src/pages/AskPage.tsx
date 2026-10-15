import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Markdown from 'markdown-to-jsx';
import { api, ApiError } from '../lib/api';
import type { DashboardPayload, QueryResponse } from '../lib/types';
import { PageBody, PageHeader } from '../components/AppShell';
import { EvidencePanel, ConfidenceReadout } from '../components/EvidencePanel';
import { ConversationSidebar } from '../components/ConversationSidebar';
import { ThinkingIndicator, type PipelineStage } from '../components/ThinkingIndicator';
import { ChatLanding } from '../components/ChatLanding';
import { Button, Card, cx, ErrorNotice } from '../components/ui/primitives';
import { IconChevron, IconClose, IconSend, IconTrash } from '../components/ui/icons';

interface ChatMessage {
  id: string;
  role: 'operator' | 'agent';
  text: string;
  payload?: QueryResponse;
  error?: string;
  streaming?: boolean;
}

const SESSION_STORAGE_KEY = 'indusbrain.session';

function loadSessionId(): string {
  const existing = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) return existing;
  const created = crypto.randomUUID();
  window.localStorage.setItem(SESSION_STORAGE_KEY, created);
  return created;
}

export const AskPage: React.FC<{
  dashboard: DashboardPayload | null;
  onDataChanged: () => void;
}> = ({ dashboard, onDataChanged }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [engineMode, setEngineMode] = useState<'LOCAL' | 'FALLBACK'>('LOCAL');
  const [useStreaming, setUseStreaming] = useState(true);
  const [busy, setBusy] = useState(false);
  const [statusText, setStatusText] = useState<string | null>(null);
  const [stage, setStage] = useState<PipelineStage>('supervisor');
  const [elapsed, setElapsed] = useState(0);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [sessionId, setSessionId] = useState<string>(loadSessionId);
  const [historyKey, setHistoryKey] = useState(0);
  const [showHistory, setShowHistory] = useState(true);
  const [searchParams, setSearchParams] = useSearchParams();

  // Switch to an existing thread: its stored messages (and their evidence) load
  // via the history effect below.
  const openConversation = (nextSessionId: string) => {
    window.localStorage.setItem(SESSION_STORAGE_KEY, nextSessionId);
    setSessionId(nextSessionId);
    setMessages([]);
    setExpanded(new Set());
  };

  const startNewConversation = () => {
    const fresh = crypto.randomUUID();
    window.localStorage.setItem(SESSION_STORAGE_KEY, fresh);
    setSessionId(fresh);
    setMessages([]);
    setExpanded(new Set());
  };

  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Restore prior conversation so a refresh does not lose context.
  useEffect(() => {
    let cancelled = false;
    api
      .history(sessionId)
      .then((history) => {
        if (cancelled || history.messages.length === 0) return;
        setMessages(
          history.messages.map((message) => ({
            id: `stored-${message.id}`,
            role: message.sender,
            text: message.content,
            // Rehydrate the stored audit payload so restored answers keep their
            // sources. Without this, reloading the page silently stripped every
            // citation from earlier answers.
            payload: message.evidence
              ? ({ ...message.evidence, session_id: history.session_id } as QueryResponse)
              : undefined,
          })),
        );
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const scrollToBottom = useCallback(() => {
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, []);

  // Follow the conversation as it grows. Skipped while the landing is showing,
  // otherwise opening the page would scroll past the headline to the bottom.
  useEffect(() => {
    if (messages.length > 0) scrollToBottom();
  }, [messages, statusText, scrollToBottom]);

  // Elapsed counter while a request is in flight. Local inference can take over a
  // minute, and seeing the seconds tick up is what tells the user the app is
  // working rather than hung.
  useEffect(() => {
    if (!busy) return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [busy]);

  const toggleExpanded = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const askQuestion = async (question: string, sessionOverride?: string) => {
    const trimmed = question.trim();
    if (!trimmed || busy) return;

    // A directed question (e.g. from the Conflicts page) opens its own thread, so
    // the analysis is not buried at the bottom of an unrelated conversation.
    const targetSession = sessionOverride ?? sessionId;

    // crypto.randomUUID() rather than Date.now(): two messages created in the
    // same millisecond would otherwise collide on their React key.
    const turnId = crypto.randomUUID();
    const operatorId = `op-${turnId}`;
    const agentId = `ag-${turnId}`;

    setMessages((prev) => [
      ...prev,
      { id: operatorId, role: 'operator', text: trimmed },
      { id: agentId, role: 'agent', text: '', streaming: true },
    ]);
    setInput('');
    setBusy(true);
    setStatusText('Classifying the question…');
    setStage('supervisor');
    setElapsed(0);

    const controller = new AbortController();
    abortRef.current = controller;

    const finish = (updater: (message: ChatMessage) => ChatMessage) => {
      setMessages((prev) => prev.map((m) => (m.id === agentId ? updater(m) : m)));
    };

    try {
      if (useStreaming) {
        let accumulated = '';
        await api.streamQuery(
          trimmed,
          engineMode,
          targetSession,
          {
            onSession: (id) => {
              setSessionId(id);
              window.localStorage.setItem(SESSION_STORAGE_KEY, id);
            },
            onStatus: (message, stageId) => {
              setStatusText(message);
              if (stageId) setStage(stageId as PipelineStage);
            },
            onMetadata: (payload) => {
              finish((m) => ({ ...m, payload }));
              setStatusText('Composing answer…');
              setStage('reasoning');
            },
            onToken: (text) => {
              accumulated += text;
              finish((m) => ({ ...m, text: accumulated }));
            },
            onDone: () => finish((m) => ({ ...m, streaming: false, text: accumulated.trim() })),
            onError: (message) => finish((m) => ({ ...m, streaming: false, error: message })),
          },
          controller.signal,
        );
        finish((m) => ({ ...m, streaming: false }));
      } else {
        const payload = await api.submitQuery(trimmed, engineMode, targetSession);
        setSessionId(payload.session_id);
        window.localStorage.setItem(SESSION_STORAGE_KEY, payload.session_id);
        finish((m) => ({ ...m, text: payload.response, payload, streaming: false }));
      }
      onDataChanged();
      // Refresh the thread list so a new conversation appears immediately and an
      // existing one moves to the top with its updated preview.
      setHistoryKey((key) => key + 1);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Something went wrong sending your question.';
      finish((m) => ({ ...m, streaming: false, error: message }));
    } finally {
      setBusy(false);
      setStatusText(null);
      abortRef.current = null;
    }
  };

  // ---------------------------------------------------------------------------
  // DIRECTED QUESTIONS
  //
  // Other pages link here with ?q=<question> — for example "Ask IndusBrain about
  // this conflict". Those links previously navigated but the question was
  // silently dropped, because nothing read the parameter.
  //
  // The question now opens its own thread and sends automatically, so the user
  // never copies anything by hand. The parameter is cleared afterwards so a
  // refresh does not re-ask it.
  // ---------------------------------------------------------------------------
  const autoSentRef = useRef<string | null>(null);

  useEffect(() => {
    const directedQuestion = searchParams.get('q');
    if (!directedQuestion || autoSentRef.current === directedQuestion) return;

    autoSentRef.current = directedQuestion;

    const freshSession = crypto.randomUUID();
    window.localStorage.setItem(SESSION_STORAGE_KEY, freshSession);
    setSessionId(freshSession);
    setMessages([]);
    setExpanded(new Set());

    // Send immediately, passing the new session explicitly so it does not depend
    // on the setSessionId above having been applied yet.
    //
    // NOT wrapped in a timeout with a cleanup: clearing the URL parameter below
    // re-runs this effect, and the cleanup would then cancel our own pending
    // send. The ref guard above is what prevents duplicate sends.
    void askQuestion(directedQuestion, freshSession);

    // Clear the parameter so refreshing the page does not re-ask the question.
    setSearchParams({}, { replace: true });
    // askQuestion is intentionally omitted: it is recreated every render, and
    // including it would re-fire this effect continuously.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, setSearchParams]);

  const stopGeneration = () => {
    abortRef.current?.abort();
    setBusy(false);
    setStatusText(null);
    setMessages((prev) => prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)));
  };

  const clearConversation = async () => {
    try {
      await api.purgeSession(sessionId);
    } catch {
      /* clearing the display matters more than the server call succeeding */
    }
    const fresh = crypto.randomUUID();
    window.localStorage.setItem(SESSION_STORAGE_KEY, fresh);
    setSessionId(fresh);
    setMessages([]);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      askQuestion(input);
    }
  };


  return (
    <PageBody>
      <PageHeader
        title="Ask IndusBrain"
        description="Answers are grounded in your indexed documents. Every claim can be traced to its source."
        actions={
          <>
            {/* Engine selector */}
            <div
              className="btn-glass flex items-center rounded-[var(--radius-control)] p-0.5"
              role="radiogroup"
              aria-label="Reasoning engine"
            >
              {(
                [
                  ['LOCAL', 'AI reasoning', 'Runs the local language model over retrieved passages'],
                  ['FALLBACK', 'Retrieval only', 'Returns matching passages verbatim with no model inference'],
                ] as const
              ).map(([value, label, hint]) => (
                <button
                  key={value}
                  role="radio"
                  aria-checked={engineMode === value}
                  title={hint}
                  onClick={() => setEngineMode(value)}
                  className={cx(
                    'pressable rounded-[4px] px-2.5 py-1.5 text-[12.5px]',
                    engineMode === value
                      ? 'bg-[var(--color-ink-primary)] font-semibold text-[var(--color-surface-raised)]'
                      : 'text-[var(--color-ink-muted)] hover:text-[var(--color-ink-primary)]',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setUseStreaming((v) => !v)}
              title="Stream the answer token by token, or wait for the complete response"
            >
              {useStreaming ? 'Streaming on' : 'Streaming off'}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowHistory((v) => !v)}
              className="hidden lg:inline-flex"
              title="Show or hide the conversation list"
            >
              {showHistory ? 'Hide history' : 'Show history'}
            </Button>
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={async () => {
                  await clearConversation();
                  setHistoryKey((key) => key + 1);
                }}
                title="Delete this conversation and start a new one"
              >
                <IconTrash size={14} />
                Clear
              </Button>
            )}
          </>
        }
      />

      <div className="flex h-[calc(100vh-320px)] min-h-[520px] gap-4">
        {/* Conversation history */}
        {showHistory && (
          <Card className="hidden w-[260px] shrink-0 overflow-hidden lg:block">
            <ConversationSidebar
              activeSessionId={sessionId}
              onSelect={openConversation}
              onNewChat={startNewConversation}
              refreshKey={historyKey}
            />
          </Card>
        )}

      <Card className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Conversation */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
          {messages.length === 0 ? (
            // Entirely corpus-driven: empty state when nothing is indexed,
            // generated starters when documents exist. See ChatLanding.
            <ChatLanding dashboard={dashboard} onAsk={(question) => askQuestion(question)} />
          ) : (
            <div className="space-y-5">
              {messages.map((message) =>
                message.role === 'operator' ? (
                  <div key={message.id} className="flex justify-end">
                    <div className="animate-fade-rise max-w-[85%] rounded-[var(--radius-sheet)] rounded-br-[6px] bg-[var(--color-accent)] px-4 py-2.5 text-[14px] leading-relaxed text-[var(--color-on-accent)]">
                      {message.text}
                    </div>
                  </div>
                ) : (
                  <div key={message.id} className="animate-fade-rise max-w-[92%]">
                    <div className="px-1 py-1">
                      {message.error ? (
                        <ErrorNotice title="Could not complete this request" detail={message.error} />
                      ) : message.text ? (
                        <div className="answer-prose text-[var(--color-ink-secondary)]">
                          <Markdown options={{ forceBlock: true }}>{message.text}</Markdown>
                          {message.streaming && (
                            <span className="animate-caret ml-0.5 inline-block h-3.5 w-1.5 translate-y-0.5 rounded-sm bg-[var(--color-accent)]" />
                          )}
                        </div>
                      ) : (
                        <ThinkingIndicator
                          stage={stage}
                          message={statusText ?? 'Thinking…'}
                          elapsedSeconds={elapsed}
                        />
                      )}
                    </div>

                    {/* Evidence disclosure.
                        Previously this was a blue underlined "View Core Analytics" that looked
                        like a hyperlink but was actually a toggle - and it crashed on open. */}
                    {message.payload && !message.error && (
                      <div className="mt-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <ConfidenceReadout
                            compact
                            score={message.payload.confidence_score}
                            band={message.payload.confidence_band}
                            explanation={message.payload.confidence_explanation}
                          />
                        </div>
                        <button
                          onClick={() => toggleExpanded(message.id)}
                          aria-expanded={expanded.has(message.id)}
                          aria-controls={`evidence-${message.id}`}
                          className="pressable mt-2 flex items-center gap-1.5 rounded-[var(--radius-control)] px-2 py-1 text-[12.5px] font-medium text-[var(--color-ink-muted)] hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-ink-primary)]"
                        >
                          <IconChevron
                            size={14}
                            direction={expanded.has(message.id) ? 'up' : 'down'}
                          />
                          {expanded.has(message.id) ? 'Hide evidence' : 'Show evidence'}
                          <span className="font-[family-name:var(--font-mono)] text-[11.5px] text-[var(--color-ink-muted)]">
                            ({message.payload.citations.length} source
                            {message.payload.citations.length === 1 ? '' : 's'},{' '}
                            {message.payload.decision_replay_path.length} steps)
                          </span>
                        </button>

                        {expanded.has(message.id) && (
                          <div id={`evidence-${message.id}`}>
                            <EvidencePanel
                              citations={message.payload.citations}
                              confidence={message.payload.confidence_metadata}
                              memory={message.payload.organizational_memory}
                              trace={message.payload.decision_replay_path}
                              engine={message.payload.engine}
                              notice={message.payload.notice}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ),
              )}
            </div>
          )}
        </div>

        {/* Composer */}
        <div className="border-t border-[var(--color-line-subtle)] p-3 sm:p-4">
          <div className="flex items-end gap-2">
            <div className="relative flex-1">
              <label htmlFor="question" className="sr-only">
                Your question
              </label>
              <textarea
                id="question"
                ref={textareaRef}
                rows={1}
                value={input}
                onChange={(event) => {
                  setInput(event.target.value);
                  const el = event.target;
                  el.style.height = 'auto';
                  el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
                }}
                onKeyDown={handleKeyDown}
                disabled={busy}
                placeholder="Ask about an asset, procedure, specification or safety requirement…"
                className="btn-glass max-h-40 w-full resize-none rounded-[var(--radius-control)] px-3.5 py-2.5 text-[14px] text-[var(--color-ink-primary)] transition-colors duration-200 placeholder:text-[var(--color-ink-muted)] hover:border-[var(--color-ink-muted)] focus:border-[var(--color-ink-primary)] disabled:opacity-60"
              />
            </div>
            {busy ? (
              <Button variant="secondary" onClick={stopGeneration} className="h-[42px]">
                <IconClose size={14} />
                Stop
              </Button>
            ) : (
              <Button
                variant="primary"
                onClick={() => askQuestion(input)}
                disabled={!input.trim()}
                className="h-[42px]"
              >
                <IconSend size={15} />
                <span className="hidden sm:inline">Send</span>
              </Button>
            )}
          </div>
          <p className="mt-2 text-[12px] text-[var(--color-ink-muted)]">
            {engineMode === 'LOCAL'
              ? 'AI reasoning mode — the local model summarises retrieved passages and flags contradictions.'
              : 'Retrieval-only mode — passages are returned verbatim with no model interpretation.'}
            {' Press Enter to send, Shift+Enter for a new line.'}
          </p>
        </div>
      </Card>
      </div>
    </PageBody>
  );
};
