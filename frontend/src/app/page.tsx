"use client";

import { useState, useRef, useEffect } from "react";
import { UploadCloud, Search, FileText, Loader2, Sparkles, Database, Send, User, Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  
  // Create a persistent thread ID for this session
  const threadId = useRef(Math.random().toString(36).substring(2, 15));
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSearching]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setUploadMessage("");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setIsUploading(true);
    setUploadMessage("");
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/documents/upload", {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setUploadMessage(`✅ Indexed ${data.chunks_saved} segments from ${data.filename}`);
        setFile(null); // Reset
      } else {
        setUploadMessage(`❌ Error: ${data.detail || 'Upload failed'}`);
      }
    } catch (error) {
      setUploadMessage("❌ Connection error. Is the backend running?");
    } finally {
      setIsUploading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    const userQuery = searchQuery;
    setMessages(prev => [...prev, { role: "user", content: userQuery }]);
    setSearchQuery("");
    setIsSearching(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/search/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userQuery, thread_id: threadId.current }),
      });

      const data = await res.json();
      
      if (res.ok) {
        setMessages(prev => [...prev, { role: "assistant", content: data.answer }]);
      } else {
        setMessages(prev => [...prev, { role: "assistant", content: `Error: ${data.detail || 'Search failed'}` }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: "assistant", content: "Connection error. Is the backend running?" }]);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="app-container">
      {/* LEFT SIDEBAR - Document Ingestion */}
      <aside className="sidebar glass-panel">
        <div className="sidebar-header">
          <Database size={32} color="var(--primary)" />
          <h2>SourceSeek</h2>
        </div>
        <p className="sidebar-subtitle">
          Upload documents to build your secure enterprise knowledge base.
        </p>

        <div className="upload-section">
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
      </aside>

      {/* MAIN CONTENT - Chat Interface */}
      <main className="main-chat">
        <header className="chat-header glass-panel">
          <Sparkles color="var(--primary)" />
          <h3>Deep Insights</h3>
        </header>

        <div className="chat-window glass-panel">
          {messages.length === 0 ? (
            <div className="empty-state">
              <Search size={48} color="var(--text-muted)" style={{ opacity: 0.3 }} />
              <h2>How can I help you today?</h2>
              <p>Ask a question about your uploaded documents.</p>
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

      <style jsx global>{`
        .spinner { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
