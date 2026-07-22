import React, { useCallback, useRef, useState } from 'react';
import { api, ApiError } from '../lib/api';
import type { DashboardPayload } from '../lib/types';
import { PageBody, PageHeader } from '../components/AppShell';
import { Badge, Button, Card, CardHeader, cx, EmptyState, ErrorNotice, Skeleton } from '../components/ui/primitives';
import { IconCheck, IconClose, IconDocs, IconRefresh, IconTrash, IconUpload } from '../components/ui/icons';

type TrackedStage = 'UPLOADING' | 'PENDING' | 'PARSED' | 'EMBEDDED' | 'FAILED';

interface TrackedUpload {
  key: string;
  filename: string;
  documentId?: number;
  stage: TrackedStage;
  error?: string;
}

const STAGE_COPY: Record<TrackedStage, { label: string; tone: 'neutral' | 'info' | 'warning' | 'success' | 'danger' }> = {
  UPLOADING: { label: 'Uploading', tone: 'neutral' },
  PENDING: { label: 'Queued for extraction', tone: 'warning' },
  PARSED: { label: 'Extracting and indexing', tone: 'info' },
  EMBEDDED: { label: 'Indexed', tone: 'success' },
  FAILED: { label: 'Failed', tone: 'danger' },
};

const DOC_STATUS_TONE = {
  EMBEDDED: 'success',
  PARSED: 'info',
  PENDING: 'warning',
  FAILED: 'danger',
} as const;

export const DocumentsPage: React.FC<{
  dashboard: DashboardPayload | null;
  onDataChanged: () => void;
}> = ({ dashboard, onDataChanged }) => {
  const [queue, setQueue] = useState<File[]>([]);
  const [tracked, setTracked] = useState<TrackedUpload[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = (incoming: FileList | File[]) => {
    const pdfs = Array.from(incoming).filter((file) => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'));
    const rejected = Array.from(incoming).length - pdfs.length;
    if (rejected > 0) {
      setError(`${rejected} file${rejected === 1 ? '' : 's'} skipped — only PDF documents are supported.`);
    }
    if (pdfs.length > 0) setQueue((prev) => [...prev, ...pdfs]);
  };

  /**
   * Polls the real backend status for a document until it reaches a terminal
   * state.
   *
   * The previous UI faked this with setTimeout steps and declared "BATCH
   * SUCCESS" as soon as the HTTP request returned — but upload returns 202
   * Accepted and the actual extraction, embedding and graph sync happen
   * afterwards in a background task. A document could fail and the UI would
   * still show success.
   */
  const trackDocument = useCallback(
    async (key: string, documentId: number) => {
      const deadline = Date.now() + 10 * 60 * 1000;

      while (Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        try {
          const status = await api.ingestionStatus(documentId);
          const stage = status.current_pipeline_stage.split('.').pop()?.toUpperCase() as TrackedStage;

          setTracked((prev) => prev.map((item) => (item.key === key ? { ...item, stage } : item)));

          if (stage === 'EMBEDDED' || stage === 'FAILED') {
            onDataChanged();
            return;
          }
        } catch {
          // Transient polling failure — keep trying until the deadline.
        }
      }

      setTracked((prev) =>
        prev.map((item) =>
          item.key === key
            ? { ...item, stage: 'FAILED', error: 'Timed out waiting for indexing to finish.' }
            : item,
        ),
      );
    },
    [onDataChanged],
  );

  const startUpload = async () => {
    if (queue.length === 0) return;
    setUploading(true);
    setError(null);

    const batch = queue;
    const placeholders: TrackedUpload[] = batch.map((file, index) => ({
      key: `${Date.now()}-${index}`,
      filename: file.name,
      stage: 'UPLOADING',
    }));
    setTracked((prev) => [...placeholders, ...prev]);
    setQueue([]);

    try {
      const result = await api.upload(batch);

      // Match each returned document id back to its placeholder by filename.
      const updated = placeholders.map((placeholder) => {
        const match = result.queue_manifest.find((item) => item.filename === placeholder.filename);
        return match
          ? { ...placeholder, documentId: match.id, stage: 'PENDING' as TrackedStage }
          : { ...placeholder, stage: 'FAILED' as TrackedStage, error: 'Server did not acknowledge this file.' };
      });

      setTracked((prev) => [...updated, ...prev.filter((p) => !placeholders.some((n) => n.key === p.key))]);
      onDataChanged();

      await Promise.all(
        updated
          .filter((item) => item.documentId !== undefined)
          .map((item) => trackDocument(item.key, item.documentId!)),
      );
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Upload failed.';
      setError(message);
      setTracked((prev) =>
        prev.map((item) =>
          placeholders.some((p) => p.key === item.key)
            ? { ...item, stage: 'FAILED', error: message }
            : item,
        ),
      );
    } finally {
      setUploading(false);
    }
  };

  const deleteDocument = async (documentId: number) => {
    setDeletingId(documentId);
    try {
      const result = await api.deleteDocument(documentId);
      if (result.warnings?.length) {
        setError(`Document removed, but cleanup reported: ${result.warnings.join('; ')}`);
      }
      onDataChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not delete this document.');
    } finally {
      setDeletingId(null);
    }
  };

  const activeUploads = tracked.filter((t) => t.stage !== 'EMBEDDED');

  return (
    <PageBody>
      <PageHeader
        title="Documents"
        description="Upload and manage the source documents that IndusBrain reasons over."
        actions={
          <Button variant="secondary" size="sm" onClick={onDataChanged}>
            <IconRefresh size={14} />
            Refresh
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <ErrorNotice title="Something went wrong" detail={error} />
        </div>
      )}

      <div className="grid min-w-0 gap-5 lg:grid-cols-5">
        {/* Upload */}
        <Card className="lg:col-span-2">
          <CardHeader title="Add documents" description="PDF manuals, SOPs, logs and standards" />
          <div className="p-5">
            <div
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragging(false);
                addFiles(event.dataTransfer.files);
              }}
              className={cx(
                'rounded-xl border-2 border-dashed px-5 py-9 text-center transition-colors',
                dragging
                  ? 'border-[var(--color-accent)] bg-[var(--color-accent-soft)]'
                  : 'border-[var(--color-line-default)] bg-[var(--color-surface-overlay)]',
              )}
            >
              <IconUpload size={26} className="mx-auto text-[var(--color-ink-faint)]" />
              <p className="mt-2.5 text-[13.5px] text-[var(--color-ink-secondary)]">
                Drop PDF files here, or
              </p>
              <button
                onClick={() => inputRef.current?.click()}
                className="mt-1 text-[13.5px] font-medium text-[var(--color-accent-hover)] hover:underline"
              >
                browse your computer
              </button>
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,application/pdf"
                multiple
                className="hidden"
                onChange={(event) => {
                  if (event.target.files) addFiles(event.target.files);
                  event.target.value = '';
                }}
              />
            </div>

            {queue.length > 0 && (
              <div className="mt-4 space-y-1.5">
                <p className="text-[12px] font-semibold tracking-wide text-[var(--color-ink-faint)] uppercase">
                  Ready to upload ({queue.length})
                </p>
                {queue.map((file, index) => (
                  <div
                    key={`${file.name}-${index}`}
                    className="flex items-center gap-2 rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-overlay)] px-3 py-2"
                  >
                    <IconDocs size={14} className="shrink-0 text-[var(--color-ink-faint)]" />
                    <span className="min-w-0 flex-1 truncate text-[12.5px] text-[var(--color-ink-secondary)]">
                      {file.name}
                    </span>
                    <span className="shrink-0 text-[11.5px] text-[var(--color-ink-faint)] tabular-nums">
                      {(file.size / 1024).toFixed(0)} KB
                    </span>
                    <button
                      onClick={() => setQueue((prev) => prev.filter((_, i) => i !== index))}
                      className="shrink-0 rounded p-0.5 text-[var(--color-ink-faint)] hover:text-[var(--color-danger)]"
                      aria-label={`Remove ${file.name}`}
                    >
                      <IconClose size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <Button
              variant="primary"
              className="mt-4 w-full"
              onClick={startUpload}
              disabled={queue.length === 0 || uploading}
            >
              {uploading ? 'Uploading…' : `Upload ${queue.length || ''} document${queue.length === 1 ? '' : 's'}`}
            </Button>

            <p className="mt-2.5 text-[11.5px] leading-relaxed text-[var(--color-ink-faint)]">
              Text is extracted, split into passages, embedded into the vector index and mapped into
              the knowledge graph. Scanned pages fall back to OCR.
            </p>
          </div>
        </Card>

        {/* Live ingestion progress — driven by real backend status */}
        <Card className="lg:col-span-3">
          <CardHeader
            title="Ingestion activity"
            description={
              activeUploads.length > 0
                ? `${activeUploads.length} in progress`
                : 'Real pipeline status, polled from the server'
            }
          />
          <div className="max-h-[420px] overflow-y-auto p-4">
            {tracked.length === 0 ? (
              <EmptyState
                compact
                title="No recent uploads"
                description="Progress here reflects the real server-side pipeline, not a simulated timer."
              />
            ) : (
              <ul className="space-y-2">
                {tracked.map((item) => {
                  const copy = STAGE_COPY[item.stage];
                  const inFlight = item.stage === 'UPLOADING' || item.stage === 'PENDING' || item.stage === 'PARSED';
                  return (
                    <li
                      key={item.key}
                      className="rounded-lg border border-[var(--color-line-subtle)] bg-[var(--color-surface-overlay)] p-3"
                    >
                      <div className="flex items-center gap-2">
                        {item.stage === 'EMBEDDED' ? (
                          <IconCheck size={14} className="shrink-0 text-[var(--color-success)]" />
                        ) : item.stage === 'FAILED' ? (
                          <IconClose size={14} className="shrink-0 text-[var(--color-danger)]" />
                        ) : (
                          <IconDocs size={14} className="shrink-0 text-[var(--color-ink-faint)]" />
                        )}
                        <span className="min-w-0 flex-1 truncate font-[family-name:var(--font-mono)] text-[12.5px] text-[var(--color-ink-primary)]">
                          {item.filename}
                        </span>
                        <Badge tone={copy.tone}>{copy.label}</Badge>
                      </div>

                      {inFlight && (
                        <div className="progress-indeterminate relative mt-2 h-1 overflow-hidden rounded-full bg-[var(--color-surface-base)]" />
                      )}

                      {item.error && (
                        <p className="mt-1.5 text-[12px] text-[var(--color-danger)]">{item.error}</p>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </Card>
      </div>

      {/* Library */}
      <Card className="mt-5">
        <CardHeader
          title="Document library"
          description={dashboard ? `${dashboard.inventory.length} documents indexed` : 'Loading…'}
        />
        {!dashboard ? (
          <div className="p-5">
            <Skeleton className="h-40" />
          </div>
        ) : dashboard.inventory.length === 0 ? (
          <EmptyState
            icon={<IconDocs size={28} />}
            title="No documents in the library"
            description="Upload your first document to begin building the knowledge base."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-[13px]">
              <thead>
                <tr className="border-b border-[var(--color-line-subtle)] text-left text-[12px] text-[var(--color-ink-muted)]">
                  <th className="px-5 py-2.5 font-medium">Document</th>
                  <th className="px-5 py-2.5 font-medium">Status</th>
                  <th className="px-5 py-2.5 text-right font-medium">Passages</th>
                  <th className="px-5 py-2.5 text-right font-medium">Size</th>
                  <th className="px-5 py-2.5 text-right font-medium">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {dashboard.inventory.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-b border-[var(--color-line-subtle)] last:border-0 hover:bg-[var(--color-surface-overlay)]"
                  >
                    <td className="max-w-[360px] truncate px-5 py-3 font-[family-name:var(--font-mono)] text-[12.5px] text-[var(--color-ink-primary)]">
                      {doc.filename}
                    </td>
                    <td className="px-5 py-3">
                      <Badge tone={DOC_STATUS_TONE[doc.status] ?? 'neutral'}>
                        {doc.status.toLowerCase()}
                      </Badge>
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums text-[var(--color-ink-secondary)]">
                      {doc.chunk_count}
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums text-[var(--color-ink-muted)]">
                      {(doc.file_size / 1024).toFixed(0)} KB
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={deletingId === doc.id}
                        onClick={() => deleteDocument(doc.id)}
                        title={`Delete ${doc.filename} from all stores`}
                      >
                        <IconTrash size={14} />
                        {deletingId === doc.id ? 'Deleting…' : 'Delete'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </PageBody>
  );
};
