import React, { useState } from 'react';
import type { apiService, QueryResponse } from '../services/api';
import { Terminal, Cpu, Loader2 } from 'lucide-react';

export const TerminalConsole: React.FC<{ onResultReceived: (res: QueryResponse) => void }> = ({ onResultReceived }) => {
  const [query, setQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [commandHistory, setCommandHistory] = useState<{ q: string, rPath: string[] }[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    try {
      const responseData = await apiService.submitQuery(query);
      setCommandHistory(prev => [...prev, { q: query, rPath: responseData.reasoning_path }]);
      onResultReceived(responseData);
      setQuery("");
    } catch (err: any) {
      alert("Analysis failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-industrial-dark p-6 rounded-lg border border-industrial-border flex flex-col h-full">
      <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-industrial-terminal">
        <Terminal className="w-5 h-5" /> Live Agent Operations Console
      </h2>

      <div className="flex-1 bg-industrial-darkest p-4 rounded-lg font-mono text-xs space-y-4 overflow-y-auto min-h-[300px] max-h-[400px] border border-industrial-border">
        <div className="text-gray-500 border-b border-industrial-border pb-2">
          SYSTEM ONLINE // MULTI-AGENT STATE ENGINE ROUTERS CONNECTED
        </div>
        
        {commandHistory.map((item, index) => (
          <div key={index} className="space-y-2">
            <div className="text-white flex items-center gap-1">
              <span className="text-industrial-accent">operator$</span> {item.q}
            </div>
            <div className="text-gray-400 pl-4 space-y-1">
              {item.rPath.map((step, sIdx) => (
                <div key={sIdx} className="flex items-center gap-1 text-[10px]">
                  <Cpu className="w-3 h-3 text-industrial-terminal" /> 
                  <span className="text-industrial-terminal">LOG:</span> {step}
                </div>
              ))}
            </div>
          </div>
        ))}

        {loading && (
          <div className="text-industrial-accent animate-pulse flex items-center gap-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Thinking...
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input 
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask system specs, maintenance dates, safety standards..."
          className="flex-1 bg-industrial-darkest text-white border border-industrial-border rounded-lg py-2.5 px-4 font-mono text-sm focus:outline-none focus:border-industrial-accent"
        />
        <button 
          type="submit" 
          className="bg-industrial-terminal text-industrial-darkest font-bold py-2.5 px-6 rounded-lg hover:bg-white transition-colors text-sm cursor-pointer"
        >
          SUBMIT
        </button>
      </form>
    </div>
  );
};