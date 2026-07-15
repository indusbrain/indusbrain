import React from 'react';
import type { QueryResponse } from '../services/api';
import { FileText, ShieldAlert, CheckCircle } from 'lucide-react';
import Markdown from 'markdown-to-jsx';

interface ExecutiveReportProps {
  report: QueryResponse | null;
}

export const ExecutiveReport: React.FC<ExecutiveReportProps> = ({ report }) => {
  if (!report) {
    return (
      <div className="bg-industrial-dark p-6 rounded-lg border border-industrial-border h-full flex flex-col items-center justify-center text-center text-gray-500 min-h-[300px]">
        <FileText className="w-12 h-12 mb-2 opacity-30" />
        <p className="text-sm">Submit an operator query in the console to generate the active Industrial Intelligence Report.</p>
      </div>
    );
  }

  const isViolating = report.response.includes("🔴 CRITICAL WARNING");

  return (
    <div className="bg-industrial-dark p-6 rounded-lg border border-industrial-border space-y-6">
      <div className="flex justify-between items-center border-b border-industrial-border pb-4">
        <h2 className="text-xl font-bold flex items-center gap-2 text-industrial-accent">
          <FileText className="w-5 h-5" /> Executive Decision Board
        </h2>
        
        <div className="flex items-center gap-3 bg-industrial-darkest px-4 py-1.5 rounded-full border border-industrial-border">
          <span className="text-xs text-gray-400 font-semibold">Confidence Indicator:</span>
          <span className={`text-sm font-bold ${report.confidence_score >= 0.8 ? 'text-industrial-terminal' : 'text-industrial-accent'}`}>
            {(report.confidence_score * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {isViolating ? (
        <div className="bg-red-950/40 border border-red-500/50 rounded-lg p-4 flex gap-3 text-red-400">
          <ShieldAlert className="w-5 h-5 shrink-0" />
          <div className="text-xs">
            <span className="font-bold block mb-1">COMPLIANCE WARNING FLAGGED:</span>
            This procedure violates regulatory safety thresholds. Review safety remediations below.
          </div>
        </div>
      ) : (
        <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-lg p-4 flex gap-3 text-emerald-400">
          <CheckCircle className="w-5 h-5 shrink-0" />
          <div className="text-xs">
            <span className="font-bold block mb-1">COMPLIANCE NOMINAL:</span>
            No critical active safety violations were detected in the query parameters.
          </div>
        </div>
      )}

      <div className="prose prose-invert max-w-none text-sm text-gray-300 leading-relaxed max-h-[500px] overflow-y-auto pr-2 bg-industrial-darkest/40 p-4 rounded-lg border border-industrial-border font-sans">
        <Markdown>{report.response}</Markdown>
      </div>
    </div>
  );
};