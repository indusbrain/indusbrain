import React, { useState, useEffect } from 'react';
import { FileBulkUploadGrid } from './components/FileBulkUploadGrid';
import { OperatorChatPanel } from './components/OperatorChatPanel';

interface FileEntry {
  id: number;
  filename: string;
  storage_path: string;
  uploaded_at: string;
}

interface AssetEntry {
  tag: string;
  name: string;
  type: string;
  status: string;
  health: string;
}

interface TelemetryState {
  infrastructure: { postgresql: string; neo4j: string; chromadb: string; ollama_qwen: string; };
  metrics: { total_documents: number; knowledge_score: number; documentation_completeness: number; compliance_health: number; };
  inventory: FileEntry[];
  assets: AssetEntry[];
}

function App() {
  const [telemetry, setTelemetry] = useState<TelemetryState>({
    infrastructure: { postgresql: 'OFFLINE', neo4j: 'OFFLINE', chromadb: 'OFFLINE', ollama_qwen: 'OFFLINE' },
    metrics: { total_documents: 0, knowledge_score: 0, documentation_completeness: 0, compliance_health: 0 },
    inventory: [],
    assets: []
  });

  const refreshDashboardMetrics = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/telemetry/dashboard');
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (err) {
      console.warn("Telemetry grid link sleeping.");
    }
  };

  // 🎯 CRUD ACTION: Sends an HTTP DELETE command to purge a document entry out of SQL tables
  const dispatchDocumentPurge = async (docId: number) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/telemetry/document/${docId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        // Trigger a metric scan refresh to update the UI tables instantly
        refreshDashboardMetrics();
      }
    } catch (err) {
      console.error("Failed to execute CRUD delete command:", err);
    }
  };

  // 🎯 CRUD ACTION: Simulated view/edit property parameters modal hook
  const triggerAssetUpdateAlert = (tag: string) => {
    alert(`🔧 CRITICAL OPERATIONS CRUD PROTOCOL:\n====================================\nOpening secure system parameter configurations mapping editor panel for Asset node: [${tag}].\n\n[Authorized Clearance Confirmed]`);
  };

  useEffect(() => {
    refreshDashboardMetrics();
    const metricsInterval = setInterval(refreshDashboardMetrics, 3500);
    return () => clearInterval(metricsInterval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased font-sans selection:bg-blue-500/20">
      
      {/* Header bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/20 px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <span className="text-xl">🧠</span>
          <h1 className="text-sm font-black tracking-widest bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent font-mono uppercase">
            IndusBrain Engine Operational Grid OS
          </h1>
        </div>
        
        {/* Status indicator lights */}
        <div className="flex flex-wrap items-center gap-4 font-mono text-[10px] text-slate-400 bg-slate-950 border border-slate-900 px-4 py-1.5 rounded-lg shadow-inner">
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${telemetry.infrastructure.postgresql === 'ONLINE' ? 'bg-emerald-500 shadow-[0_0_6px_#10b981]' : 'bg-red-500'}`}></span>
            <span>POSTGRES</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${telemetry.infrastructure.neo4j === 'ONLINE' ? 'bg-emerald-500 shadow-[0_0_6px_#10b981]' : 'bg-red-500'}`}></span>
            <span>NEO4J</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${telemetry.infrastructure.chromadb === 'ONLINE' ? 'bg-emerald-500 shadow-[0_0_6px_#10b981]' : 'bg-red-500'}`}></span>
            <span>CHROMA</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${telemetry.infrastructure.ollama_qwen === 'ONLINE' ? 'bg-emerald-500 shadow-[0_0_6px_#10b981]' : 'bg-red-500'}`}></span>
            <span>OLLAMA (QWEN)</span>
          </div>
        </div>
      </header>

      {/* Main Grid Viewport Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 flex flex-col gap-6">
        
        {/* ROW 1: System Telemetry Tiles */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/20 border border-slate-800/60 p-4 rounded-xl flex flex-col justify-between font-mono">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">System Knowledge DNA</span>
            <div className="flex items-baseline gap-1 mt-2">
              <span className="text-2xl font-black text-blue-400">{telemetry.metrics.knowledge_score}%</span>
            </div>
          </div>
          <div className="bg-slate-900/20 border border-slate-800/60 p-4 rounded-xl flex flex-col justify-between font-mono">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Extraction Completeness</span>
            <div className="flex items-baseline gap-1 mt-2">
              <span className="text-2xl font-black text-indigo-400">{telemetry.metrics.documentation_completeness}%</span>
            </div>
          </div>
          <div className="bg-slate-900/20 border border-slate-800/60 p-4 rounded-xl flex flex-col justify-between font-mono">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Compliance Margin</span>
            <div className="flex items-baseline gap-1 mt-2">
              <span className="text-2xl font-black text-purple-400">{telemetry.metrics.compliance_health}%</span>
            </div>
          </div>
          <div className="bg-slate-900/20 border border-slate-800/60 p-4 rounded-xl flex flex-col justify-between font-mono">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Knowledge Inventory</span>
            <div className="flex items-baseline gap-1 mt-2">
              <span className="text-2xl font-black text-emerald-400">{telemetry.metrics.total_documents}</span>
              <span className="text-[10px] text-slate-600 font-bold ml-1">FILES</span>
            </div>
          </div>
        </div>

        {/* ROW 2: Primary Operations Splitting Column Layout */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
          
          {/* LEFT 2 COLUMNS: Conversational Chat Logic Core */}
          <div className="xl:col-span-2 flex flex-col gap-6">
            <OperatorChatPanel />
            <FileBulkUploadGrid />
          </div>

          {/* RIGHT 1 COLUMN: Inventory & Asset Ledger Management Hub Panels */}
          <div className="flex flex-col gap-6">
            
            {/* PANEL A: Tracked Asset Entity Explorer Hub with Update CRUD hooks */}
            <div className="bg-slate-900/30 border border-slate-800/80 rounded-xl overflow-hidden backdrop-blur-md shadow-xl">
              <div className="px-4 py-3 bg-slate-950/60 border-b border-slate-800/80 font-mono text-xs text-slate-400 font-bold tracking-wider uppercase">
                ⚙️ Tracked Asset Entity Deck
              </div>
              <div className="p-4 flex flex-col gap-3 max-h-[220px] overflow-y-auto">
                {telemetry.assets.length === 0 ? (
                  <span className="text-xs font-mono text-slate-600 italic block text-center py-6">No active equipment entity indices loaded.</span>
                ) : (
                  telemetry.assets.map((asset, i) => (
                    <div 
                      key={i} 
                      onClick={() => triggerAssetUpdateAlert(asset.tag)}
                      className="bg-slate-950/80 border border-slate-800/60 hover:border-blue-500/40 p-3 rounded-lg flex items-center justify-between font-mono text-xs cursor-pointer transition"
                    >
                      <div>
                        <div className="text-blue-400 font-bold">{asset.tag}</div>
                        <div className="text-slate-500 text-[10px] font-sans mt-0.5">{asset.name}</div>
                      </div>
                      <div className="text-right">
                        <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${asset.status === 'Operational' ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/30' : 'bg-amber-950/40 text-amber-400 border border-amber-900/30'}`}>
                          {asset.status}
                        </span>
                        <div className="text-[9px] text-slate-600 mt-1 font-bold">{asset.health}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* PANEL B: Persistent Vault Knowledge Inventory History Ledger with Delete CRUD hooks */}
            <div className="bg-slate-900/30 border border-slate-800/80 rounded-xl overflow-hidden backdrop-blur-md shadow-xl">
              <div className="px-4 py-3 bg-slate-950/60 border-b border-slate-800/80 font-mono text-xs text-slate-400 font-bold tracking-wider uppercase">
                📚 Vault Document Ledger
              </div>
              <div className="p-4 flex flex-col gap-3 max-h-[220px] overflow-y-auto">
                {telemetry.inventory.length === 0 ? (
                  <span className="text-xs font-mono text-slate-600 italic block text-center py-6">No historical file records committed.</span>
                ) : (
                  telemetry.inventory.map((file) => (
                    <div key={file.id} className="bg-slate-950/40 border border-slate-800/40 p-2.5 rounded-lg font-mono text-[11px] flex items-center justify-between gap-2">
                      <div className="truncate flex-1">
                        <div className="text-slate-200 font-bold truncate">📄 {file.filename}</div>
                        <div className="text-[9px] text-slate-500 mt-0.5">{file.uploaded_at}</div>
                      </div>
                      {/* 🗑️ CRUD PURGE BUTTON ELEMENT */}
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); dispatchDocumentPurge(file.id); }}
                        className="px-2 py-1 bg-red-950/30 hover:bg-red-900/40 text-red-400 border border-red-900/20 rounded font-bold text-[9px] transition"
                      >
                        PURGE
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>

          {/* RIGHT 1 COLUMN (Placeholder column alignment block) */}
        </div>
        
      </main>
    </div>
  );
}

export default App;