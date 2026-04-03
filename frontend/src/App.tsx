import { useState, useRef, useEffect } from 'react'
import './App.css'

interface ToolCall {
  id: string;
  name: string;
  args?: any;
  result?: any;
  status: 'running' | 'completed';
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const [threadId] = useState(() => Date.now().toString() + Math.random().toString(36).substring(2));
  const [pendingInterrupt, setPendingInterrupt] = useState<string | null>(null);
  const [currentAssistantId, setCurrentAssistantId] = useState<string | null>(null);
  const [editedArgsStr, setEditedArgsStr] = useState<string>('');

  const pendingTool = messages.flatMap(m => m.toolCalls || []).find(t => t.name === pendingInterrupt && t.status === 'running');

  useEffect(() => {
    if (pendingTool && pendingTool.args && editedArgsStr === '') {
      setEditedArgsStr(JSON.stringify(pendingTool.args, null, 2));
    }
  }, [pendingInterrupt, pendingTool]);

  const executeChatStream = async (payload: any, assistantId: string) => {
    setIsTyping(true);
    // Do NOT reset pendingInterrupt/editedArgsStr here since we reset it natively on action!
    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, thread_id: threadId }),
      });

      if (!response.body) throw new Error('No body in response');
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            
            if (data.type === 'interrupt') {
              setPendingInterrupt(data.tool_name || 'unknown');
              setEditedArgsStr(''); // Reset editable content when a new interrupt arrives
              setIsTyping(false);
              return; // Stop streaming, wait for user action
            }
            
            setMessages(prev => prev.map(msg => {
              if (msg.id !== assistantId) return msg;
              
              if (data.type === 'token') {
                return { ...msg, content: msg.content + data.content };
              } else if (data.type === 'tool_start') {
                let parsedArgs = data.args || data.inputs || data.input || data.tool_input || data.kwargs || data.arguments || {};
                if (typeof parsedArgs === 'string') {
                  try { parsedArgs = JSON.parse(parsedArgs); } catch (e) {}
                }
                const newTool: ToolCall = {
                  id: data.id || data.run_id || Date.now().toString() + Math.random(),
                  name: data.name,
                  args: parsedArgs,
                  status: 'running'
                };
                return { ...msg, toolCalls: [...(msg.toolCalls || []), newTool] };
              } else if (data.type === 'tool_end') {
                return { 
                  ...msg, 
                  toolCalls: (msg.toolCalls || []).map(tc => {
                    const isMatch = (data.id || data.run_id) 
                      ? tc.id === (data.id || data.run_id)
                      : tc.name === data.name && tc.status === 'running';
                    
                    if (isMatch) {
                      let parsedResult = data.result || data.output || data.content || '';
                      if (typeof parsedResult === 'string') {
                        try {
                          const cleanResult = parsedResult.replace(/^```json\n/, '').replace(/\n```$/, '');
                          parsedResult = JSON.parse(cleanResult);
                        } catch (e) {}
                      }
                      return { ...tc, status: 'completed', result: parsedResult };
                    }
                    return tc;
                  })
                };
              }
              return msg;
            }));
          } catch (e) {
            console.error('Error parsing JSON line:', e);
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'assistant', content: 'Sorry, I encountered an error.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || pendingInterrupt) return;

    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    
    const assistantId = (Date.now() + 1).toString();
    setCurrentAssistantId(assistantId);
    setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '', toolCalls: [] }]);

    await executeChatStream({ message: userMessage.content }, assistantId);
  };

  const handleInterruptResponse = async (decision: 'approve' | 'reject' | 'edit') => {
    if (!currentAssistantId) return;

    let resumeObj: any = { decisions: [{ type: decision }] };

    if (decision === 'edit') {
      try {
        const parsedArgs = JSON.parse(editedArgsStr);
        resumeObj = {
          decisions: [{
            type: 'edit',
            edited_action: { name: pendingInterrupt, args: parsedArgs }
          }]
        };
      } catch (err) {
        alert("Invalid JSON returned: " + err);
        return;
      }
    }

    setPendingInterrupt(null);
    setEditedArgsStr('');
    await executeChatStream({ resume: resumeObj }, currentAssistantId);
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>History</h2>
          <button className="new-chat-btn">+ New Chat</button>
        </div>
        <div className="history-list">
          <div className="history-item active">Current Session</div>
          <div className="history-item">Yesterday's Research</div>
          <div className="history-item">Project Alpha Ideas</div>
        </div>
        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="avatar">U</div>
            <span>User Account</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="chat-header">
          <h1>AGENT_DESKTOP_V1</h1>
          <div className="status-indicator">SYSTEM ONLINE</div>
        </header>

        <div className="messages-area">
          {messages.map((msg) => (
             <div key={msg.id} className={`message ${msg.role}`}>
              <div className="message-bubble">
                <div className="role-label">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
                
                {msg.toolCalls && msg.toolCalls.length > 0 && (
                  <div className="tool-calls-container">
                    {msg.toolCalls.map((tool, idx) => (
                      <details key={tool.id || idx} className="tool-collapse">
                        <summary className="tool-summary">
                          <span className="tool-icon">⚙️</span>
                          <span className="tool-name">Used tool: <strong>{tool.name}</strong></span>
                          {tool.status === 'running' && <span className="tool-running"> (running...)</span>}
                        </summary>
                        <div className="tool-details">
                          <div className="tool-section">
                            <div className="tool-section-title">Arguments:</div>
                            <pre className="tool-code">
                              {JSON.stringify(tool.args, null, 2)}
                            </pre>
                          </div>
                          {tool.status === 'completed' && (
                            <div className="tool-section">
                              <div className="tool-section-title">Result:</div>
                              <pre className="tool-code">
                                {typeof tool.result === 'string' 
                                  ? tool.result 
                                  : JSON.stringify(tool.result, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </details>
                    ))}
                  </div>
                )}

                <div className="content">
                  {msg.content.split('\n').map((line, i) => (
                    <span key={i}>{line}<br /></span>
                  ))}
                </div>
              </div>
             </div>
          ))}
          {isTyping && <div className="typing-indicator">Agent is analyzing...</div>}
          
          {pendingInterrupt && (
            <div className="interrupt-dialog">
              <div className="interrupt-alert">
                <h3>⚠️ Action Requires Approval</h3>
                <p>The agent wants to execute: <strong>{pendingInterrupt}</strong>.</p>
                {editedArgsStr !== '' && (
                  <textarea 
                    value={editedArgsStr}
                    onChange={e => setEditedArgsStr(e.target.value)}
                    style={{width: '100%', minHeight: '100px', backgroundColor: '#1a1a1a', color: 'white', padding: '10px', margin: '10px 0', fontFamily: 'monospace', border: '1px solid #333', borderRadius: '4px'}}
                  />
                )}
                <div className="interrupt-actions">
                  <button className="reject-btn" onClick={() => handleInterruptResponse('reject')}>Reject</button>
                  <button className="approve-btn" onClick={() => handleInterruptResponse('edit')}>Approve with Edits</button>
                  <button className="approve-btn" onClick={() => handleInterruptResponse('approve')}>Approve As-Is</button>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="input-form">
          <div className="input-wrapper">
            <input 
              type="text" 
              value={input} 
              onChange={(e) => setInput(e.target.value)} 
              placeholder="Message Agent..."
              disabled={isTyping || pendingInterrupt !== null}
            />
            <button type="submit" disabled={isTyping || !input.trim() || pendingInterrupt !== null}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M7 11L12 6L17 11M12 18V7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}

export default App
