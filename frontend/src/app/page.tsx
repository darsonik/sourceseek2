"use client";

import { useState, useRef, useEffect } from "react";
import { UploadCloud, Search, FileText, Loader2, Sparkles, Database, Send, User, Bot, Trash2, LogOut, PlusCircle, Lightbulb, MessageCircle, MessageSquare, History } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);

  // Auth UI State
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authUsername, setAuthUsername] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  // App State
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [duplicateInfo, setDuplicateInfo] = useState<{
    filename: string;
    chunkCount: number;
  } | null>(null);
  const [userDocs, setUserDocs] = useState<any[]>([]);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  
  const [insights, setInsights] = useState<{ insights: {text: string, source_filename: string}[], suggestions: {text: string, source_filename: string}[] } | null>(null);
  const [isFetchingInsights, setIsFetchingInsights] = useState(false);
  
  const [chatHistories, setChatHistories] = useState<any[]>([]);
  const [currentContextFile, setCurrentContextFile] = useState<string | null>(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(true);
  const [historyFilter, setHistoryFilter] = useState<string>("All");

  const threadId = useRef(Math.random().toString(36).substring(2, 15));
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const storedToken = localStorage.getItem("sourceseek_token");
    const storedUsername = localStorage.getItem("sourceseek_username");
    if (storedToken && storedUsername) {
      setToken(storedToken);
      setUsername(storedUsername);
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchDocuments();
      fetchHistories();
    }
  }, [token]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSearching]);

  useEffect(() => {
    if (token && userDocs.length > 0 && messages.length === 0 && !insights && !isFetchingInsights) {
      fetchInsights();
    }
  }, [userDocs.length, messages.length, token]);

  const fetchInsights = async () => {
    setIsFetchingInsights(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/insights", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setInsights(data);
      }
    } catch (e) {
      console.error("Failed to fetch insights", e);
    } finally {
      setIsFetchingInsights(false);
    }
  };

  const fetchHistories = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/history", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setChatHistories(data);
      }
    } catch (e) {
      console.error("Failed to fetch histories", e);
    }
  };

  const loadHistory = async (id: string, file: string | null) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/history/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
        threadId.current = id;
        setCurrentContextFile(file);
      }
    } catch (e) {
      console.error("Failed to load history", e);
    }
  };

  const deleteHistory = async (id: string) => {
    if (!confirm("Delete this chat?")) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/history/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        fetchHistories();
        if (threadId.current === id) handleNewChat();
      }
    } catch (e) {}
  };

  const clearAllHistory = async () => {
    if (!confirm("Delete all chat history?")) return;
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/history", {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        fetchHistories();
        handleNewChat();
      }
    } catch (e) {}
  };

  const handleNewChat = () => {
    setMessages([]);
    setCurrentContextFile(null);
    threadId.current = Math.random().toString(36).substring(2, 15);
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAuthenticating(true);
    setAuthError("");
    try {
      const endpoint = authMode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register";
      const res = await fetch(`http://127.0.0.1:8000${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: authUsername, password: authPassword }),
      });
      const data = await res.json();
      if (res.ok) {
        setToken(data.access_token);
        setUsername(data.username);
        localStorage.setItem("sourceseek_token", data.access_token);
        localStorage.setItem("sourceseek_username", data.username);
        setAuthUsername("");
        setAuthPassword("");
      } else {
        setAuthError(data.detail || "Authentication failed");
      }
    } catch (e) {
      setAuthError("Connection error. Backend running?");
    } finally {
      setIsAuthenticating(false);
    }
  };

  const logout = () => {
    setToken(null);
    setUsername(null);
    localStorage.removeItem("sourceseek_token");
    localStorage.removeItem("sourceseek_username");
    setUserDocs([]);
    setMessages([]);
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/documents", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUserDocs(data);
      }
    } catch (e) {
      console.error("Failed to fetch documents", e);
    }
  };

  const deleteDocument = async (id: string) => {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/documents/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        fetchDocuments();
      } else {
        alert("Failed to delete document.");
      }
    } catch (e) {
      alert("Error connecting to server.");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setUploadMessage("");
    }
  };

  const handleUpload = async () => {
    if (!file || !token) return;
    setIsUploading(true);
    setUploadMessage("");
    
    try {
      const checkRes = await fetch(`http://127.0.0.1:8000/api/v1/documents/check?filename=${encodeURIComponent(file.name)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (checkRes.ok) {
        const checkData = await checkRes.json();
        if (checkData.exists) {
          setDuplicateInfo({
            filename: checkData.filename,
            chunkCount: checkData.chunk_count,
          });
          setIsUploading(false);
          return;
        }
      }
      await proceedWithUpload(false);
    } catch (error) {
      setUploadMessage("❌ Connection error. Is the backend running?");
      setIsUploading(false);
    }
  };

  const proceedWithUpload = async (forceReprocess: boolean) => {
    if (!file || !token) return;
    setIsUploading(true);
    setUploadMessage("");
    setDuplicateInfo(null);
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      const url = `http://127.0.0.1:8000/api/v1/documents/upload${forceReprocess ? '?force_reprocess=true' : ''}`;
      const res = await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      
      const data = await res.json();
      if (res.ok) {
        setUploadMessage(`✅ Indexed ${data.chunks_saved} segments from ${data.filename}`);
        setFile(null);
        fetchDocuments(); // refresh sidebar
        setInsights(null); // Clear insights to trigger refetch with new doc
      } else {
        setUploadMessage(`❌ Error: ${data.detail?.message || data.detail || 'Upload failed'}`);
      }
    } catch (error) {
      setUploadMessage("❌ Connection error. Is the backend running?");
    } finally {
      setIsUploading(false);
    }
  };

  const handleSearch = async (e?: React.FormEvent, directQuery?: string) => {
    if (e) e.preventDefault();
    const queryToUse = directQuery || searchQuery;
    if (!queryToUse.trim() || !token) return;

    setMessages(prev => [...prev, { role: "user", content: queryToUse }]);
    if (!directQuery) setSearchQuery("");
    setIsSearching(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/search", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ 
          query: queryToUse, 
          thread_id: threadId.current,
          associated_filename: currentContextFile 
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setMessages(prev => [...prev, { role: "assistant", content: data.answer }]);
        fetchHistories();
      } else {
        setMessages(prev => [...prev, { role: "assistant", content: `Error: ${data.detail || 'Search failed'}` }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: "assistant", content: "Connection error. Is the backend running?" }]);
    } finally {
      setIsSearching(false);
    }
  };

  if (!token) {
    return (
      <div className="auth-container">
        <div className="auth-box glass-panel">
          <div className="auth-header">
            <Database size={40} color="var(--primary)" />
            <h2>SourceSeek</h2>
            <p>Sign in to access your knowledge base</p>
          </div>
          
          <form onSubmit={handleAuth} className="auth-form">
            <input 
              type="text" 
              className="input-field" 
              placeholder="Username" 
              value={authUsername}
              onChange={(e) => setAuthUsername(e.target.value)}
              required
            />
            <input 
              type="password" 
              className="input-field" 
              placeholder="Password" 
              value={authPassword}
              onChange={(e) => setAuthPassword(e.target.value)}
              required
            />
            {authError && <div className="auth-error">{authError}</div>}
            
            <button type="submit" className="btn-primary" disabled={isAuthenticating}>
              {isAuthenticating ? <Loader2 className="spinner" size={18} /> : (authMode === "login" ? "Login" : "Register")}
            </button>
          </form>

          <p className="auth-toggle">
            {authMode === "login" ? "Don't have an account? " : "Already have an account? "}
            <span onClick={() => { setAuthMode(authMode === "login" ? "register" : "login"); setAuthError(""); }}>
              {authMode === "login" ? "Register here" : "Login here"}
            </span>
          </p>
        </div>
        <style jsx global>{`
          .auth-container { height: 100vh; display: flex; align-items: center; justify-content: center; background-color: var(--bg-color); }
          .auth-box { width: 100%; max-width: 400px; padding: 2.5rem; display: flex; flex-direction: column; gap: 1.5rem; }
          .auth-header { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; text-align: center; }
          .auth-header h2 { font-size: 1.8rem; }
          .auth-header p { color: var(--text-muted); font-size: 0.95rem; }
          .auth-form { display: flex; flex-direction: column; gap: 1rem; }
          .auth-error { color: var(--danger); font-size: 0.9rem; text-align: center; }
          .auth-toggle { text-align: center; font-size: 0.9rem; color: var(--text-muted); margin-top: 0.5rem; }
          .auth-toggle span { color: var(--primary); cursor: pointer; font-weight: 500; }
          .auth-toggle span:hover { text-decoration: underline; }
          .spinner { animation: spin 1s linear infinite; }
          @keyframes spin { 100% { transform: rotate(360deg); } }
        `}</style>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* LEFT SIDEBAR - Document Ingestion */}
      <aside className="sidebar glass-panel">
        <div className="sidebar-header">
          <Database size={32} color="var(--primary)" />
          <h2>SourceSeek</h2>
        </div>
        
        <div className="user-profile">
          <div className="user-info">
            <User size={18} />
            <span>{username}</span>
          </div>
          <button className="logout-btn" onClick={logout} title="Logout">
            <LogOut size={16} />
          </button>
        </div>

        <div className="upload-section" style={{ marginTop: "1rem" }}>
          <div className="upload-dropzone">
            <input 
              type="file" 
              onChange={handleFileChange} 
              accept=".pdf,.docx,.xlsx,image/*"
              className="file-input"
            />
            {file ? (
              <div className="file-info">
                <FileText size={36} color="var(--primary)" />
                <p className="file-name">{file.name}</p>
                <p className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <div className="file-prompt">
                <UploadCloud size={36} color="var(--text-muted)" style={{ opacity: 0.6 }} />
                <p>Click or drag a file</p>
                <span className="file-types">PDF, DOCX, XLSX, Images</span>
              </div>
            )}
          </div>

          <button 
            className="btn-primary upload-btn" 
            onClick={handleUpload} 
            disabled={!file || isUploading}
          >
            {isUploading ? <><Loader2 className="spinner" size={18} /> Processing...</> : "Upload Document"}
          </button>

          {uploadMessage && (
            <div className={`upload-message ${uploadMessage.includes("❌") ? "error" : "success"}`}>
              {uploadMessage}
            </div>
          )}
        </div>

        <div className="user-documents">
          <h3>Your Documents</h3>
          {userDocs.length === 0 ? (
            <p className="empty-docs">No documents uploaded yet.</p>
          ) : (
            <ul className="doc-list">
              {userDocs.map(doc => (
                <li key={doc.id} className="doc-item">
                  <div className="doc-info">
                    <FileText size={16} color="var(--text-muted)" />
                    <span className="doc-name" title={doc.filename}>{doc.filename}</span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.25rem' }}>
                    <button className="doc-action-btn" onClick={() => { handleNewChat(); setCurrentContextFile(doc.filename); }} title="Chat with document">
                      <MessageSquare size={16} />
                    </button>
                    <button className="doc-action-btn delete" onClick={() => deleteDocument(doc.id)} title="Delete file">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      {/* MAIN CONTENT - Chat Interface */}
      <main className="main-chat">
        <header className="chat-header glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sparkles color="var(--primary)" />
            <h3 style={{ margin: 0 }}>{currentContextFile ? `Chat: ${currentContextFile}` : 'Deep Insights'}</h3>
            {currentContextFile && (
              <button 
                onClick={handleNewChat} 
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', marginLeft: '0.5rem', fontSize: '0.85rem', textDecoration: 'underline' }}
              >
                Clear
              </button>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {messages.length > 0 && (
              <button 
                className="btn-secondary" 
                onClick={handleNewChat}
                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}
                title="Start a new conversation"
              >
                <PlusCircle size={16} /> New Chat
              </button>
            )}
            <button 
              className="btn-secondary" 
              onClick={() => setIsHistoryOpen(!isHistoryOpen)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}
              title="Toggle History"
            >
              <History size={16} /> History
            </button>
          </div>
        </header>

        <div className="chat-window glass-panel">
          {messages.length === 0 ? (
            <div className="empty-state">
              {userDocs.length === 0 ? (
                <>
                  <Search size={48} color="var(--text-muted)" style={{ opacity: 0.3 }} />
                  <h2>How can I help you today?</h2>
                  <p>Upload a document to get started.</p>
                </>
              ) : isFetchingInsights ? (
                <div className="insights-loading">
                  <Loader2 className="spinner" size={24} color="var(--primary)" />
                  <p>Analyzing your documents...</p>
                </div>
              ) : insights && (insights.insights.length > 0 || insights.suggestions.length > 0) ? (
                <div className="insights-container">
                  <div className="insights-header">
                    <Lightbulb color="var(--primary)" size={24} />
                    <h2>Recent Insights</h2>
                  </div>
                  <div className="insights-grid">
                    {insights.insights.map((insight, i) => (
                      <div key={i} className="insight-card glass-panel">
                        <p>{insight.text}</p>
                        {insight.source_filename && (
                          <div className="insight-source">
                            <FileText size={12} />
                            <span>{insight.source_filename}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  
                  {insights.suggestions.length > 0 && (
                    <div className="suggestions-section">
                      <div className="suggestions-header">
                        <MessageCircle size={16} color="var(--text-muted)" />
                        <h4>Suggested Questions</h4>
                      </div>
                      <div className="suggestions-chips">
                        {insights.suggestions.map((sug, i) => (
                          <button 
                            key={i} 
                            className="suggestion-chip"
                            onClick={() => handleSearch(undefined, sug.text)}
                          >
                            <span className="suggestion-text">{sug.text}</span>
                            {sug.source_filename && (
                              <span className="suggestion-source"> ({sug.source_filename})</span>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <>
                  <Search size={48} color="var(--text-muted)" style={{ opacity: 0.3 }} />
                  <h2>How can I help you today?</h2>
                  <p>Ask a question about your uploaded documents.</p>
                </>
              )}
            </div>
          ) : (
            <div className="messages-container">
              {messages.map((msg, idx) => (
                <div key={idx} className={`message-wrapper ${msg.role}`}>
                  <div className="avatar">
                    {msg.role === "user" ? <User size={20} /> : <Bot size={20} />}
                  </div>
                  <div className={`message-bubble ${msg.role}`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  </div>
                </div>
              ))}
              {isSearching && (
                <div className="message-wrapper assistant">
                  <div className="avatar">
                    <Bot size={20} />
                  </div>
                  <div className="message-bubble assistant loading">
                    <Loader2 className="spinner" size={18} /> Searching documents...
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="chat-input-container">
          <form onSubmit={handleSearch} className="chat-form glass-panel">
            <input 
              type="text" 
              className="chat-input" 
              placeholder="Ask a question about your documents..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              disabled={isSearching}
            />
            <button type="submit" className="send-btn" disabled={isSearching || !searchQuery.trim()}>
              <Send size={20} />
            </button>
          </form>
        </div>
      </main>

      {/* RIGHT SIDEBAR - Chat History */}
      {isHistoryOpen && (
        <aside className="sidebar right-sidebar glass-panel">
          <div className="sidebar-header" style={{ justifyContent: 'space-between' }}>
            <h2>History</h2>
            {chatHistories.length > 0 && (
              <button className="logout-btn" onClick={clearAllHistory} title="Clear all history">
                <Trash2 size={16} />
              </button>
            )}
          </div>
          
          <div className="user-documents">
            {chatHistories.length === 0 ? (
              <p className="empty-docs">No chat history yet.</p>
            ) : (
              <>
                <div style={{ marginBottom: '1rem' }}>
                  <select 
                    className="input-field" 
                    style={{ padding: '0.5rem', fontSize: '0.85rem' }}
                    value={historyFilter}
                    onChange={e => setHistoryFilter(e.target.value)}
                  >
                    <option value="All">All Documents</option>
                    {Array.from(new Set(chatHistories.flatMap(h => h.associated_filename ? h.associated_filename.split(',').map((f: string) => f.strip ? f.strip() : f.trim()) : []))).map((filename: any, idx) => (
                      <option key={idx} value={filename}>{filename}</option>
                    ))}
                  </select>
                </div>
                <ul className="doc-list history-list">
                  {chatHistories.filter(h => historyFilter === "All" || (h.associated_filename && h.associated_filename.includes(historyFilter))).map(history => (
                    <li key={history.thread_id} className={`doc-item ${threadId.current === history.thread_id ? 'active' : ''}`}>
                      <div className="doc-info" onClick={() => loadHistory(history.thread_id, history.associated_filename)} style={{ cursor: 'pointer', flex: 1 }}>
                        <MessageSquare size={16} color="var(--text-muted)" style={{ flexShrink: 0, marginTop: '2px' }} />
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', overflow: 'hidden', width: '100%' }}>
                          <span className="doc-name" title={history.title} style={{ whiteSpace: 'normal', lineHeight: '1.2' }}>{history.title}</span>
                          {history.associated_filename && (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                              {history.associated_filename.split(',').map((f: string, i: number) => (
                                <span key={i} style={{ 
                                  fontSize: '0.65rem', 
                                  backgroundColor: 'rgba(0,0,0,0.05)', 
                                  color: 'var(--text-muted)', 
                                  padding: '0.1rem 0.4rem', 
                                  borderRadius: '4px',
                                  border: '1px solid rgba(0,0,0,0.05)',
                                  whiteSpace: 'nowrap',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  maxWidth: '100%'
                                }}>
                                  {f.trim()}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                      <button className="doc-action-btn delete" onClick={() => deleteHistory(history.thread_id)} title="Delete chat" style={{ flexShrink: 0 }}>
                        <Trash2 size={16} />
                      </button>
                    </li>
                  ))}
                  {chatHistories.filter(h => historyFilter === "All" || (h.associated_filename && h.associated_filename.includes(historyFilter))).length === 0 && (
                     <p className="empty-docs">No history matches the selected document.</p>
                  )}
                </ul>
              </>
            )}
          </div>
        </aside>
      )}

      <style jsx global>{`
        .spinner { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        
        .user-profile {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem;
          background: rgba(0,0,0,0.03);
          border-radius: 8px;
          margin-bottom: 0.5rem;
        }
        .user-info { display: flex; align-items: center; gap: 0.5rem; font-weight: 500; font-size: 0.95rem; }
        .logout-btn { background: transparent; border: none; cursor: pointer; color: var(--text-muted); display: flex; align-items: center; justify-content: center; padding: 0.25rem; border-radius: 4px; }
        .logout-btn:hover { color: var(--danger); background: rgba(196, 91, 91, 0.1); }
        
        .user-documents { margin-top: 2rem; flex: 1; overflow-y: auto; }
        .user-documents h3 { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 1rem; }
        .empty-docs { font-size: 0.85rem; color: var(--text-muted); font-style: italic; }
        .doc-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
        .doc-item { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; border-radius: 6px; background: rgba(0,0,0,0.02); transition: all 0.2s; }
        .doc-item:hover { background: rgba(0,0,0,0.04); }
        .doc-info { display: flex; align-items: center; gap: 0.5rem; overflow: hidden; }
        .doc-name { font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
        .doc-action-btn { background: transparent; border: none; color: var(--text-muted); cursor: pointer; padding: 0.25rem; border-radius: 4px; display: flex; opacity: 0.5; transition: all 0.2s; }
        .doc-item:hover .doc-action-btn { opacity: 1; }
        .doc-action-btn:hover { color: var(--primary); background: rgba(0,0,0,0.05); }
        .doc-action-btn.delete:hover { color: var(--danger); background: rgba(196, 91, 91, 0.1); }
        .doc-item.active { background: rgba(217, 119, 87, 0.1); border-left: 2px solid var(--primary); }
        .right-sidebar { width: 300px; flex-shrink: 0; }
        .history-list .doc-info { align-items: flex-start; margin-top: 0.2rem; }
        
        .insights-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem; color: var(--text-muted); padding: 3rem 0; width: 100%; height: 100%; }
        .insights-container { width: 100%; max-width: 800px; text-align: left; padding: 2rem; display: flex; flex-direction: column; align-items: stretch; justify-content: flex-start; height: 100%; }
        .insights-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; }
        .insights-header h2 { margin: 0; font-size: 1.5rem; color: var(--text-color); }
        .insights-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-bottom: 2rem; width: 100%; }
        .insight-card { padding: 1.25rem; border-radius: 8px; background: rgba(0,0,0, 0.03); border: 1px solid rgba(0,0,0, 0.1); display: flex; flex-direction: column; justify-content: space-between; }
        .insight-card p { margin: 0; font-size: 0.95rem; line-height: 1.5; color: var(--text-color); margin-bottom: 0.75rem; }
        .insight-source { display: flex; align-items: center; gap: 0.25rem; font-size: 0.75rem; color: var(--text-muted); padding-top: 0.5rem; border-top: 1px solid rgba(0,0,0,0.05); font-style: italic; }
        .suggestions-section { display: flex; flex-direction: column; gap: 1rem; }
        .suggestions-header { display: flex; align-items: center; gap: 0.5rem; }
        .suggestions-header h4 { margin: 0; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }
        .suggestions-chips { display: flex; flex-wrap: wrap; gap: 0.75rem; }
        .suggestion-chip { background: rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.05); padding: 0.75rem 1rem; border-radius: 20px; font-size: 0.9rem; color: var(--text-color); cursor: pointer; transition: all 0.2s; text-align: left; line-height: 1.3; max-width: 100%; }
        .suggestion-chip:hover { background: rgba(0,0,0, 0.1); border-color: rgba(0,0,0, 0.2); transform: translateY(-1px); }
        .suggestion-source { font-size: 0.8rem; color: var(--text-muted); font-style: italic; white-space: nowrap; }
      `}</style>

      {/* Duplicate File Modal */}
      {duplicateInfo && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel">
            <h3>Document Already Exists</h3>
            <p>
              <strong>{duplicateInfo.filename}</strong> has already been processed and indexed with {duplicateInfo.chunkCount} segments.
            </p>
            <p>
              You can query the existing data now, or choose to reprocess the file. 
              Reprocessing will delete the old data and index it again.
            </p>
            
            <div className="modal-actions">
              <button 
                className="btn-secondary" 
                onClick={() => {
                  setDuplicateInfo(null);
                  setFile(null);
                  setUploadMessage(`✅ Ready to query existing data for ${duplicateInfo.filename}`);
                }}
              >
                Keep Existing
              </button>
              <button 
                className="btn-primary warning" 
                onClick={() => proceedWithUpload(true)}
              >
                Reprocess File
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
