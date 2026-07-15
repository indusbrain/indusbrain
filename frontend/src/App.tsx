import { useState } from 'react';
import { IngestionStepper } from './components/IngestionStepper';
import { TerminalConsole } from './components/TerminalConsole';
import { ExecutiveReport } from './components/ExecutiveReport';
import type { QueryResponse } from './services/api';
import { Shield } from 'lucide-react';

function App() {
  const [report, setReport] = useState<QueryResponse | null>(null);

  return (
    <div className="min-h-screen bg-industrial-darkest flex flex-col text-gray-200">
      {/* Top Header Controls */}
      <header className="border-b border-industrial-border bg-industrial-dark py-4 px-6 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="bg-industrial-accent/15 p-2 rounded-lg text-industrial-accent">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
              IndusBrain <span className="text-xs bg-industrial-accent/15 text-industrial-accent font-semibold px-2 py-0.5 rounded">v1.0.0</span>
            </h1>
            <p className="text-[10px] text-gray-500 tracking-wider">INDUSTRIAL KNOWLEDGE OPERATING CORE ENGINE</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-industrial-terminal animate-pulse"></div>
          <span className="text-xs font-mono text-gray-400">SYSTEM STATUS: OPTIMAL // PORT 8000</span>
        </div>
      </header>

      {/* Main Grid View */}
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: File Loader */}
        <div className="lg:col-span-1">
          <IngestionStepper />
        </div>

        {/* Right Columns: Interactive Workspace split into Console + Report */}
        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">
          <TerminalConsole onResultReceived={setReport} />
          <ExecutiveReport report={report} />
        </div>
      </main>
    </div>
  );
}

export default App;