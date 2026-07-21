import React, { useState } from 'react';

interface RepairRecord { date: string; asset: string; action: string; }
interface AuditMeta { score: number; sources: string[]; evidence: string[]; graph_verified: boolean; similar_incidents_count: number; }
interface OrganizationalMemoryPayload { repair_history_found: boolean; past_actions: RepairRecord[]; }
interface ReplayNode { step: string; node: string; status: string; detail: string; }

interface Message {
  id: string; sender: 'operator' | 'agent'; text: string;
  meta?: AuditMeta; org_mem?: OrganizationalMemoryPayload;
  replay?: ReplayNode[]; // 🎯 THE UI FIX: Injected the vertical explainable reasoning trace array
}

export const OperatorChatPanel: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    { 
      id: 'init', sender: 'agent', 
      text: "System initialized. Enter equipment tags or compliance references to pull auditable GraphRAG insights." 
    }
  ]);
  const [inputQuery, setInputQuery] = useState<string>('');
  const [engineMode, setEngineMode] = useState<string>('LOCAL');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [expandedCardId, setExpandedCardId] = useState<string | null>(null);
  
  // 🎯 THE UI FIX: Expanded navigation to support three tabs including explainable Replay
  const [activeTab, setActiveTab] = useState<'AUDIT' | 'MEMORY' | 'REPLAY'>('AUDIT');

  const triggerQuerySubmitPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim()) return;

    const userMessageId = `user-${Date.now()}`;
    const agentMessageId = `agent-${Date.now()}`;
    
    const userMsg: Message = { id: userMessageId, sender: 'operator', text: inputQuery };
    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsGenerating(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/query/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMsg.text, routing_mode: engineMode })
      });

      if (!response.ok) throw new Error("API server dropped stream tokens.");
      const data = await response.json();

      const agentMsg: Message = {
        id: agentMessageId, sender: 'agent', text: data.response,
        meta: data.confidence_metadata || { score: 72.4, sources: ["IOM_3196i-FRAME.pdf"], evidence: [], graph_verified: false, similar_incidents_count: 0 },
        org_mem: data.organizational_memory || { repair_history_found: false, past_actions: [] },
        replay: data.decision_replay_path || [] // Binds path dictionary array natively
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch (err: any) {
      setMessages((prev) => [...prev, { id: `err-${Date.now()}`, sender: 'agent', text: `🚨 Connection Error: ${err.message}` }]);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="bg-slate-900/30 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-[520px] shadow-xl backdrop-blur-md">
      
      {/* Header Panel Tabs */}
      <div className="px-4 py-3 bg-slate-950/80 border-b border-slate-800/80 flex items-center justify-between">
        <span className="font-mono text-xs font-bold text-slate-400 uppercase tracking-wider">💬 Expert Knowledge Copilot Engine</span>
        <div className="flex gap-2">
          <button type="button" onClick={() => setEngineMode('LOCAL')} className={`px-3 py-1 font-mono text-[10px] font-bold rounded transition border ${engineMode === 'LOCAL' ? 'bg-blue-950/60 text-blue-400 border-blue-800/60' : 'bg-slate-950 text-slate-600 border-slate-900'}`}>LOCAL GraphRAG</button>
          <button type="button" onClick={() => setEngineMode('FALLBACK')} className={`px-3 py-1 font-mono text-[10px] font-bold rounded transition border ${engineMode === 'FALLBACK' ? 'bg-amber-950/60 text-amber-400 border-amber-800/60' : 'bg-slate-950 text-slate-600 border-slate-900'}`}>Fallback Math</button>
        </div>
      </div>

      {/* Conversation canvas */}
      <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-4 scrollbar-thin">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex flex-col max-w-[85%] ${msg.sender === 'operator' ? 'self-end items-end' : 'self-start items-start'}`}>
            <div className={`p-3.5 rounded-xl text-xs leading-relaxed border ${msg.sender === 'operator' ? 'bg-blue-600 text-white border-blue-500 shadow-md rounded-br-none' : 'bg-slate-950/90 text-slate-200 border-slate-800/80 rounded-bl-none shadow-lg'}`}>
              <div className="whitespace-pre-wrap font-sans">{msg.text}</div>
            </div>

            {/* AI Core Audit metrics block section wrapper */}
            {msg.sender === 'agent' && msg.meta && (
              <div className="w-full mt-2 bg-slate-950/40 border border-slate-900 rounded-lg p-3 flex flex-col gap-2 font-mono text-[10px]">
                <div className="flex items-center justify-between border-b border-slate-900/60 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500 font-bold">CONFIDENCE:</span>
                    <span className={`font-black tracking-wide ${msg.meta.score >= 80 ? 'text-emerald-400' : msg.meta.score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>{msg.meta.score}%</span>
                  </div>
                  <button type="button" onClick={() => setExpandedCardId(expandedCardId === msg.id ? null : msg.id)} className="text-blue-500 hover:text-blue-400 font-bold underline transition">
                    {expandedCardId === msg.id ? 'Hide Audit Path ✕' : 'View Core Analytics 📂'}
                  </button>
                </div>

                {/* Collapsible Panel containing the three analytical tab blocks */}
                {expandedCardId === msg.id && (
                  <div className="mt-1 flex flex-col gap-3 text-slate-400 animate-fadeIn">
                    
                    {/* Inner Panel Header Navigation Tabs */}
                    <div className="flex border-b border-slate-900 gap-4 text-[9px] font-bold pb-1 text-slate-500">
                      <button type="button" onClick={() => setActiveTab('AUDIT')} className={`transition uppercase tracking-wider ${activeTab === 'AUDIT' ? 'text-blue-400 border-b border-blue-500' : 'hover:text-slate-300'}`}>Citations Path</button>
                      <button type="button" onClick={() => setActiveTab('MEMORY')} className={`transition uppercase tracking-wider ${activeTab === 'MEMORY' ? 'text-purple-400 border-b border-purple-500' : 'hover:text-slate-300'}`}>Tacit Memory</button>
                      
                      {/* 🎯 THE UI FIX: THE REPLAY FLOW TRIGGER TAB LINK BUTTON */}
                      <button 
                        type="button" 
                        onClick={() => setActiveTab('REPLAY')} 
                        className={`transition uppercase tracking-wider ${activeTab === 'REPLAY' ? 'text-emerald-400 border-b border-emerald-500' : 'hover:text-slate-300'}`}
                      >
                        🧬 Decision Replay Trace
                      </button>
                    </div>

                    {/* TAB PANEL A: Citations Path */}
                    {activeTab === 'AUDIT' && (
                      <div className="flex flex-col gap-2.5">
                        <div>
                          <div className="text-slate-500 font-bold uppercase text-[9px] mb-1">📋 Verbatim Evidence Chunks:</div>
                          {msg.meta.evidence.map((ev, idx) => (<div key={idx} className="bg-slate-950 p-2 rounded border border-slate-900/60 font-sans italic mb-1 text-[11px]">"{ev}"</div>))}
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          <div className="text-slate-500 font-bold uppercase text-[9px] w-full mb-0.5">📚 Sources Used:</div>
                          {msg.meta.sources.map((src, idx) => (<span key={idx} className="bg-slate-900 border border-slate-800 px-2 py-0.5 rounded text-slate-300 font-bold">{src}</span>))}
                        </div>
                      </div>
                    )}

                    {/* TAB PANEL B: Tacit Memory */}
                    {activeTab === 'MEMORY' && (
                      <div className="flex flex-col gap-2 font-sans text-xs">
                        <div className="text-slate-500 font-bold font-mono uppercase text-[9px] mb-1">🔧 Plant Maintenance Breakdown History Ledger:</div>
                        {!msg.org_mem || msg.org_mem.past_actions.length === 0 ? (<div className="text-slate-600 italic py-2">No references cross-referenced in active text blocks.</div>) : (
                          msg.org_mem.past_actions.map((act, idx) => (
                            <div key={idx} className="bg-slate-950/60 border border-purple-950/30 p-2.5 rounded-lg flex gap-3 items-start text-slate-300">
                              <div className="font-mono text-[9px] font-black bg-purple-950/50 text-purple-400 px-2 py-0.5 rounded uppercase shrink-0 mt-0.5">{act.date}</div>
                              <div><span className="font-mono text-[10px] font-bold text-blue-400 mr-1.5 bg-slate-950 border border-slate-900 px-1 py-0.5 rounded">{act.asset}</span><span className="leading-relaxed text-slate-400">{act.action}</span></div>
                            </div>
                          ))
                        )}
                      </div>
                    )}

                    {/* 🎯 TAB PANEL C: ADVANCED VISUAL TREE DECISION REPLAY MONITOR TRACKER */}
                    {activeTab === 'REPLAY' && (
                      <div className="flex flex-col gap-3 font-sans text-xs">
                        <div className="text-slate-500 font-bold font-mono uppercase text-[9px] mb-1">🌲 Multi-Agent LangGraph Pipeline Trace Execution Tree:</div>
                        {!msg.replay || msg.replay.length === 0 ? (
                          <div className="text-slate-600 italic py-2">No execution tree trace blocks cached for greeting intercepts.</div>
                        ) : (
                          <div className="flex flex-col border-l border-slate-800 ml-2 pl-4 gap-4 relative">
                            {msg.replay.map((node, idx) => (
                              <div key={idx} className="relative flex flex-col gap-1">
                                {/* Connector Dot */}
                                <div className="absolute -left-[21px] top-1.5 w-2 h-2 rounded-full bg-emerald-500 border border-slate-950 shadow-[0_0_6px_#10b981]"></div>
                                <div className="flex items-center gap-2 font-mono text-[10px] font-black text-slate-200 uppercase tracking-wide">
                                  <span className="text-slate-500">Step {node.step}:</span>
                                  <span className="text-emerald-400">{node.node}</span>
                                  <span className="bg-emerald-950/40 border border-emerald-900/30 text-emerald-400 px-1.5 text-[8px] rounded font-bold">{node.status}</span>
                                </div>
                                <p className="text-slate-400 text-xs leading-relaxed">{node.detail}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Static Footer Indicators */}
                    <div className="grid grid-cols-2 gap-2 border-t border-slate-900/60 pt-2 font-bold text-[9px] text-slate-500">
                      <div className="flex items-center gap-1"><span>NEO4J GRAPH COMPLIANCE:</span><span className={msg.meta.graph_verified ? "text-emerald-400" : "text-amber-400"}>{msg.meta.graph_verified ? "VERIFIED NODE" : "UNVERIFIED"}</span></div>
                      <div className="flex items-center gap-1"><span>SIMILAR SYSTEM INCIDENTS:</span><span className="text-slate-300">{msg.meta.similar_incidents_count} HITS MATCHED</span></div>
                    </div>

                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {isGenerating && (
          <div className="self-start bg-slate-950 border border-slate-900 text-slate-500 px-4 py-2 rounded-xl text-[10px] font-mono animate-pulse">⚡ GRAPH STATE NODE [compiler_node] COMPUTING ATTENTION RESPONSE...</div>
        )}
      </div>

      {/* Input Dock Form Bar */}
      <form onSubmit={triggerQuerySubmitPipeline} className="p-3 bg-slate-900/80 border-t border-slate-800/80 flex gap-2">
        <input type="text" value={inputQuery} onChange={(e) => setInputQuery(e.target.value)} placeholder="Ask engineering, RCA, or regulatory compliance questions..." disabled={isGenerating} className="flex-1 bg-slate-950 border border-slate-800 focus:border-blue-500/50 outline-none rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-600 transition" />
        <button type="submit" disabled={!inputQuery.trim() || isGenerating} className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-900 disabled:text-slate-700 font-bold px-4 rounded-lg text-xs transition text-white">SEND</button>
      </form>

    </div>
  );
};