import React, { useState, useEffect } from 'react';
import { FileBulkUploadGrid } from './components/FileBulkUploadGrid';
import { OperatorChatPanel } from './components/OperatorChatPanel';

interface FileEntry { id: number; filename: string; storage_path: string; uploaded_at: string; }
interface AssetEntry { tag: string; name: string; type: string; status: string; health: string; }
interface ConflictAnomaly { asset_tag: string; parameter: string; unit: string; severity: string; conflict_statement: string; doc_a: string; val_a: number; doc_b: string; val_b: number; }
interface ProactiveInsight { id: string; target_asset: string; severity: string; statement: string; }
interface ImprovementRecommendation { id: string; type: string; asset: string; recommendation: string; }

interface TelemetryState {
  infrastructure: { postgresql: string; neo4j: string; chromadb: string; ollama_qwen: string; };
  metrics: { total_documents: number; knowledge_score: number; documentation_completeness: number; compliance_health: number; quality_coverage: number; missing_documents: number; duplicate_documents: number; };
  inventory: FileEntry[]; assets: AssetEntry[]; conflicts: ConflictAnomaly[]; ai_insights: ProactiveInsight[];
  improvements: ImprovementRecommendation[]; // 🎯 THE UI FIX: Injected the automated structural knowledge optimization array
}

function App() {
  const [telemetry, setTelemetry] = useState<TelemetryState>({
    infrastructure: { postgresql: 'OFFLINE', neo4j: 'OFFLINE', chromadb: 'OFFLINE', ollama_qwen: 'OFFLINE' },
    metrics: { total_documents: 0, knowledge_score: 0, documentation_completeness: 0, compliance_health: 0, quality_coverage: 0, missing_documents: 0, duplicate_documents: 0 },
    inventory: [], assets: [], conflicts: [], ai_insights: [], improvements: []
  });
  
  const [showConflictPanel, setShowConflictPanel] = useState<boolean>(false);

  // AI IMPACT SIMULATOR CONTROL STATES
  const [simScenario, setSimScenario] = useState<string>('Delay maintenance schedule by one week');
  const [simAsset, setSimAsset] = useState<string>('SELECT ASSET');
  const [isSimulating, setIsSimUploading] = useState<boolean>(false);
  const [simResult, setSimResult] = useState<any | null>(null);

  const refreshDashboardMetrics = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/telemetry/dashboard');
      if (res.ok) {
        const data = await res.json();
        setTelemetry({
          infrastructure: data?.infrastructure || { postgresql: 'OFFLINE', neo4j: 'OFFLINE', chromadb: 'OFFLINE', ollama_qwen: 'OFFLINE' },
          metrics: data?.metrics || { total_documents: 0, knowledge_score: 0, documentation_completeness: 0, compliance_health: 0, quality_coverage: 0, missing_documents: 0, duplicate_documents: 0 },
          inventory: Array.isArray(data?.inventory) ? data.inventory : [],
          assets: Array.isArray(data?.assets) ? data.assets : [] ,
          conflicts: Array.isArray(data?.conflicts) ? data.conflicts : [],
          ai_insights: Array.isArray(data?.ai_insights) ? data.ai_insights : [],
          improvements: Array.isArray(data?.improvements) ? data.improvements : []
        });
      }
    } catch (err) {
      console.warn("Telemetry polling active.");
    }
  };

  const executeSimulationModelPass = async () => {
    setIsSimUploading(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/simulator/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: simScenario, asset_tag: simAsset })
      });
      if (res.ok) {
        const output = await res.json();
        setSimResult(output);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSimUploading(false);
    }
  };

  const dispatchDocumentPurge = async (docId: number) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/telemetry/document/${docId}`, { method: 'DELETE' });
      if (res.ok) refreshDashboardMetrics();
    } catch (err) { console.error(err); }
  };

  useEffect(() => {
    refreshDashboardMetrics();
    const metricsInterval = setInterval(refreshDashboardMetrics, 4000);
    return () => clearInterval(metricsInterval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased font-sans selection:bg-blue-500/20">
      
      {/* Top Banner Navigation Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/20 px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <span className="text-xl">🧠</span>
          <h1 className="text-sm font-black tracking-widest bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent font-mono uppercase">
            IndusBrain Engine Operational Grid OS
          </h1>
        </div>
        
        <div className="flex flex-wrap items-center gap-4 font-mono text-[10px] text-slate-400 bg-slate-950 border border-slate-900 px-4 py-1.5 rounded-lg shadow-inner">
          <div className="flex items-center gap-1.5"><span className={`w-1.5 h-1.5 rounded-full ${telemetry.infrastructure.postgresql === 'ONLINE' ? 'bg-emerald-500 shadow-[0_0_6px_#10b981]' : 'bg-red-500 animate-pulse'}`}></span><span>POSTGRES</span></div>
          <div className="flex items-center gap-1.5"><span className={`w-1.5 h-1.5 rounded-full ${telemetry.infrastructure.neo4j === 'ONLINE' ? 'bg-emerald-500 shadow-[0_0_6px_#10b981]' : 'bg-red-500 animate-pulse'}`}></span><span>NEO4J</span></div>
          <div className="flex items-center gap-1.5"><span className={`w-1.5 h-1.5 rounded-full ${telemetry.infrastructure.chromadb === 'ONLINE' ? 'bg-emerald-500 shadow-[0_0_6px_#10b981]' : 'bg-red-500 animate-pulse'}`}></span><span>CHROMA</span></div>
          <div className="flex items-center gap-1.5"><span className={`w-1.5 h-1.5 rounded-full ${telemetry.infrastructure.ollama_qwen === 'ONLINE' ? 'bg-emerald-500 shadow-[0_0_6px_#10b981]' : 'bg-red-500 animate-pulse'}`}></span><span>OLLAMA (QWEN)</span></div>
        </div>
      </header>

      {/* Critical Conflict Alarm Bar */}
      {telemetry.conflicts.length > 0 && (
        <div 
          onClick={() => setShowConflictPanel(!showConflictPanel)}
          className="bg-amber-500 text-slate-950 px-6 py-2.5 text-center font-mono text-xs font-black tracking-wide uppercase cursor-pointer flex items-center justify-center gap-2 shadow-lg animate-pulse hover:bg-amber-400 transition"
        >
          <span>⚠️ OPERATIONAL CRITICAL WARNING: DISCOVERED {telemetry.conflicts.length} CROSS-DOCUMENT KNOWLEDGE PARAMETER CONFLICTS. CLICK TO AUDIT CONTRADICTIONS.</span>
        </div>
      )}

      {/* Main Dashboard Layout Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 flex flex-col gap-6">
        
        {/* ROW 1: Knowledge DNA Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/20 border border-slate-800/60 p-4 rounded-xl flex flex-col justify-between font-mono shadow-md">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Knowledge Score Health</span>
            <div className="flex items-baseline gap-1 mt-2"><span className="text-2xl font-black text-blue-400">{telemetry.metrics.knowledge_score}%</span></div>
          </div>
          <div className="bg-slate-900/20 border border-slate-800/60 p-4 rounded-xl flex flex-col justify-between font-mono shadow-md">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Maintenance Coverage</span>
            <div className="flex items-baseline gap-1 mt-2"><span className="text-2xl font-black text-indigo-400">{telemetry.metrics.documentation_completeness}%</span></div>
          </div>
          <div className="bg-slate-900/20 border border-slate-800/60 p-4 rounded-xl flex flex-col justify-between font-mono shadow-md">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Safety Compliance</span>
            <div className="flex items-baseline gap-1 mt-2"><span className="text-2xl font-black text-purple-400">{telemetry.metrics.compliance_health}%</span></div>
          </div>
          <div className="bg-slate-900/20 border border-slate-800/60 p-4 rounded-xl flex flex-col justify-between font-mono shadow-md">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Quality Documentation</span>
            <div className="flex items-baseline gap-1 mt-2"><span className="text-2xl font-black text-emerald-400">{telemetry.metrics.quality_coverage}%</span></div>
          </div>
        </div>

        {/* ROW 2: Proactive AI Curiosity Tickers */}
        {telemetry.ai_insights.length > 0 && (
          <div className="flex flex-col gap-2 font-mono">
            <span className="text-[10px] text-purple-400 font-bold tracking-widest uppercase">✨ Autonomous AI Curiosity Insights</span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {telemetry.ai_insights.map((insight) => (
                <div key={insight.id} className="bg-gradient-to-br from-purple-950/20 to-slate-950 p-4 rounded-xl border border-purple-900/30 flex items-start gap-3 shadow-md">
                  <span className="text-lg mt-0.5 animate-pulse">💡</span>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-purple-400 font-black text-[11px] bg-purple-950/40 border border-purple-900/50 px-2 py-0.5 rounded">{insight.target_asset}</span>
                    </div>
                    <p className="text-slate-300 text-xs font-sans leading-relaxed">{insight.statement}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ===================================================================== */}
        {/* ⚙️ DYNAMIC AUTONOMOUS KNOWLEDGE IMPROVEMENT RECOMMENDATIONS MATRIX    */}
        {/* ===================================================================== */}
        {telemetry.improvements.length > 0 && (
          <div className="flex flex-col gap-2 font-mono animate-fadeIn">
            <span className="text-[10px] text-blue-400 font-bold tracking-widest uppercase">⚙️ Autonomous Knowledge Improvement Directives (Management Deck)</span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {telemetry.improvements.map((imp) => (
                <div key={imp.id} className="bg-slate-900/40 border border-slate-800/80 p-4 rounded-xl flex items-start gap-3 shadow-md border-l-2 border-l-blue-500">
                  <span className="text-lg mt-0.5">⚙️</span>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-blue-400 font-black text-[10px] bg-slate-950 border border-slate-900 px-1.5 py-0.5 rounded">{imp.asset}</span>
                      <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded uppercase ${imp.type === 'BROKEN_REFERENCE' ? 'bg-red-950/40 text-red-400' : 'bg-amber-950/40 text-amber-400'}`}>
                        {imp.type.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-slate-400 text-xs font-sans leading-relaxed">{imp.recommendation}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Collapsible Conflict Panel Drawer Box */}
        {showConflictPanel && telemetry.conflicts.length > 0 && (
          <div className="bg-slate-900/80 border border-amber-500/30 p-5 rounded-xl font-mono text-xs text-slate-300 animate-slideDown shadow-xl flex flex-col gap-4">
            <div className="text-amber-400 font-black uppercase tracking-wider flex items-center justify-between border-b border-slate-800 pb-2">
              <span>🚨 Knowledge Conflict Cross-Correlation Audit Center</span>
              <button type="button" onClick={() => setShowConflictPanel(false)} className="text-slate-500 hover:text-slate-300">✕ Close Panel</button>
            </div>
            <div className="flex flex-col gap-3">
              {telemetry.conflicts.map((conf, idx) => (
                <div key={idx} className="bg-slate-950 p-4 rounded-lg border border-slate-900 flex flex-col gap-3">
                  <p className="text-slate-300 font-sans text-xs leading-relaxed">{conf.conflict_statement}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Inventory metric secondary blocks */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-slate-950 border border-slate-900 px-4 py-3 rounded-xl flex items-center justify-between font-mono text-xs"><span className="text-slate-500 font-bold">Vault Inventory:</span><span className="text-slate-200 font-black text-sm">{telemetry.metrics.total_documents} Files</span></div>
          <div className={`border px-4 py-3 rounded-xl flex items-center justify-between font-mono text-xs transition ${telemetry.metrics.missing_documents > 0 ? 'bg-amber-950/20 border-amber-900/50 text-amber-400 animate-pulse' : 'bg-slate-950 border-slate-900 text-slate-500'}`}><span className="font-bold">Missing Critical Documents:</span><span className="font-black text-sm">{telemetry.metrics.missing_documents} Gaps</span></div>
          <div className={`border px-4 py-3 rounded-xl flex items-center justify-between font-mono text-xs transition ${telemetry.metrics.duplicate_documents > 0 ? 'bg-red-950/20 border-red-900/50 text-red-400' : 'bg-slate-950 border-slate-900 text-slate-500'}`}><span className="font-bold">Duplicate Documents:</span><span className="font-black text-sm">{telemetry.metrics.duplicate_documents} Copies</span></div>
        </div>

        {/* AI Predictive Decision Impact Simulator Control Workspace */}
        <div className="bg-slate-900/20 border border-slate-800/80 p-5 rounded-xl font-mono text-xs text-slate-400 flex flex-col gap-4 shadow-xl backdrop-blur-md">
          <span className="text-slate-500 font-bold tracking-widest block uppercase text-[10px]">🔮 Advanced AI Predictive Decision Impact Simulator</span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
            <div className="flex flex-col gap-2">
              <label className="text-slate-500 text-[9px] font-bold uppercase">Target Hardware Node:</label>
              <select value={simAsset} onChange={(e) => setSimAsset(e.target.value)} className="bg-slate-950 border border-slate-800 text-slate-200 px-3 py-2 rounded-lg font-bold">
                <option value="SELECT ASSET">-- CHOOSE ACTIVE TAG --</option>
                {telemetry.assets.map((as, idx) => (<option key={idx} value={as.tag}>{as.tag}</option>))}
              </select>
            </div>
            <div className="sm:col-span-2 flex flex-col gap-2">
              <label className="text-slate-500 text-[9px] font-bold uppercase">Hypothetical Operational Scenario Directive:</label>
              <div className="flex gap-2">
                <input type="text" value={simScenario} onChange={(e) => setSimScenario(e.target.value)} placeholder="Enter schedule modifications or stress variables..." className="flex-1 bg-slate-950 border border-slate-800 px-3 py-2 text-slate-200 rounded-lg" />
                <button type="button" onClick={executeSimulationModelPass} disabled={isSimulating} className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-black px-4 rounded-lg tracking-wide shrink-0 font-mono border border-purple-500/20 shadow-md text-[10px]">{isSimulating ? 'COMPUTING CALC...' : 'RUN SIMULATION'}</button>
              </div>
            </div>
          </div>
          {simResult && (
            <div className="mt-2 border-t border-slate-900 pt-4 grid grid-cols-1 lg:grid-cols-3 gap-5 animate-fadeIn">
              <div className="lg:col-span-1 flex flex-col gap-3.5 bg-slate-950/60 p-4 border border-slate-900 rounded-xl">
                <div>
                  <div className="flex justify-between text-[10px] font-bold text-slate-500 mb-1"><span>PRODUCTION OUTPUT VARIANCE:</span><span className={simResult.metrics.production_impact_pct >= 0 ? "text-emerald-400" : "text-red-400"}>{simResult.metrics.production_impact_pct >= 0 ? '+' : ''}{simResult.metrics.production_impact_pct}%</span></div>
                  <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden"><div className="bg-emerald-500 h-full" style={{ width: `${Math.max(10, Math.min(100, simResult.metrics.production_impact_pct * 4))}%` }}></div></div>
                </div>
                <div>
                  <div className="flex justify-between text-[10px] font-bold text-slate-500 mb-1"><span>FATIGUE RISK MULTIPLIER:</span><span className="text-amber-400 font-black">{simResult.metrics.risk_multiplier_factor}x Factor</span></div>
                  <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden"><div className="bg-amber-500 h-full" style={{ width: `${(simResult.metrics.risk_multiplier_factor / 4) * 100}%` }}></div></div>
                </div>
                <div>
                  <div className="flex justify-between text-[10px] font-bold text-slate-500 mb-1"><span>REGULATORY COMPLIANCE HOLE INDEX:</span><span className="text-purple-400 font-black">{simResult.metrics.compliance_vulnerability_index}/100 Risk</span></div>
                  <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden"><div className="bg-purple-500 h-full" style={{ width: `${simResult.metrics.compliance_vulnerability_index}%` }}></div></div>
                </div>
              </div>
              <div className="lg:col-span-2 bg-purple-950/10 border border-purple-900/20 p-4 rounded-xl flex flex-col justify-between">
                <div><span className="text-[9px] font-black uppercase text-purple-400 block mb-1">📋 AI Risk Prediction & Mitigation Directive Log:</span><p className="text-slate-300 font-sans text-xs leading-relaxed">{simResult.mitigation_directive}</p></div>
              </div>
            </div>
          )}
        </div>

        {/* Main Operational Split Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
          <div className="xl:col-span-2 flex flex-col gap-6"><OperatorChatPanel /><FileBulkUploadGrid /></div>
          <div className="flex flex-col gap-6">
            <div className="bg-slate-900/30 border border-slate-800/80 rounded-xl overflow-hidden backdrop-blur-md shadow-xl">
              <div className="px-4 py-3 bg-slate-950/60 border-b border-slate-800/80 font-mono text-xs text-slate-400 font-bold tracking-wider uppercase flex items-center justify-between"><span>⚙️ Tracked Asset Explorer</span><span className="text-[10px] text-blue-400 font-black">Total: {telemetry.assets.length}</span></div>
              <div className="p-4 flex flex-col gap-3 max-h-[250px] overflow-y-auto scrollbar-thin">
                {telemetry.assets.length === 0 ? (<span className="text-xs font-mono text-slate-600 italic block text-center py-8">No active hardware nodes mapped in graph indices.</span>) : (
                  telemetry.assets.map((asset, i) => (
                    <div key={i} onClick={() => alert(`🔧 CRITICAL OPERATIONS CRUD PROTOCOL:\n====================================\nOpening parameter editor for asset node: [${asset.tag}].`)} className="bg-slate-950/80 border border-slate-800/60 hover:border-blue-500/40 p-3 rounded-lg flex items-center justify-between font-mono text-xs cursor-pointer transition animate-fadeIn">
                      <div><div className="text-blue-400 font-bold">{asset.tag}</div><div className="text-slate-500 text-[10px] font-sans mt-0.5">{asset.name}</div></div>
                      <div className="text-right"><span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${asset.status === 'Operational' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-900/30' : 'bg-amber-950/40 text-amber-400 border-amber-800/30'}`}>{asset.status}</span><div className="text-[9px] text-slate-600 mt-1 font-bold">{asset.health}</div></div>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div className="bg-slate-900/30 border border-slate-800/80 rounded-xl overflow-hidden backdrop-blur-md shadow-xl">
              <div className="px-4 py-3 bg-slate-950/60 border-b border-slate-800/80 font-mono text-xs text-slate-400 font-bold tracking-wider uppercase">📚 Vault Document Ledger Register</div>
              <div className="p-4 flex flex-col gap-3 max-h-[250px] overflow-y-auto scrollbar-thin">
                {telemetry.inventory.length === 0 ? (<span className="text-xs font-mono text-slate-600 italic block text-center py-8">Vault repository empty. Awaiting file uploads.</span>) : (
                  telemetry.inventory.map((file) => (
                    <div key={file.id} className="bg-slate-950/40 border border-slate-800/40 p-2.5 rounded-lg font-mono text-[11px] flex items-center justify-between gap-2 animate-fadeIn">
                      <div className="truncate flex-1"><div className="text-slate-200 font-bold truncate">📄 {file.filename}</div><div className="text-[9px] text-slate-500 mt-0.5">Partition ID #{file.id}</div></div>
                      <button type="button" onClick={(e) => { e.stopPropagation(); dispatchDocumentPurge(file.id); }} className="px-2 py-1 bg-red-950/30 hover:bg-red-900/40 text-red-400 border border-red-900/20 rounded font-bold text-[9px] transition">PURGE</button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
        
      </main>
    </div>
  );
}

export default App;