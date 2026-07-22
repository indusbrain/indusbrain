import React, { useCallback, useEffect, useRef, useState } from 'react';
import Markdown from 'markdown-to-jsx';
import { api, ApiError } from '../lib/api';
import type { AssetRecord, QueryResponse } from '../lib/types';
import { PageBody, PageHeader } from '../components/AppShell';
import { EvidencePanel, ConfidenceReadout } from '../components/EvidencePanel';
import { Badge, Button, Card, cx, ErrorNotice } from '../components/ui/primitives';
import { IconChevron, IconClose, IconSend, IconSpark, IconTrash } from '../components/ui/icons';

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

const STARTER_PROMPTS = [
  'What is the maximum discharge pressure for PUMP-101?',
  'Explain the maintenance history of PUMP-101.',
  'Are there conflicting pressure values in the documents?',
  'Which SOP should be followed before startup?',
];

export const AskPage: React.FC<{ assets: AssetRecord[]; onDataChanged: () => void }> = ({
  assets,
  onDataChanged,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [engineMode, setEngineMode] = useState<'LOCAL' | 'FALLBACK'>('LOCAL');
  const [useStreaming, setUseStreaming] = useState(true);
  const [busy, setBusy] = useState(false);
  const [statusText, setStatusText] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [sessionId, setSessionId] = useState<string>(loadSessionId);

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

  useEffect(scrollToBottom, [messages, statusText, scrollToBottom]);

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

  const askQuestion = async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || busy) return;

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
    setStatusText('Searching indexed documents…');

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
          sessionId,
          {
            onSession: (id) => {
              setSessionId(id);
              window.localStorage.setItem(SESSION_STORAGE_KEY, id);
            },
            onStatus: (message) => setStatusText(message),
            onMetadata: (payload) => {
              finish((m) => ({ ...m, payload }));
              setStatusText('Composing answer…');
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
        const payload = await api.submitQuery(trimmed, engineMode, sessionId);
        setSessionId(payload.session_id);
        window.localStorage.setItem(SESSION_STORAGE_KEY, payload.session_id);
        finish((m) => ({ ...m, text: payload.response, payload, streaming: false }));
      }
      onDataChanged();
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

  const assetSuggestions = assets.slice(0, 6);

  return (
    <PageBody>
      <PageHeader
        title="Ask IndusBrain"
        description="Answers are grounded in your indexed documents. Every claim can be traced to its source."
        actions={
          <>
            {/* Engine selector */}
            <div
              className="flex items-center rounded-lg border border-[var(--color-line-default)] bg-[var(--color-surface-overlay)] p-0.5"
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
                    'rounded-md px-2.5 py-1.5 text-[12.5px] transition-colors',
                    engineMode === value
                      ? 'bg-[var(--color-accent)] font-medium text-white'
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
            {messages.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clearConversation} title="Clear this conversation">
                <IconTrash size={14} />
                Clear
              </Button>
            )}
          </>
        }
      />

      <Card className="flex h-[calc(100vh-232px)] min-h-[520px] flex-col overflow-hidden">
        {/* Conversation */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
          {messages.length === 0 ? (
            <div className="mx-auto flex max-w-lg flex-col items-center py-10 text-center">
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--color-accent-soft)]">
                <IconSpark size={20} className="text-[var(--color-accent-hover)]" />
              </div>
              <h2 className="text-[16px] font-semibold text-[var(--color-ink-primary)]">
                Ask about your equipment
              </h2>
              <p className="mt-1.5 text-[13.5px] leading-relaxed text-[var(--color-ink-muted)]">
                I only answer from documents you have indexed. If the answer is not in them, I will
                say so rather than guess.
              </p>

              <div className="mt-6 w-full space-y-2">
                {STARTER_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => askQuestion(prompt)}
                    className="w-full rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-overlay)] px-3.5 py-2.5 text-left text-[13px] text-[var(--color-ink-secondary)] transition-colors hover:border-[var(--color-line-strong)] hover:text-[var(--color-ink-primary)]"
                  >
                    {prompt}
                  </button>
                ))}
              </div>

              {assetSuggestions.length > 0 && (
                <div className="mt-6 w-full">
                  <p className="mb-2 text-[12px] text-[var(--color-ink-faint)]">
                    Assets found in your documents
                  </p>
                  <div className="flex flex-wrap justify-center gap-1.5">
                    {assetSuggestions.map((asset) => (
                      <button key={asset.tag} onClick={() => setInput(`Tell me about ${asset.tag}`)}>
                        <Badge tone="accent" mono>
                          {asset.tag}
                        </Badge>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-5">
              {messages.map((message) =>
                message.role === 'operator' ? (
                  <div key={message.id} className="flex justify-end">
                    <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-[var(--color-accent)] px-4 py-2.5 text-[13.5px] leading-relaxed text-white">
                      {message.text}
                    </div>
                  </div>
                ) : (
                  <div key={message.id} className="animate-fade-rise max-w-[92%]">
                    <div className="rounded-2xl rounded-bl-sm border border-[var(--color-line-subtle)] bg-[var(--color-surface-overlay)] px-4 py-3">
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
                        <div className="flex items-center gap-2 text-[13px] text-[var(--color-ink-muted)]">
                          <span className="animate-caret inline-block h-3.5 w-1.5 rounded-sm bg-[var(--color-accent)]" />
                          {statusText ?? 'Thinking…'}
                        </div>
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
                          className="mt-2 flex items-center gap-1.5 rounded-md px-2 py-1 text-[12.5px] font-medium text-[var(--color-ink-muted)] transition-colors hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-ink-primary)]"
                        >
                          <IconChevron
                            size={14}
                            direction={expanded.has(message.id) ? 'up' : 'down'}
                          />
                          {expanded.has(message.id) ? 'Hide evidence' : 'Show evidence'}
                          <span className="text-[var(--color-ink-faint)]">
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
        <div className="border-t border-[var(--color-line-subtle)] bg-[var(--color-surface-raised)] p-3 sm:p-4">
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
                className="max-h-40 w-full resize-none rounded-lg border border-[var(--color-line-default)] bg-[var(--color-surface-base)] px-3.5 py-2.5 text-[13.5px] text-[var(--color-ink-primary)] placeholder:text-[var(--color-ink-faint)] focus:border-[var(--color-accent)] disabled:opacity-60"
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
          <p className="mt-2 text-[11.5px] text-[var(--color-ink-faint)]">
            {engineMode === 'LOCAL'
              ? 'AI reasoning mode — the local model summarises retrieved passages and flags contradictions.'
              : 'Retrieval-only mode — passages are returned verbatim with no model interpretation.'}
            {' Press Enter to send, Shift+Enter for a new line.'}
          </p>
        </div>
      </Card>
    </PageBody>
  );
};
