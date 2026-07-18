import React from 'react';
// 🟢 Link our new multi-file background streaming dropzone component
import { FileBulkUploadGrid } from './components/FileBulkUploadGrid';
// 🟢 Link our brand new Phase 9.2 cross-document anomaly detection alert panel
import { ConflictAlertPanel } from './components/ConflictAlertPanel';

function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased selection:bg-blue-500/20 selection:text-blue-300">
      
      {/* 🌌 Master Global Top Layout Navigation Bar Banner */}
      <header className="border-b border-slate-800 bg-slate-900/40 px-8 py-4 flex items-center justify-between backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <span className="text-xl">🧠</span>
          <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
            IndusBrain Engine Tectonic Control Center
          </h1>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1 rounded-md">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          LOCAL PIPELINE ONLINE
        </div>
      </header>

      {/* 🎛️ Master Dynamic Dashboard Content Layout Grid */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-6 flex flex-col gap-6">
        
        {/* SECTION A: Phase 9.2 Cross-Document Multi-File Parameter Discrepancy Audits */}
        <section className="w-full">
          <ConflictAlertPanel />
        </section>

        {/* SECTION B: Stage 1 Multi-File Asynchronous Streaming Dropzone Grid */}
        <section className="w-full flex flex-col gap-2">
          <div className="mb-2 bg-slate-900/40 border border-slate-800/80 p-4 rounded-xl shadow-inner">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">Knowledge Asset Base Ingestion</h2>
            <p className="text-xs text-slate-500 mt-1">Pipes gigabyte multi-page vendor manuals concurrently across hardware sub-processes safely.</p>
          </div>
          <FileBulkUploadGrid />
        </section>

        {/* SECTION C: Multi-Agent Conversational Workflow Loop Sandbox */}
        <section className="w-full bg-slate-900/30 border border-slate-800 rounded-xl p-5 min-h-[180px] flex flex-col items-center justify-center text-slate-600 text-xs font-mono gap-1 border-dashed shadow-inner">
          <span className="text-lg">💬</span>
          <span>[ PHASE 10 MULTI-AGENT RETRIEVAL SANDBOX CONTAINER ]</span>
          <span className="text-[10px] text-slate-700 font-normal">Decoupled data streams verified. Ready for query-space integration.</span>
        </section>
        
      </main>
    </div>
  );
}

export default App;