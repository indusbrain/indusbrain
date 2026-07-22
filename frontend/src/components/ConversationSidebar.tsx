import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../lib/api';
import type { ConversationSummary } from '../lib/types';
import { Button, cx, EmptyState } from './ui/primitives';
import { IconChat, IconClose, IconSearch, IconTrash } from './ui/icons';

/**
 * Conversation history panel.
 *
 * Threads are titled from the first question asked, so the list is scannable
 * without the user having to name anything. Search covers message bodies as
 * well as titles, because you usually remember what was said, not what the
 * thread was called.
 */
export const ConversationSidebar: React.FC<{
  activeSessionId: string;
  onSelect: (sessionId: string) => void;
  onNewChat: () => void;
  refreshKey: number;
}> = ({ activeSessionId, onSelect, onNewChat, refreshKey }) => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  // Reference time for date grouping, captured at fetch time (see grouped below).
  const [fetchedAt, setFetchedAt] = useState(() => Date.now());
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState('');

  useEffect(() => {
    let cancelled = false;

    // setLoading is deliberately inside the timer rather than the effect body:
    // calling it synchronously here forces a second render pass on every
    // keystroke while searching.
    const timer = setTimeout(() => {
      if (!cancelled) setLoading(true);
      api
        .conversations(search)
        .then((result) => {
          if (!cancelled) {
            setConversations(result);
            setFetchedAt(Date.now());
          }
        })
        .catch(() => {
          if (!cancelled) setConversations([]);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, search ? 250 : 0); // debounce typing, but load immediately otherwise

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [search, refreshKey]);

  const remove = async (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setConversations((prev) => prev.filter((c) => c.session_id !== sessionId));
    try {
      await api.deleteConversation(sessionId);
      if (sessionId === activeSessionId) onNewChat();
    } catch {
      /* the list refreshes on the next poll if this failed */
    }
  };

  const commitRename = async (sessionId: string) => {
    const title = draftTitle.trim();
    setRenaming(null);
    if (!title) return;
    setConversations((prev) =>
      prev.map((c) => (c.session_id === sessionId ? { ...c, title } : c)),
    );
    try {
      await api.renameConversation(sessionId, title);
    } catch {
      /* optimistic; corrected on next load */
    }
  };

  const grouped = useMemo(() => {
    // The reference time is captured when the list was fetched, not read during
    // render. Calling Date.now() inside render makes the component impure: the
    // same props could produce different output on a re-render.
    const now = fetchedAt;
    const buckets: Record<string, ConversationSummary[]> = { Today: [], 'Last 7 days': [], Earlier: [] };
    conversations.forEach((c) => {
      const updated = c.updated_at ? new Date(c.updated_at).getTime() : 0;
      const ageDays = (now - updated) / 86_400_000;
      if (ageDays < 1) buckets.Today.push(c);
      else if (ageDays < 7) buckets['Last 7 days'].push(c);
      else buckets.Earlier.push(c);
    });
    return Object.entries(buckets).filter(([, items]) => items.length > 0);
  }, [conversations, fetchedAt]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--color-line-subtle)] p-3">
        <Button variant="primary" className="mb-2.5 w-full" onClick={onNewChat}>
          <IconChat size={15} />
          New conversation
        </Button>

        <div className="relative">
          <IconSearch
            size={14}
            className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-[var(--color-ink-faint)]"
          />
          <label htmlFor="conversation-search" className="sr-only">
            Search conversations
          </label>
          <input
            id="conversation-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search conversations…"
            className="w-full rounded-lg border border-[var(--color-line-default)] bg-[var(--color-surface-base)] py-1.5 pr-7 pl-8 text-[12.5px] text-[var(--color-ink-primary)] placeholder:text-[var(--color-ink-faint)] focus:border-[var(--color-accent)]"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              aria-label="Clear search"
              className="absolute top-1/2 right-2 -translate-y-1/2 text-[var(--color-ink-faint)] hover:text-[var(--color-ink-primary)]"
            >
              <IconClose size={12} />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {loading && conversations.length === 0 ? (
          <p className="px-2 py-4 text-[12.5px] text-[var(--color-ink-faint)]">Loading…</p>
        ) : conversations.length === 0 ? (
          <EmptyState
            compact
            title={search ? 'No matches' : 'No conversations yet'}
            description={
              search
                ? 'Try a different search term.'
                : 'Your chats appear here once you ask a question.'
            }
          />
        ) : (
          grouped.map(([bucket, items]) => (
            <div key={bucket} className="mb-3">
              <p className="mb-1 px-2 text-[11px] font-semibold tracking-wide text-[var(--color-ink-faint)] uppercase">
                {bucket}
              </p>
              <ul className="space-y-0.5">
                {items.map((conversation) => {
                  const isActive = conversation.session_id === activeSessionId;
                  return (
                    <li key={conversation.session_id}>
                      <div
                        role="button"
                        tabIndex={0}
                        onClick={() => onSelect(conversation.session_id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') onSelect(conversation.session_id);
                        }}
                        onDoubleClick={() => {
                          setRenaming(conversation.session_id);
                          setDraftTitle(conversation.title);
                        }}
                        className={cx(
                          'group flex cursor-pointer items-start gap-2 rounded-lg px-2 py-2 transition-colors',
                          isActive
                            ? 'bg-[var(--color-accent-soft)]'
                            : 'hover:bg-[var(--color-surface-overlay)]',
                        )}
                      >
                        <div className="min-w-0 flex-1">
                          {renaming === conversation.session_id ? (
                            <input
                              autoFocus
                              value={draftTitle}
                              onChange={(e) => setDraftTitle(e.target.value)}
                              onBlur={() => commitRename(conversation.session_id)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') commitRename(conversation.session_id);
                                if (e.key === 'Escape') setRenaming(null);
                              }}
                              onClick={(e) => e.stopPropagation()}
                              className="w-full rounded border border-[var(--color-accent)] bg-[var(--color-surface-base)] px-1.5 py-0.5 text-[12.5px] text-[var(--color-ink-primary)]"
                            />
                          ) : (
                            <p
                              className={cx(
                                'truncate text-[12.5px]',
                                isActive
                                  ? 'font-medium text-[var(--color-ink-primary)]'
                                  : 'text-[var(--color-ink-secondary)]',
                              )}
                              title={`${conversation.title}\n\nDouble-click to rename`}
                            >
                              {conversation.title}
                            </p>
                          )}
                          {conversation.last_preview && renaming !== conversation.session_id && (
                            <p className="mt-0.5 truncate text-[11.5px] text-[var(--color-ink-faint)]">
                              {conversation.last_preview}
                            </p>
                          )}
                        </div>

                        <button
                          onClick={(event) => remove(conversation.session_id, event)}
                          aria-label={`Delete ${conversation.title}`}
                          className="shrink-0 rounded p-1 text-[var(--color-ink-faint)] opacity-0 transition-opacity group-hover:opacity-100 hover:text-[var(--color-danger)] focus:opacity-100"
                        >
                          <IconTrash size={13} />
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
