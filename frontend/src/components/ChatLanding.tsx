import React from 'react';
import { Link } from 'react-router-dom';
import type { DashboardPayload } from '../lib/types';
import { Badge, Button, cx } from './ui/primitives';
import { IconAlert, IconArrowUpRight, IconDocs, IconGraph, IconUpload } from './ui/icons';
import { LogoMark } from './brand/Logo';

/**
 * Chat landing content.
 *
 * Everything here is derived from the CURRENT knowledge base. The previous
 * version listed four fixed prompts naming PUMP-101, which kept inviting the
 * user to ask about equipment long after every document mentioning it had been
 * deleted — the question looked legitimate but could never be answered.
 *
 * Two distinct states:
 *   empty corpus  -> explain what to upload and how the system works. No prompts,
 *                    because there is genuinely nothing to ask about.
 *   loaded corpus -> starters generated from real assets, real contradictions and
 *                    real documents, plus a snapshot of what is indexed.
 */

const REASON_STYLES: Record<string, { tone: 'danger' | 'accent' | 'info' | 'warning'; text: string }> = {
  conflict: { tone: 'danger', text: 'Contradiction' },
  asset: { tone: 'accent', text: 'Equipment' },
  document: { tone: 'info', text: 'Procedure' },
  gap: { tone: 'warning', text: 'Known gap' },
};

const EmptyCorpus: React.FC = () => (
  <div className="mx-auto flex max-w-xl flex-col items-center py-8 text-center">
    <div className="mb-5 text-[var(--color-ink-muted)]">
      <IconUpload size={34} />
    </div>

    <h2 className="text-[22px] font-bold tracking-[-0.02em] text-[var(--color-ink-primary)]">
      No documents have been indexed yet
    </h2>
    <p className="mt-2 text-[13.5px] leading-relaxed text-[var(--color-ink-muted)]">
      Upload industrial documents to begin building your knowledge base. IndusBrain
      answers only from what you have indexed, so there is nothing to ask about yet.
    </p>

    <div className="mt-7 w-full border-t border-[var(--color-line-subtle)] pt-5 text-left">
      <p className="eyebrow mb-2.5">
        What to upload
      </p>
      <ul className="space-y-1.5 text-[13px] text-[var(--color-ink-secondary)]">
        {[
          'OEM equipment manuals and specification sheets',
          'Standard operating procedures (startup, shutdown, changeover)',
          'Maintenance logs, work orders and failure reports',
          'Safety standards, permits and compliance documents',
          'Inspection reports and certification registers',
        ].map((item) => (
          <li key={item} className="flex gap-2">
            <span aria-hidden="true" className="mt-2 h-px w-3 shrink-0 bg-[var(--color-ink-muted)]" />
            {item}
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[12.5px] text-[var(--color-ink-muted)]">
        PDF format. Scanned pages fall back to OCR automatically.
      </p>
    </div>

    <div className="mt-5 w-full border-t border-[var(--color-line-subtle)] pt-5 text-left">
      <p className="eyebrow mb-2.5">
        How it works
      </p>
      <ol className="space-y-1.5 text-[13px] text-[var(--color-ink-secondary)]">
        {[
          'Text is extracted and split into searchable passages.',
          'Equipment tags are recognised and mapped into a knowledge graph.',
          'Questions search both the vector index and the graph together.',
          'Every answer cites the passages it came from, with a relevance score.',
          'Contradictions between documents are detected automatically.',
        ].map((step, index) => (
          <li key={step} className="flex gap-2.5">
            <span className="mt-0.5 shrink-0 font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-ink-muted)] tabular-nums">
              {String(index + 1).padStart(2, '0')}
            </span>
            {step}
          </li>
        ))}
      </ol>
    </div>

    <Link to="/documents" className="mt-5">
      <Button variant="primary">
        <IconUpload size={15} />
        Upload documents
      </Button>
    </Link>
  </div>
);

export const ChatLanding: React.FC<{
  dashboard: DashboardPayload | null;
  onAsk: (question: string) => void;
}> = ({ dashboard, onAsk }) => {
  // Until the first dashboard poll returns we cannot know whether the corpus is
  // empty, so show nothing rather than briefly flashing the wrong state.
  if (!dashboard) return null;

  if (dashboard.empty_states.no_documents) return <EmptyCorpus />;

  const suggestions = dashboard.chat_suggestions ?? [];
  const context = dashboard.chat_context;
  const conflicts = dashboard.conflicts ?? [];

  return (
    <div className="mx-auto flex max-w-3xl flex-col py-6">
      <div className="mb-7">
        <LogoMark size={40} className="text-[var(--color-ink-primary)]" />
        <h2 className="mt-4 text-[clamp(1.6rem,1.2rem+1.4vw,2.3rem)] leading-[1.05] font-bold tracking-[-0.03em] text-[var(--color-ink-primary)]">
          What do you need to know
          <span className="text-[var(--color-ink-muted)]"> about the plant?</span>
        </h2>
        <p className="mt-2 text-[13.5px] leading-relaxed text-[var(--color-ink-muted)]">
          {dashboard.metrics.total_documents} document
          {dashboard.metrics.total_documents === 1 ? '' : 's'} indexed ·{' '}
          {dashboard.metrics.total_assets} asset
          {dashboard.metrics.total_assets === 1 ? '' : 's'} recognised. I answer only from
          these documents.
        </p>
      </div>

      {/* Live contradiction — the highest-value thing to surface first */}
      {conflicts.length > 0 && (
        <Link
          to="/conflicts"
          className="mb-6 flex items-start gap-3"
        >
          <IconAlert size={17} className="mt-0.5 shrink-0 text-[var(--color-danger)]" />
          <div className="min-w-0">
            <p className="text-[13px] font-medium text-[var(--color-danger)]">
              {conflicts.length} unresolved contradiction
              {conflicts.length === 1 ? '' : 's'} in your documents
            </p>
            <p className="mt-0.5 truncate text-[12.5px] text-[var(--color-ink-secondary)]">
              {conflicts[0].asset_tag} · {conflicts[0].parameter}
            </p>
          </div>
        </Link>
      )}

      {/* Starters generated from the corpus */}
      {suggestions.length > 0 && (
        <div className="grid gap-x-8 sm:grid-cols-2">
          {suggestions.map((suggestion, index) => {
            const style = REASON_STYLES[suggestion.reason] ?? REASON_STYLES.asset;
            return (
              <button
                key={suggestion.question}
                onClick={() => onAsk(suggestion.question)}
                className="pressable group animate-fade-rise flex w-full flex-col border-t border-[var(--color-line-subtle)] py-4 text-left hover:border-[var(--color-ink-primary)]"
                style={{ animationDelay: `${0.08 + index * 0.05}s` }}
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-ink-muted)] tabular-nums">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <Badge tone={style.tone}>{style.text}</Badge>
                  <span className="truncate text-[11.5px] text-[var(--color-ink-muted)]">
                    {suggestion.label}
                  </span>
                  <IconArrowUpRight
                    size={14}
                    className="ml-auto shrink-0 text-[var(--color-ink-muted)] transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-[var(--color-ink-primary)]"
                  />
                </div>
                <p className="text-[13.5px] leading-snug text-[var(--color-ink-primary)]">
                  {suggestion.question}
                </p>
              </button>
            );
          })}
        </div>
      )}

      {/* Snapshot of what is currently indexed */}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {context?.top_assets?.length > 0 && (
          <div className="border-t border-[var(--color-line-subtle)] pt-4">
            <div className="mb-2.5 flex items-center gap-2">
              <IconGraph size={14} className="text-[var(--color-ink-muted)]" />
              <p className="eyebrow">
                Most referenced equipment
              </p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {context.top_assets.slice(0, 6).map((asset) => (
                <button
                  key={asset.tag}
                  onClick={() => onAsk(`What do the documents say about ${asset.tag}?`)}
                  title={`${asset.category} · ${asset.mentions} mentions`}
                >
                  <Badge tone="accent" mono className="pressable hover:border-[var(--color-accent)]">
                    {asset.tag}
                  </Badge>
                </button>
              ))}
            </div>
          </div>
        )}

        {context?.recent_documents?.length > 0 && (
          <div className="border-t border-[var(--color-line-subtle)] pt-4">
            <div className="mb-2.5 flex items-center gap-2">
              <IconDocs size={14} className="text-[var(--color-ink-muted)]" />
              <p className="eyebrow">
                Recently indexed
              </p>
            </div>
            <ul className="space-y-1">
              {context.recent_documents.slice(0, 4).map((doc) => (
                <li
                  key={doc.id}
                  className={cx(
                    'truncate font-[family-name:var(--font-mono)] text-[11.5px]',
                    'text-[var(--color-ink-secondary)]',
                  )}
                  title={`${doc.filename} · ${doc.chunk_count} passages`}
                >
                  {doc.filename}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
