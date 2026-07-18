import React, { useEffect, useState } from 'react';

interface Anomaly {
  asset: string;
  metric: string;
  variance: number;
  max_value: number;
  min_value: number;
  conflicting_sources: string[];
  message: string;
}

interface ConflictReport {
  conflict_detected: boolean;
  severity: string;
  detected_anomalies: Anomaly[];
}

export const ConflictAlertPanel: React.FC = () => {
  const [report, setReport] = useState<ConflictReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const triggerSystemAuditScan = async () => {
    setLoading(true);
    try {
      // Stream a request straight to Rudra's Phase 9 FastAPI conflict checker route
      const response = await fetch('http://localhost:8000/api/v1/ingestion/scan-conflicts', {
        method: 'POST',
      });
      if (response.ok) {
        const data = await response.json();
        setReport(data);
      }
    } catch (error) {
      console.error('❌ ANOMALY UI ERROR: Connection to analytics grid failed:', error);
    } finally {
      setLoading(false);
    }
  };

  // Trigger a full cross-document safety audit scan automatically when the panel mounts
  useEffect(() => {
    triggerSystemAuditScan();
  }, []);

  if (loading) {
    return (
      <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl animate-pulse text-slate-400 font-mono text-xs flex items-center gap-3 shadow-inner">
        <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
        🔄 Running global multi-document parameter tolerance safety audit scan...
      </div>
    );
  }

  // GATE A: Pristine Data Agreement. Render a non-intrusive, protective emerald layout block.
  if (!report || !report.conflict_detected || report.detected_anomalies.length === 0) {
    return (
      <div className="p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-xl text-emerald-400 flex items-center justify-between shadow-lg shadow-emerald-950/5">
        <div className="flex items-center gap-2.5 text-sm">
          <span>🛡️</span>
          <span className="font-medium">System specifications aligned. Zero parameter discrepancies identified across active repositories.</span>
        </div>
        <button 
          onClick={triggerSystemAuditScan} 
          className="text-xs bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 text-emerald-300 px-3 py-1 rounded-md font-mono transition"
        >
          Re-Audit
        </button>
      </div>
    );
  }

  // GATE B: Threat Vector Caught. Expand high-impact crimson threat matrices immediately.
  return (
    <div className="w-full bg-red-950/10 border border-red-500/30 rounded-xl overflow-hidden shadow-2xl shadow-red-950/20 transition-all duration-300">
      
      {/* High-Impact Visual Banner Top Strip */}
      <div className="bg-gradient-to-r from-red-600 to-amber-600 px-6 py-3.5 flex items-center justify-between text-white font-bold tracking-wide shadow-md">
        <div className="flex items-center gap-3">
          <span className="text-xl animate-bounce">🚨</span>
          <span className="text-sm uppercase font-mono tracking-wider">
            CRITICAL PARAMETER CONTRADICTION IDENTIFIED: {report.severity || "WARNING"}
          </span>
        </div>
        <button 
          onClick={triggerSystemAuditScan} 
          className="bg-white/10 hover:bg-white/20 border border-white/15 text-xs px-3 py-1.5 rounded-lg font-mono backdrop-blur-md transition"
        >
          Force System Check
        </button>
      </div>

      {/* Dynamic Mapping Anomaly Display Ledger Container */}
      <div className="p-6 flex flex-col gap-4 max-h-[400px] overflow-y-auto bg-slate-950/40">
        {report.detected_anomalies.map((anomaly, idx) => (
          <div key={idx} className="bg-slate-900/90 border border-slate-800/80 rounded-lg p-5 flex flex-col gap-3 shadow-inner group hover:border-slate-700 transition">
            
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/60 pb-2.5">
              <div className="flex items-center gap-2">
                <span className="text-slate-500 text-xs">TARGET ASSET:</span>
                <span className="text-amber-400 font-mono font-bold text-base tracking-tight bg-amber-500/5 border border-amber-500/10 px-2 py-0.5 rounded">
                  {anomaly.asset}
                </span>
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 font-mono font-medium">
                Delta Spread: {anomaly.variance} {anomaly.metric}
              </span>
            </div>
            
            <p className="text-slate-300 text-xs font-mono leading-relaxed">{anomaly.message}</p>
            
            {/* Visual Contrast Parameter Blocks Side-By-Side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-1">
              <div className="bg-slate-950/80 border-l-4 border-amber-500 p-3 rounded-md shadow-inner">
                <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider font-semibold">Upper Limit Readout</div>
                <div className="text-lg font-mono font-bold text-slate-100 mt-0.5">
                  {anomaly.max_value} <span className="text-xs text-slate-400 font-normal">{anomaly.metric}</span>
                </div>
              </div>
              <div className="bg-slate-950/80 border-l-4 border-red-500 p-3 rounded-md shadow-inner">
                <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider font-semibold">Lower Limit Readout</div>
                <div className="text-lg font-mono font-bold text-slate-100 mt-0.5">
                  {anomaly.min_value} <span className="text-xs text-slate-400 font-normal">{anomaly.metric}</span>
                </div>
              </div>
            </div>

            {/* Document Traversal Origin Lineage Fields */}
            <div className="mt-1 pt-2.5 border-t border-slate-800/40 flex flex-wrap items-center gap-2 text-xs">
              <span className="font-mono text-[11px] font-semibold text-slate-500 uppercase tracking-tight">Lineage Data Trail:</span>
              <div className="flex flex-wrap gap-1.5">
                {anomaly.conflicting_sources.map((sourceFilename, sIdx) => (
                  <span key={sIdx} className="bg-slate-950 text-slate-300 px-2 py-0.5 rounded font-mono text-[11px] border border-slate-800/80 shadow-inner group-hover:border-slate-700/60 transition">
                    📄 {sourceFilename}
                  </span>
                ))}
              </div>
            </div>

          </div>
        ))}
      </div>

    </div>
  );
};