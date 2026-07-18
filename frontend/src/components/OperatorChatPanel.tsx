import React, { useState, useRef, useEffect } from 'react';

interface ChatMessage {
  id: string;
  sender: 'operator' | 'agent';
  text: string;
  timestamp: string;
}

export const OperatorChatPanel: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState<string>('');
  const [isStreaming, setIsUploading] = useState<boolean>(false);
  const chatBottomAnchorRef = useRef<HTMLDivElement | null>(null);

  // Automatically scroll the chat block downwards as words stream into view
  useEffect(() => {
    chatBottomAnchorRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const dispatchStreamingQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isStreaming) return;

    const userQueryText = inputQuery.trim();
    setInputQuery('');
    setIsUploading(true);

    const operatorMessageId = `op_${Date.now()}`;
    const agentMessageId = `agent_${Date.now()}`;

    // Append the operator's initial question to the chat list array
    const incomingUserMessage: ChatMessage = {
      id: operatorMessageId,
      sender: 'operator',
      text: userQueryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, incomingUserMessage]);

    // Provision a blank token placeholder slot for the incoming agent streaming bytes
    setMessages((prev) => [
      ...prev,
      { id: agentMessageId, sender: 'agent', text: '', timestamp: 'Processing...' }
    ]);

    try {
      // Direct network pipeline link to Rudra's Sub-Phase 10.4 FastAPI endpoint
      const response = await fetch('http://localhost:8000/api/v1/query/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userQueryText }) // Mapped explicitly to Pydantic schemas
      });

      if (!response.ok || !response.body) {
        console.error('❌ INTERFACE FAULT: Event stream target unreachable.');
        setIsUploading(false);
        return;
      }

      // Initialize native browser stream reader loops over the network response body
      const streamReader = response.body.getReader();
      const textDecoder = new TextDecoder();
      let accumulatedResponseText = '';

      while (true) {
        const { value, done } = await streamReader.read();
        if (done) break;

        // Decode the raw byte stream chunk fragments into standard text strings
        const textChunkFragment = textDecoder.decode(value, { stream: true });
        
        // Split text by lines to extract matching Server-Sent Event (SSE) "data: " fields
        const linesArray = textChunkFragment.split('\n');
        for (const line of linesArray) {
          if (line.startsWith('data: ')) {
            const cleanTokenWord = line.replace('data: ', '');
            accumulatedResponseText += cleanTokenWord + ' ';

            // Dynamically update the specific target message node in real-time
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

  return (
    <div className="flex flex-col h-[500px] bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden backdrop-blur-md shadow-2xl">
      
      {/* Dynamic Header Strip Layout */}
      <div className="px-5 py-3.5 border-b border-slate-800/80 bg-slate-900/60 flex items-center justify-between font-mono text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]"></span>
          <span>LANGGRAPH REASONING CORES RETRIEVAL AGENT</span>
        </div>
        <span className="text-[10px] tracking-widest text-slate-500 font-bold uppercase">SECURE PIPE</span>
      </div>

      {/* Interactive Conversational Flow Scroll Container */}
      <div className="flex-1 p-5 overflow-y-auto flex flex-col gap-4">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500 font-mono text-xs text-center gap-2">
            <span>💬</span>
            <span>IKIP Query Space Interface Activated.</span>
            <span className="text-[10px] text-slate-600 font-normal max-w-xs">Ask technical questions regarding active folder manuals, equipment indices, or threshold parameters.</span>
          </div>
        ) : (
          messages.map((message) => (
            <div 
              key={message.id} 
              className={`flex flex-col max-w-[80%] ${message.sender === 'operator' ? 'self-end items-end' : 'self-start items-start'}`}
            >
              <div className={`px-4 py-2.5 rounded-xl text-sm leading-relaxed whitespace-pre-wrap ${
                message.sender === 'operator' 
                  ? 'bg-blue-600 text-white rounded-tr-none shadow-md' 
                  : 'bg-slate-950/80 text-slate-200 border border-slate-800/80 rounded-tl-none font-mono text-xs shadow-inner'
              }`}>
                {message.text || (isStreaming && message.timestamp === 'Processing...' ? '⚡ Executing Graph Walk...' : '')}
              </div>
              <span className="text-[10px] font-mono text-slate-500 mt-1 px-1">{message.timestamp}</span>
            </div>
          ))
        )}
        <div ref={chatBottomAnchorRef} />
      </div>

      {/* Input Message Form Command Core */}
      <form onSubmit={dispatchStreamingQuery} className="p-4 border-t border-slate-800/80 bg-slate-950/40 flex gap-3">
        <input 
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          disabled={isStreaming}
          placeholder={isStreaming ? "Awaiting model response array tokens..." : "Type industrial query vector request (e.g. Check PUMP-102 metrics)..."}
          className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm font-mono placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50 text-slate-100 transition shadow-inner disabled:opacity-50"
        />
        <button 
          type="submit"
          disabled={isStreaming || !inputQuery.trim()}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-800 disabled:text-slate-600 border border-blue-500/20 px-5 rounded-lg text-white font-mono text-xs font-bold transition flex items-center justify-center gap-1 shadow-md"
        >
          {isStreaming ? '⚡' : 'SEND'}
        </button>
      </form>

    </div>
  );
};