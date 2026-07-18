import React, { useState, useEffect } from 'react';

interface QueueItem {
  id: number;
  filename: string;
  status: string;
}

export const FileBulkUploadGrid: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadQueue, setUploadQueue] = useState<QueueItem[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const executeBulkUpload = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (selectedFiles.length === 0) return;
    setIsUploading(true);

    const formData = new FormData();
    selectedFiles.forEach((file) => {
      formData.append("files", file); 
    });

    try {
      const response = await fetch('http://localhost:8000/api/v1/ingestion/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        console.error(`❌ CONNECTION REFUSED: Ingestion node returned status ${response.status}`);
        return;
      }

      const data = await response.json();
      setUploadQueue(data.queue_manifest);

    } catch (err) {
      console.error('❌ FRONTEND TRANSMISSION FAULT:', err);
    } finally {
      setIsUploading(false);
    }
  };

  useEffect(() => {
    // 🎯 THE FIX: Keep polling ONLY if the status is not EMBEDDED, COMPLETED, AVAILABLE, or FAILED
    const activeProcessingIds = uploadQueue
      .filter(item => 
        item.status !== 'EMBEDDED' && 
        item.status !== 'COMPLETED' && 
        item.status !== 'AVAILABLE' && 
        item.status !== 'FAILED'
      )
      .map(item => item.id);

    if (activeProcessingIds.length === 0) {
      return;
    }

    const passiveTrackingTimer = setTimeout(async () => {
      try {
        const statusUpdatesBuffer = await Promise.all(
          activeProcessingIds.map(async (docId) => {
            try {
              const check = await fetch(`http://localhost:8000/api/v1/ingestion/status/${docId}`);
              if (!check.ok) return null;
              
              const report = await check.json();
              let pipelineStage = String(report.current_pipeline_stage).toUpperCase();
              
              if (pipelineStage.includes('DOCUMENTSTATUS.')) {
                pipelineStage = pipelineStage.replace('DOCUMENTSTATUS.', '');
              }
              return { id: docId, status: pipelineStage };
            } catch (innerErr) {
              return null;
            }
          })
        );

        setUploadQueue((currentQueue) =>
          currentQueue.map((item) => {
            const matchedUpdate = statusUpdatesBuffer.find((update) => update && update.id === item.id);
            return matchedUpdate ? { ...item, status: matchedUpdate.status } : item;
          })
        );

      } catch (err) {
        console.error('📡 POLLING SYSTEM EXCEPTION:', err);
      }
    }, 2000);

    return () => clearTimeout(passiveTrackingTimer);
  }, [uploadQueue]);

  const getStatusBadgeColor = (status: string) => {
    // 🎯 THE FIX: Render EMBEDDED with our emerald success layout styling attributes
    if (status === 'EMBEDDED' || status === 'COMPLETED' || status === 'AVAILABLE') {
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    }
    if (status === 'FAILED') {
      return 'bg-red-500/10 text-red-400 border-red-500/20';
    }
    if (status === 'PENDING') {
      return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    }
    return 'bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse';
  };

  return (
    <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-xl max-w-4xl mx-auto flex flex-col gap-6">
      <div className="border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-lg p-8 text-center cursor-pointer transition">
        <input type="file" multiple onChange={handleFileChange} className="hidden" id="bulk-file-input" />
        <label htmlFor="bulk-file-input" className="cursor-pointer text-slate-400 text-sm">
          <span>📁 Click to browse or drop an industrial folder batch container here</span>
        </label>
        {selectedFiles.length > 0 && (
          <div className="text-xs text-amber-400 font-mono mt-3">
            {selectedFiles.length} files selected for pipeline upload processing array.
          </div>
        )}
      </div>

      <button 
        type="button" 
        onClick={executeBulkUpload} 
        disabled={isUploading || selectedFiles.length === 0}
        className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-slate-800 disabled:to-slate-800 text-white font-semibold py-2.5 px-4 rounded-lg shadow-md transition"
      >
        {isUploading ? '⚡ Executing High-Throughput Socket Streams...' : '🚀 Initialize Bulk Ingestion Pipeline'}
      </button>

      {uploadQueue.length > 0 && (
        <div className="flex flex-col gap-2 mt-2">
          <h4 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Live Processing Ledger Queue</h4>
          {uploadQueue.map((item) => (
            <div key={item.id} className="bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 flex items-center justify-between font-mono text-sm">
              <span className="text-slate-200 truncate max-w-md">📄 {item.filename}</span>
              <span className={`px-2.5 py-0.5 rounded-full border text-xs font-medium ${getStatusBadgeColor(item.status)}`}>
                {item.status === 'EMBEDDED' ? 'COMPLETED' : item.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};