import React, { useEffect, useState } from 'react';
import { api, ApiError } from '../lib/api';
import type { DocumentDetail } from '../lib/types';
import { Badge, Button, cx, ErrorNotice, Skeleton } from './ui/primitives';
import { IconClose, IconDocs, IconSearch, IconUpload } from './ui/icons';

/**
 * In-app document viewer.
 *
 * Two tabs, because they answer different questions:
 *   - Document : the original PDF, rendered inline. What the engineer signed off.
 *   - Passages : the extracted text as IndusBrain actually indexed it. This is
 *                what retrieval searches, so it is the honest way to check why a
 *                document did or did not answer a question.
 *
 * The passage view matters: a PDF can look perfect while its extracted text is
 * empty or garbled, and only the passage view reveals that.
 */
export const DocumentViewer: React.FC<{
  documentId: number;
  onClose: () => void;
}> = ({ documentId, onClose }) => {
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'file' | 'passages'>('file');
  const [search, setSearch] = useState('');

  useEffect(() => {
    let cancelled = false;

    // The reset is inside the fetch chain rather than the effect body: calling
    // setState synchronously here forces an extra render pass on open.
    api
      .documentDetail(documentId)
      .then((result) => {
        if (!cancelled) {
          setDetail(result);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setDetail(null);
          setError(err instanceof ApiError ? err.message : 'Could not load this document.');
        }
      });

    return () => {
      cancelled = true;
    };
  }, [documentId]);

  // Close on Escape, the expected behaviour for a modal.
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const matchingPassages =
    detail?.passages.filter((p) =>
      search.trim() ? p.text.toLowerCase().includes(search.trim().toLowerCase()) : true,
    ) ?? [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <button
        className="absolute inset-0 bg-[#15171B]/60"
        onClick={onClose}
        aria-label="Close document viewer"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label={detail?.filename ?? 'Document'}
        className="animate-fade-rise relative flex h-full max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden glass-strong rounded-[var(--radius-sheet)]"
      >
        {/* Header */}
        <div className="flex items-start gap-3 border-b border-[var(--color-line-subtle)] px-5 py-3.5">
          <IconDocs size={18} className="mt-0.5 shrink-0 text-[var(--color-ink-muted)]" />
          <div className="min-w-0 flex-1">
            <h2 className="truncate font-[family-name:var(--font-mono)] text-[14px] font-medium text-[var(--color-ink-primary)]">
              {detail?.filename ?? 'Loading…'}
            </h2>
            {detail && (
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <Badge tone={detail.status === 'EMBEDDED' ? 'success' : 'warning'}>
                  {detail.status.toLowerCase()}
                </Badge>
                <span className="text-[12px] text-[var(--color-ink-muted)]">
                  {detail.chunk_count} passages · {(detail.file_size / 1024).toFixed(0)} KB
                </span>
                {detail.created_at && (
                  <span className="text-[12px] text-[var(--color-ink-muted)]">
                    indexed {new Date(detail.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {detail?.file_available && (
              <a href={api.documentFileUrl(documentId, true)} download>
                <Button variant="secondary" size="sm">
                  <IconUpload size={14} className="rotate-180" />
                  Download
                </Button>
              </a>
            )}
            <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
              <IconClose size={15} />
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-[var(--color-line-subtle)] px-3" role="tablist">
          {(
            [
              ['file', 'Document'],
              ['passages', `Indexed passages${detail ? ` (${detail.chunk_count})` : ''}`],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              role="tab"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={cx(
                '-mb-px border-b-2 px-3 py-2 text-[13px] transition-colors',
                tab === id
                  ? 'border-[var(--color-accent)] font-medium text-[var(--color-ink-primary)]'
                  : 'border-transparent text-[var(--color-ink-muted)] hover:text-[var(--color-ink-secondary)]',
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="min-h-0 flex-1 overflow-hidden">
          {error ? (
            <div className="p-5">
              <ErrorNotice title="Could not open document" detail={error} />
            </div>
          ) : !detail ? (
            <div className="space-y-3 p-5">
              <Skeleton className="h-6 w-1/3" />
              <Skeleton className="h-[420px]" />
            </div>
          ) : tab === 'file' ? (
            detail.file_available ? (
              // The browser's built-in PDF renderer. No JS PDF library is pulled
              // in: it would add ~1 MB to the bundle for something every target
              // browser already does natively.
              <object
                data={api.documentFileUrl(documentId)}
                type="application/pdf"
                className="h-full w-full"
                aria-label={`PDF preview of ${detail.filename}`}
              >
                <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
                  <p className="text-[13.5px] text-[var(--color-ink-secondary)]">
                    Your browser cannot display PDFs inline.
                  </p>
                  <a href={api.documentFileUrl(documentId, true)} download>
                    <Button variant="primary">Download instead</Button>
                  </a>
                </div>
              </object>
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
                <p className="text-[14px] font-medium text-[var(--color-ink-secondary)]">
                  Original file is no longer on disk
                </p>
                <p className="max-w-md text-[13px] text-[var(--color-ink-muted)]">
                  The extracted passages are still indexed and searchable — switch to the
                  Passages tab to read them.
                </p>
              </div>
            )
          ) : (
            <div className="flex h-full flex-col">
              <div className="border-b border-[var(--color-line-subtle)] p-3">
                <div className="relative">
                  <IconSearch
                    size={14}
                    className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-[var(--color-ink-muted)]"
                  />
                  <label htmlFor="passage-search" className="sr-only">
                    Search passages
                  </label>
                  <input
                    id="passage-search"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search inside this document…"
                    className="btn-glass w-full rounded-[var(--radius-control)] py-1.5 pr-3 pl-8 text-[13px] text-[var(--color-ink-primary)] placeholder:text-[var(--color-ink-muted)] focus:border-[var(--color-accent)]"
                  />
                </div>
                <p className="mt-2 text-[11.5px] text-[var(--color-ink-muted)]">
                  This is the text exactly as IndusBrain indexed it — what retrieval actually
                  searches.
                </p>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto p-3">
                {matchingPassages.length === 0 ? (
                  <p className="px-2 py-8 text-center text-[13px] text-[var(--color-ink-muted)]">
                    {search ? 'No passages match that search.' : 'No passages were extracted.'}
                  </p>
                ) : (
                  <ol>
                    {matchingPassages.map((passage) => (
                      <li
                        key={passage.chunk_index}
                        className="border-b border-[var(--color-line-subtle)] py-3 last:border-0"
                      >
                        <div className="mb-1.5 flex items-center gap-2">
                          <Badge tone="neutral" mono>
                            #{passage.chunk_index}
                          </Badge>
                          <span className="text-[11.5px] text-[var(--color-ink-muted)]">
                            page {passage.page_number}
                          </span>
                        </div>
                        <p className="text-[12.5px] leading-relaxed whitespace-pre-wrap text-[var(--color-ink-secondary)]">
                          {passage.text}
                        </p>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
