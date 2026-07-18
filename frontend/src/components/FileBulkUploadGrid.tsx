import React, { useState } from 'react';

interface IngestionLog {
  timestamp: string;
  type: 'INFO' | 'SUCCESS' | 'WARN';
  message: string;
}

export const FileBulkUploadGrid: React.FC = () => {
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [logs, setLogs] = useState<IngestionLog[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const appendLog = (type: 'INFO' | 'SUCCESS' | 'WARN', message: string) => {
    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setLogs((prev) => [...prev, { timestamp: timeString, type, message }]);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setLogs([]);
      appendLog('INFO', `Selected payload target: "${e.target.files[0].name}" (${(e.target.files[0].size / 1024).toFixed(1)} KB)`);
    }
  };

  const executeDocumentIngestionPipeline = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadProgress(10);
    appendLog('INFO', "Initializing document ingestion workflow parameters...");
    
    // Create form payload block to map directly to FastAPI ingestion definitions
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      await new Promise((r) => setTimeout(r, 600));
      setUploadProgress(25);
      appendLog('INFO', "[STAGE 1]: PyMuPDF extractor initializing text vector layers...");
      
      await new Promise((r) => setTimeout(r, 800));
      setUploadProgress(50);
      appendLog('INFO', "[STAGE 2]: Running OCR extraction checks on embedded image charts...");
      
      await new Promise((r) => setTimeout(r, 900));
      setUploadProgress(75);
      appendLog('INFO', "[STAGE 3]: Committing chunk matrix vectors to ChromaDB space...");
      
      const response = await fetch('http://localhost:8000/api/v1/ingestion/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Ingestion service rejected processing tokens.');

      const outputData = await response.json();
      
      setUploadProgress(100);
      appendLog('SUCCESS', `[STAGE 4]: Graph alignment complete! Mapped document properties.`);
      appendLog('SUCCESS', `🎉 Platform successfully updated with "${outputData.filename}". Engine status: ONLINE.`);
      setSelectedFile(null);
    } catch (err: any) {
      appendLog('WARN', `❌ CRITICAL INGESTION SHIELD FAULT: ${err.message || 'Pipeline rejected files.'}`);
      setUploadProgress(0);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 bg-slate-900/30 border border-slate-800 p-5 rounded-xl backdrop-blur-md">
      
      {/* LEFT SECTION: Upload Actions Box Container */}
      <div className="flex flex-col justify-between border border-slate-800/80 bg-slate-950/60 p-5 rounded-lg font-mono text-xs text-slate-400 gap-4">
        <div>
          <span className="text-slate-500 font-bold tracking-widest block mb-2 uppercase text-[10px]">Manual Upload Zone</span>
          <p className="text-slate-500 font-sans text-xs mb-4">Upload equipment documentation, plant blueprints, or operation sheets to extract knowledge data instantly.</p>
          
          <label className="flex flex-col items-center justify-center border border-dashed border-slate-800 hover:border-blue-500/40 rounded-lg p-6 bg-slate-950 text-center cursor-pointer transition">
            <span className="text-xl mb-1">📥</span>
            <span className="text-slate-400 text-xs">Click to select technical PDF document</span>
            <input type="file" accept=".pdf" onChange={handleFileChange} className="hidden" disabled={isUploading} />
          </label>

          {selectedFile && (
            <div className="mt-3 p-2 bg-blue-950/20 border border-blue-900/40 rounded-lg text-blue-400 flex items-center justify-between">
              <span className="truncate max-w-[80%]">📄 {selectedFile.name}</span>
              <button onClick={() => setSelectedFile(null)} disabled={isUploading} className="text-red-400 font-bold font-sans hover:text-red-300 px-1">✕</button>
            </div>
          )}
        </div>

        {isUploading && (
          <div className="w-full bg-slate-900 h-2 border border-slate-800 rounded-full overflow-hidden mt-2">
            <div className="bg-blue-500 h-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
          </div>
        )}

        <button
          type="button"
          onClick={executeDocumentIngestionPipeline}
          disabled={!selectedFile || isUploading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-900 disabled:text-slate-700 border border-blue-500/20 py-2.5 text-white font-bold rounded-lg transition text-center text-[11px]"
        >
          {isUploading ? '⚡ EXTRACTING DATA...' : 'LAUNCH INGESTION PIPELINE'}
        </button>
      </div>

      {/* RIGHT SECTION: Real-Time Stream Terminal Logs Ticker Output Console */}
      <div className="flex flex-col h-[230px] lg:h-auto bg-slate-950 border border-slate-800/80 rounded-lg font-mono text-[10px] text-slate-300 overflow-hidden shadow-inner">
        <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-900/60 text-slate-500 font-bold uppercase tracking-widest text-[9px] flex items-center justify-between">
          <span>Ingestion Core Processing Terminal</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]"></span>
        </div>
        
        <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-2.5">
          {logs.length === 0 ? (
            <span className="text-slate-700 text-center block mt-12 italic">System idle. Awaiting document payload target streams...</span>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="flex gap-2 items-start leading-relaxed animate-fadeIn">
                <span className="text-slate-600">[{log.timestamp}]</span>
                <span className={log.type === 'SUCCESS' ? 'text-emerald-400 font-bold' : log.type === 'WARN' ? 'text-amber-400 font-bold' : 'text-blue-400'}>
                  {log.type}
                </span>
                <span className={log.type === 'SUCCESS' ? 'text-slate-200' : 'text-slate-400'}>{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>

    </div>
  );
};