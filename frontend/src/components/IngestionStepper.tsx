import React, { useState } from 'react';
import { apiService } from '../services/api';
import { Upload, CheckCircle, Loader2, AlertCircle } from 'lucide-react';

export const IngestionStepper: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [currentStep, setCurrentStep] = useState<number>(-1);
  const [stepStatus, setStepStatus] = useState<'idle' | 'processing' | 'success' | 'error'>('idle');
  const [logs, setLogs] = useState<string[]>([]);
  const [docId, setDocId] = useState<number | null>(null);

  const steps = [
    { label: "Upload Asset", action: async (f: File) => {
      const res = await apiService.uploadDocument(f);
      setDocId(res.id);
      return `[POST /upload] Success. Document registered with ID: ${res.id}`;
    }},
    { label: "Layout Parsing (OCR)", action: async () => {
      const res = await apiService.parseDocument(docId!);
      return `[POST /parse] Completed. Processed ${res.character_count_processed} characters.`;
    }},
    { label: "Cognitive Chunking", action: async () => {
      const res = await apiService.chunkDocument(docId!);
      return `[POST /chunk] Segmented into ${res.total_semantic_chunks_generated} segments.`;
    }},
    { label: "Vector Indexing", action: async () => {
      const res = await apiService.embedDocument(docId!);
      return `[POST /embed] Populated ChromaDB with ${res.total_vectors_indexed} vectors.`;
    }},
    { label: "Graph Topology Sync", action: async () => {
      const res = await apiService.graphDocument(docId!);
      return `[POST /graph] Mapped ${res.total_nodes_synced} nodes in Neo4j.`;
    }}
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
  };

  const executePipeline = async () => {
    if (!file) return;
    setLogs([]);
    setStepStatus('processing');
    
    let currentFile = file;
    for (let i = 0; i < steps.length; i++) {
      setCurrentStep(i);
      try {
        setLogs(prev => [...prev, `⚙️ Initiating: ${steps[i].label}...`]);
        const logMsg = i === 0 ? await steps[i].action(currentFile) : await steps[i].action(null as any);
        setLogs(prev => [...prev, `🟢 ${logMsg}`]);
      } catch (err: any) {
        setStepStatus('error');
        setLogs(prev => [...prev, `🔴 Failed at [${steps[i].label}]: ${err.message}`]);
        return;
      }
    }
    setStepStatus('success');
  };

  return (
    <div className="bg-industrial-dark p-6 rounded-lg border border-industrial-border">
      <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-industrial-accent">
        <Upload className="w-5 h-5" /> Ingestion Control Panel
      </h2>
      
      <div className="border-2 border-dashed border-industrial-border rounded-lg p-6 text-center hover:border-industrial-accent transition-colors cursor-pointer mb-6">
        <input type="file" id="pdf-upload" className="hidden" accept=".pdf" onChange={handleFileChange} />
        <label htmlFor="pdf-upload" className="cursor-pointer">
          <Upload className="w-10 h-10 mx-auto mb-2 text-gray-500" />
          <span className="block text-sm font-semibold text-gray-300">
            {file ? file.name : "Select or Drop Technical PDF Manual"}
          </span>
        </label>
      </div>

      {file && stepStatus !== 'processing' && (
        <button 
          onClick={executePipeline}
          className="w-full bg-industrial-accent text-industrial-darkest font-bold py-2 px-4 rounded-lg hover:bg-white transition-colors cursor-pointer"
        >
          Initialize Pipeline
        </button>
      )}

      {currentStep >= 0 && (
        <div className="mt-6 space-y-4">
          {steps.map((step, idx) => (
            <div key={idx} className="flex items-center gap-3">
              {idx < currentStep ? (
                <CheckCircle className="w-5 h-5 text-industrial-terminal" />
              ) : idx === currentStep && stepStatus === 'processing' ? (
                <Loader2 className="w-5 h-5 text-industrial-accent animate-spin" />
              ) : idx === currentStep && stepStatus === 'error' ? (
                <AlertCircle className="w-5 h-5 text-red-500" />
              ) : (
                <div className="w-5 h-5 rounded-full border border-industrial-border flex items-center justify-center text-xs font-bold text-gray-500">
                  {idx + 1}
                </div>
              )}
              <span className={`text-sm ${idx === currentStep ? 'text-white font-semibold' : 'text-gray-400'}`}>
                {step.label}
              </span>
            </div>
          ))}
        </div>
      )}

      {logs.length > 0 && (
        <div className="mt-6 bg-industrial-darkest p-4 rounded-lg font-mono text-xs space-y-1 h-40 overflow-y-auto border border-industrial-border text-industrial-terminal">
          {logs.map((log, index) => (
            <div key={index}>{log}</div>
          ))}
        </div>
      )}
    </div>
  );
};