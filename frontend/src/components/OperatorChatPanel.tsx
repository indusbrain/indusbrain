import React, { useState, useRef, useEffect } from 'react';

interface ChatMessage {
  id: string;
  sender: 'operator' | 'agent';
  text: string;
  timestamp: string;
}

type RoutingMode = 'LOCAL' | 'CLOUD' | 'INTERNAL';

export const OperatorChatPanel: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState<string>('');
  const [isStreaming, setIsUploading] = useState<boolean>(false);
  const [activeMode, setActiveMode] = useState<RoutingMode>('LOCAL');
  
  const [currentSessionId, setCurrentSessionId] = useState<string>(() => {
    return localStorage.getItem('ikip_active_session_token') || '';
  });

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  // 🎯 THE PERMANENT SCROLL FIX: Calculate scroll offsets directly inside the text update frame lifecycle
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // Check if the user is currently resting near the bottom area (within a 100px tolerance window)
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    const isRestingAtBottom = distanceFromBottom < 100;

    // ONLY force scroll alignment if they are already at the bottom. If they scrolled up to read, leave it alone!
    if (isRestingAtBottom) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages]);

  const dispatchStreamingQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isStreaming) return;

    const userQueryText = inputQuery.trim();
    setInputQuery('');
    setIsUploading(true);

    const operatorMessageId = `op_${Date.now()}`;
    const agentMessageId = `agent_${Date.now()}`;

    setMessages((prev) => [...prev, {
      id: operatorMessageId,
      sender: 'operator',
      text: userQueryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);

    setMessages((prev) => [...prev, { 
      id: agentMessageId, 
      sender: 'agent', 
      text: '', 
      timestamp: 'Processing...' 
    }]);

    try {
      const response = await fetch('http://localhost:8000/api/v1/query/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: userQueryText,
          routing_mode: activeMode,
          session_id: currentSessionId
        })
      });

      if (!response.ok || !response.body) {
        setIsUploading(false);
        return;
      }

      const streamReader = response.body.getReader();
      const textDecoder = new TextDecoder();
      let accumulatedResponseText = '';

      // Snap scroller down immediately at response initialization
      if (scrollContainerRef.current) {
        scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
      }

      while (true) {
        const { value, done } = await streamReader.read();
        if (done) break;

        const textChunkFragment = textDecoder.decode(value, { stream: true });
        const linesArray = textChunkFragment.split('\n');
        
        for (const line of linesArray) {
          if (line.startsWith('data: ')) {
            const cleanTokenWord = line.replace('data: ', '');
            
            if (cleanTokenWord.trim().startsWith('__SESSION_ID__:')) {
              const isolatedToken = cleanTokenWord.trim().replace('__SESSION_ID__:', '');
              localStorage.setItem('ikip_active_session_token', isolatedToken);
              setCurrentSessionId(isolatedToken);
              continue;
            }

            accumulatedResponseText += cleanTokenWord + ' ';

            setMessages((currentMessagesList) =>
              currentMessagesList.map((msg) =>
                msg.id === agentMessageId
                  ? { 
                      ...msg, 
                      text: accumulatedResponseText,
                      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    }
                  : msg
              )
            );
          }
        }
      }
    } catch (err) {
      console.error('❌ RUNTIME RETRIEVAL EXCEPTION:', err);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSessionReset = () => {
    localStorage.removeItem('ikip_active_session_token');
    setCurrentSessionId('');
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-[520px] bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden backdrop-blur-md shadow-2xl">
      
      {/* Header Panel Control Bar Strip */}
      <div className="px-5 py-3 border-b border-slate-800/80 bg-slate-950/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-mono text-xs">
        <div className="flex items-center gap-2 text-slate-400">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
          <span>LANGGRAPH AGENT CORES CONTROLS</span>
          {currentSessionId && <span className="text-[10px] text-emerald-500 font-bold ml-1">🔒 [PERSISTENT SESSION ACTIVE]</span>}
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-900 border border-slate-800 p-0.5 rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => setActiveMode('LOCAL')}
              disabled={isStreaming}
              className={`px-3 py-1 rounded-md text-[10px] font-bold tracking-wider transition uppercase ${activeMode === 'LOCAL' ? 'bg-blue-600 text-white shadow' : 'text-slate-500 hover:text-slate-300'}`}
            >
              🤖 Local (Ollama)
            </button>
            <button
              type="button"
              onClick={() => setActiveMode('INTERNAL')}
              disabled={isStreaming}
              className={`px-3 py-1 rounded-md text-[10px] font-bold tracking-wider transition uppercase ${activeMode === 'INTERNAL' ? 'bg-amber-600/90 text-white shadow' : 'text-slate-500 hover:text-slate-300'}`}
            >
              🔧 Fallback Math
            </button>
          </div>

          {currentSessionId && (
            <button
              type="button"
              onClick={handleSessionReset}
              disabled={isStreaming}
              className="px-2.5 py-1 bg-red-950/40 hover:bg-red-900/40 text-red-400 border border-red-900/30 rounded-lg text-[10px] font-bold font-mono transition"
            >
              🔄 RESET SESSION
            </button>
          )}
        </div>
      </div>

      {/* Chat Messages Scrolling Frame */}
      <div 
        ref={scrollContainerRef}
        className="flex-1 p-5 overflow-y-auto flex flex-col gap-4 scrollbar-thin scrollbar-thumb-slate-800 selection:bg-blue-500/30"
      >
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500 font-mono text-xs text-center gap-2">
            <span>🛡️ AUDIT-READY SESSION PERSISTENCE ACTIVE</span>
            <span className="text-[10px] text-slate-600 max-w-xs font-normal">Dialogue rows are securely logged to disk, ensuring context memory survives full reboots.</span>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={`flex flex-col max-w-[85%] ${message.sender === 'operator' ? 'self-end items-end' : 'self-start items-start'}`}>
              <div className={`px-4 py-2.5 rounded-xl text-sm leading-relaxed whitespace-pre-wrap ${message.sender === 'operator' ? 'bg-blue-600 text-white rounded-tr-none shadow-md' : 'bg-slate-950/90 text-slate-200 border border-slate-800/80 rounded-tl-none font-mono text-xs shadow-inner'}`}>
                {message.text || '⚡ Resolving Intent Graph...'}
              </div>
              <span className="text-[10px] font-mono text-slate-500 mt-1 px-1">{message.timestamp}</span>
            </div>
          ))
        )}
      </div>

      {/* Input Form command field */}
      <form onSubmit={dispatchStreamingQuery} className="p-4 border-t border-slate-800/80 bg-slate-950/40 flex gap-3">
        <input 
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          disabled={isStreaming}
          placeholder="Enter technical query prompt..."
          className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm font-mono placeholder:text-slate-700 focus:outline-none focus:border-blue-500/40 text-slate-100 transition disabled:opacity-40"
        />
        <button 
          type="submit"
          disabled={isStreaming || !inputQuery.trim()}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-800 disabled:text-slate-600 border border-blue-500/20 px-6 rounded-lg text-white font-mono text-xs font-bold transition flex items-center justify-center shadow-md"
        >
          {isStreaming ? '⚡' : 'EXECUTE'}
        </button>
      </form>

    </div>
  );
};