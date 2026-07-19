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
  
  // 🎯 THE FIX: Track multiple files simultaneously inside a structured state array
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const appendLog = (type: 'INFO' | 'SUCCESS' | 'WARN', message: string) => {
    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setLogs((prev) => [...prev, { timestamp: timeString, type, message }]);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      setSelectedFiles((prev) => [...prev, ...filesArray]);
      
      filesArray.forEach((f) => {
        appendLog('INFO', `Added batch target payload: "${f.name}" (${(f.size / 1024).toFixed(1)} KB)`);
      });
    }
  };

  const executeDocumentIngestionPipeline = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setUploadProgress(15);
    appendLog('INFO', `Initializing parallel batch ingestion for ${selectedFiles.length} documents...`);
    
    // Construct single Multi-Part network payload matrix
    const formData = new FormData();
    selectedFiles.forEach((file) => {
      // 🎯 THE FIX: Append files under the 'files' field key to align with backend endpoints
      formData.append('files', file); 
    });

    try {
      await new Promise((r) => setTimeout(r, 400));
      setUploadProgress(35);
      appendLog('INFO', "[STAGE 1]: Allocating file streams across background process workers...");
      
      await new Promise((r) => setTimeout(r, 500));
      setUploadProgress(65);
      appendLog('INFO', "[STAGE 2]: Running automated computer vision text and schema extractions...");
      
      await new Promise((r) => setTimeout(r, 600));
      setUploadProgress(85);
      appendLog('INFO', "[STAGE 3]: Synchronizing parallel vector space indexing configurations...");

      const response = await fetch('http://localhost:8000/api/v1/ingestion/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Ingestion pipeline endpoint rejected the payload batch tokens.');

      const outputData = await response.json();
      
      setUploadProgress(100);
      appendLog('SUCCESS', `🎉 BATCH SUCCESS: Processed files successfully.`);
      appendLog('SUCCESS', `System status tracking updated. Active elements compiled into stores.`);
      setSelectedFiles([]);
    } catch (err: any) {
      appendLog('WARN', `❌ CRITICAL INGESTION BLOCK FAULT: ${err.message || 'Pipeline process broken.'}`);
      setUploadProgress(0);
    } finally {
      setIsUploading(false);
    }
  };

  const removeFileFromBatchQueue = (indexToRemove: number) => {
    setSelectedFiles((prev) => prev.filter((_, idx) => idx !== indexToRemove));
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 bg-slate-900/30 border border-slate-800 p-5 rounded-xl backdrop-blur-md">
      
      {/* LEFT SECTION: Advanced Multiple Files Selection Zone */}
      <div className="flex flex-col justify-between border border-slate-800/80 bg-slate-950/60 p-5 rounded-lg font-mono text-xs text-slate-400 gap-4">
        <div>
          <span className="text-slate-500 font-bold tracking-widest block mb-2 uppercase text-[10px]">Industrial Batch Upload Center</span>
          <p className="text-slate-500 font-sans text-xs mb-4">Queue multiple vendor specifications sheets, engineering drawings, or compliance manuals for parallel extraction processing passes.</p>
          
          <label className="flex flex-col items-center justify-center border border-dashed border-slate-800 hover:border-blue-500/40 rounded-lg p-6 bg-slate-950 text-center cursor-pointer transition">
            <span className="text-xl mb-1">📥</span>
            <span className="text-slate-400 text-xs">Click to choose manual files</span>
            {/* 🎯 THE FIX: Incorporated HTML5 multiple attribute descriptor tags */}
            <input type="file" accept=".pdf" onChange={handleFileChange} className="hidden" multiple disabled={isUploading} />
          </label>

          {/* Render files item rows with single element remove capabilities */}
          {selectedFiles.length > 0 && (
            <div className="mt-3 flex flex-col gap-2 max-h-[140px] overflow-y-auto pr-1">
              {selectedFiles.map((file, i) => (
                <div key={i} className="p-2 bg-blue-950/20 border border-blue-900/40 rounded-lg text-blue-400 flex items-center justify-between animate-fadeIn">
                  <span className="truncate max-w-[85%]">📄 {file.name}</span>
                  <button 
                    type="button" 
                    onClick={() => removeFileFromBatchQueue(i)} 
                    disabled={isUploading}
                    className="text-red-400 font-bold font-sans hover:text-red-300 transition"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {isUploading && (
          <div className="w-full bg-slate-900 h-2 border border-slate-800 rounded-full overflow-hidden mt-1">
            <div className="bg-blue-500 h-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
          </div>
        )}

        <button
          type="button"
          onClick={executeDocumentIngestionPipeline}
          disabled={selectedFiles.length === 0 || isUploading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-900 disabled:text-slate-700 border border-blue-500/20 py-2.5 text-white font-bold rounded-lg transition text-center text-[11px]"
        >
          {isUploading ? '⚡ DISTRIBUTING COMPUTE BATCH...' : `LAUNCH PARALLEL INGESTION [${selectedFiles.length} FILES]`}
        </button>
      </div>

      {/* RIGHT SECTION: Logs terminal block */}
      <div className="flex flex-col h-[240px] lg:h-auto bg-slate-950 border border-slate-800/80 rounded-lg font-mono text-[10px] text-slate-300 overflow-hidden shadow-inner">
        <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-900/60 text-slate-500 font-bold uppercase tracking-widest text-[9px] flex items-center justify-between">
          <span>Ingestion Core Processing Terminal</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]"></span>
        </div>
        
        <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-2.5">
          {logs.length === 0 ? (
            <span className="text-slate-700 text-center block mt-12 italic">System clean. Awaiting target industrial manual streams...</span>
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