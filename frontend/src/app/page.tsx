"use client";

import { useState, useRef, useEffect } from "react";
import { UploadCloud, Search, FileText, Loader2, Sparkles, Database, Send, User, Bot, Trash2, LogOut, PlusCircle, Lightbulb, MessageCircle, MessageSquare, History, Moon, Sun, Monitor, DownloadCloud, ArrowRight, Shield, Zap, Check, X } from "lucide-react";
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
  const [showAuthModal, setShowAuthModal] = useState(false);

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
  const [showInsights, setShowInsights] = useState(true);
  const [isHistoryOpen, setIsHistoryOpen] = useState(true);
  const [historyFilter, setHistoryFilter] = useState<string>("All");
  const [theme, setTheme] = useState<"light" | "dark" | "system">("system");

  // Export UI State
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportFormat, setExportFormat] = useState<"pdf" | "docx">("pdf");
  const [exportSaveToB2, setExportSaveToB2] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const [exportSuccess, setExportSuccess] = useState("");

  const threadId = useRef(Math.random().toString(36).substring(2, 15));
  const chatWindowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const storedToken = localStorage.getItem("sourceseek_token");
    const storedUsername = localStorage.getItem("sourceseek_username");
    if (storedToken && storedUsername) {
      setToken(storedToken);
      setUsername(storedUsername);
    }
    
    const storedTheme = localStorage.getItem("sourceseek_theme") as "light" | "dark" | "system" | null;
    if (storedTheme) {
      setTheme(storedTheme);
      if (storedTheme !== "system") {
        document.documentElement.setAttribute("data-theme", storedTheme);
      } else {
        document.documentElement.removeAttribute("data-theme");
      }
    }
  }, []);

  const toggleTheme = () => {
    let nextTheme: "light" | "dark" | "system";
    if (theme === "system") nextTheme = "light";
    else if (theme === "light") nextTheme = "dark";
    else nextTheme = "system";
    
    setTheme(nextTheme);
    localStorage.setItem("sourceseek_theme", nextTheme);
    if (nextTheme !== "system") {
      document.documentElement.setAttribute("data-theme", nextTheme);
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  };

  useEffect(() => {
    if (token) {
      fetchDocuments();
      fetchHistories();
    }
  }, [token]);

  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTo({
        top: chatWindowRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
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
      } else if (res.status === 401) {
        logout();
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
      } else if (res.status === 401) {
        logout();
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
    setShowInsights(false);
    threadId.current = Math.random().toString(36).substring(2, 15);
  };

  const handleExport = async () => {
    setIsExporting(true);
    setExportError("");
    setExportSuccess("");
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/history/${threadId.current}/export?format=${exportFormat}&save_to_b2=${exportSaveToB2}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        if (exportSaveToB2) {
          const data = await res.json();
          setExportSuccess("✅ Chat successfully saved to your documents!");
          fetchDocuments(); // Refresh documents list
          setTimeout(() => {
            setShowExportModal(false);
            setExportSuccess("");
          }, 2000);
        } else {
          const blob = await res.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          const contentDisposition = res.headers.get("content-disposition");
          let filename = `chat_export.${exportFormat}`;
          if (contentDisposition) {
            const matches = /filename="?([^"]+)"?/.exec(contentDisposition);
            if (matches && matches[1]) {
              filename = matches[1];
            }
          }
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
          setShowExportModal(false);
        }
      } else {
        const errData = await res.json();
        setExportError(errData.detail || "Failed to export chat.");
      }
    } catch (e) {
      setExportError("Connection error. Is the backend running?");
    } finally {
      setIsExporting(false);
    }
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
      } else if (res.status === 401) {
        logout();
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

  const downloadDocument = async (id: string, filename: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/documents/${id}/download?filename=${encodeURIComponent(filename)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } else {
        alert("Failed to download document.");
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
        setUploadMessage(`✅ Successfully added ${data.filename} to your knowledge base`);
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
      <div className="landing-container">
        {/* Layered background orbs */}
        <div className="landing-bg-orbs">
          <div className="orb orb-1" />
          <div className="orb orb-2" />
          <div className="orb orb-3" />
        </div>
        {/* Grid overlay pattern */}
        <div className="landing-grid-overlay" />

        {/* HEADER / NAVBAR */}
        <header className="landing-header">
          <div className="landing-header-inner">
            <div className="landing-logo">
              <div className="landing-logo-icon">
                <Database size={18} color="white" />
              </div>
              <span className="landing-logo-text">SourceSeek</span>
            </div>
            <div className="landing-nav-actions">
              <button
                className="landing-nav-btn"
                onClick={toggleTheme}
                title="Toggle Theme"
              >
                {theme === 'dark' ? <Moon size={16} /> : theme === 'light' ? <Sun size={16} /> : <Monitor size={16} />}
              </button>
              <button
                className="landing-login-btn"
                onClick={() => { setAuthMode("login"); setShowAuthModal(true); }}
              >
                Log In
              </button>
              <button
                className="landing-signup-btn"
                onClick={() => { setAuthMode("register"); setShowAuthModal(true); }}
              >
                Sign Up Free
              </button>
            </div>
          </div>
        </header>

        {/* HERO SECTION */}
        <section className="landing-hero">
          <div className="hero-content">
            <div className="hero-badge">
              <Sparkles size={14} />
              <span>AI-Powered Document Intelligence</span>
            </div>
            <h1 className="hero-title">
              Your Documents.<br />
              <span className="text-gradient-animated">Indexed. Chat Ready.</span>
            </h1>
            <p className="hero-subtitle">
              Upload PDFs, spreadsheets, images, and more. SourceSeek indexes your files, extracts insights, and lets you ask questions in natural language — all in real-time.
            </p>
            <div className="hero-cta-group">
              <button
                className="hero-cta-primary"
                onClick={() => { setAuthMode("register"); setShowAuthModal(true); }}
              >
                Get Started for Free <ArrowRight size={18} />
              </button>
              <button
                className="hero-cta-secondary"
                onClick={() => {
                  document.querySelector('.features-section')?.scrollIntoView({ behavior: 'smooth' });
                }}
              >
                See How It Works
              </button>
            </div>

            {/* Hero Stats */}
            <div className="hero-stats">
              <div className="hero-stat">
                <span className="hero-stat-value">5+</span>
                <span className="hero-stat-label">File Formats</span>
              </div>
              <div className="hero-stat">
                <span className="hero-stat-value">&lt;2s</span>
                <span className="hero-stat-label">Query Speed</span>
              </div>
              <div className="hero-stat">
                <span className="hero-stat-value">100%</span>
                <span className="hero-stat-label">Private & Secure</span>
              </div>
            </div>
          </div>

          {/* INTERACTIVE MOCKUP */}
          <div className="hero-mockup-wrapper">
            <div className="showcase-mockup">
              {/* Chrome bar */}
              <div className="mockup-chrome">
                <div className="mockup-chrome-dot" style={{ backgroundColor: '#ff5f56' }} />
                <div className="mockup-chrome-dot" style={{ backgroundColor: '#ffbd2e' }} />
                <div className="mockup-chrome-dot" style={{ backgroundColor: '#27c93f' }} />
                <div className="mockup-chrome-url">
                  <Shield size={10} style={{ marginRight: '4px', opacity: 0.5 }} />
                  localhost:3000
                </div>
              </div>
              {/* App layout */}
              <div className="mockup-inner">
                <div className="mockup-sidebar">
                  <div className="mockup-sidebar-title">Your Documents</div>
                  <div className="mockup-doc-item active">
                    <FileText size={13} />
                    <span>financial_report.xlsx</span>
                  </div>
                  <div className="mockup-doc-item">
                    <FileText size={13} />
                    <span>product_roadmap.pdf</span>
                  </div>
                  <div className="mockup-doc-item">
                    <FileText size={13} />
                    <span>meeting_notes.docx</span>
                  </div>
                </div>
                <div className="mockup-chat">
                  <div className="mockup-chat-header">
                    <Sparkles size={14} color="var(--primary)" />
                    <span>DeepInsight</span>
                    <span style={{ fontWeight: 400, fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>financial_report.xlsx</span>
                  </div>
                  <div className="mockup-messages">
                    <div className="mockup-msg user">
                      What were the Q3 financial highlights?
                    </div>
                    <div className="mockup-msg assistant">
                      Based on your financial report, here are the key highlights:<br />
                      • Revenue grew <strong>12.4%</strong> quarter-over-quarter<br />
                      • Operational expenses reduced by <strong>4.2%</strong><br />
                      • Net profit margin reached <strong>18.5%</strong>
                      <div className="citation">
                        <FileText size={10} /> financial_report.xlsx — page 4
                      </div>
                    </div>
                  </div>
                  <div className="mockup-input-area">
                    <Search size={14} />
                    Ask a question about your documents...
                    <Send size={14} className="mockup-send-icon" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* TRUSTED BY */}
        <section className="trusted-section">
          <p className="section-label">Trusted by teams at</p>
          <div className="trusted-logos">
            <span className="trusted-logo-placeholder">Acme Corp</span>
            <span className="trusted-logo-placeholder">Globex Inc.</span>
            <span className="trusted-logo-placeholder">Initech</span>
            <span className="trusted-logo-placeholder">Umbrella Co.</span>
            <span className="trusted-logo-placeholder">Stark Labs</span>
          </div>
        </section>

        {/* FEATURES GRID SECTION */}
        <section className="features-section">
          <div className="section-header">
            <span className="section-label">Features</span>
            <h2>Everything You Need, Nothing You Don&apos;t</h2>
            <p>From ingestion to insights — a complete pipeline for document intelligence.</p>
          </div>
          <div className="features-grid">
            <div className="feature-card glass-panel">
              <div className="feature-icon-wrapper">
                <UploadCloud size={24} />
              </div>
              <h3>Multi-Format Ingestion</h3>
              <p>Drop in PDFs, DOCX files, XLSX spreadsheets, and scanned images. Indexed automatically.</p>
            </div>
            <div className="feature-card glass-panel">
              <div className="feature-icon-wrapper">
                <Search size={24} />
              </div>
              <h3>Semantic Search</h3>
              <p>Vector embeddings find answers by meaning and context, not just keyword matching.</p>
            </div>
            <div className="feature-card glass-panel">
              <div className="feature-icon-wrapper">
                <Lightbulb size={24} />
              </div>
              <h3>Auto Insights</h3>
              <p>Get summaries, key findings, and follow-up question suggestions from every uploaded document.</p>
            </div>
            <div className="feature-card glass-panel">
              <div className="feature-icon-wrapper">
                <Shield size={24} />
              </div>
              <h3>Private & Secure</h3>
              <p>Your documents stay in your personal, sandboxed database. No third-party data sharing.</p>
            </div>
          </div>
        </section>

        {/* WORKFLOW STEPS SECTION */}
        <section className="workflow-section">
          <div className="section-header">
            <span className="section-label">How It Works</span>
            <h2>Three Steps to Your Internal Brain</h2>
            <p>From raw files to conversational knowledge in minutes.</p>
          </div>
          <div className="workflow-grid">
            <div className="step-card glass-panel">
              <div className="step-num">01</div>
              <h3>Upload & Ingest</h3>
              <p>Drag and drop your documents. Our system parses tables, headers, and visual content.</p>
            </div>
            <div className="step-card glass-panel">
              <div className="step-num">02</div>
              <h3>Index & Vectorize</h3>
              <p>Documents are chunked, embedded, and stored in a specialized vector search database.</p>
            </div>
            <div className="step-card glass-panel">
              <div className="step-num">03</div>
              <h3>Chat & Discover</h3>
              <p>Ask questions in plain English. Get cited answers, summaries, and cross-document insights.</p>
            </div>
          </div>
        </section>

        {/* CTA BANNER */}
        <section className="cta-section">
          <div className="cta-inner">
            <h2>Ready to Unlock Your Documents?</h2>
            <p>Start for free. No credit card required. Your data stays private.</p>
            <button
              className="cta-btn"
              onClick={() => { setAuthMode("register"); setShowAuthModal(true); }}
            >
              Create Free Account <ArrowRight size={18} />
            </button>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="landing-footer">
          <div>© 2026 SourceSeek. All rights reserved.</div>
          <div className="landing-footer-links">
            <span>Privacy Policy</span>
            <span>Terms of Service</span>
            <span>Support</span>
          </div>
        </footer>

        {/* AUTH MODAL OVERLAY */}
        {showAuthModal && (
          <div className="auth-modal-overlay" onClick={() => setShowAuthModal(false)}>
            <div className="auth-modal-card" onClick={(e) => e.stopPropagation()}>
              <button className="modal-close-btn" onClick={() => setShowAuthModal(false)}>
                <X size={18} />
              </button>

              {/* Gradient accent bar */}
              <div className="auth-modal-accent" />

              <div className="auth-modal-body">
                {/* Logo */}
                <div className="auth-modal-logo">
                  <div className="auth-modal-logo-icon">
                    <Database size={18} color="white" />
                  </div>
                  <span className="auth-modal-logo-text">SourceSeek</span>
                </div>

                {/* Heading */}
                <div className="auth-modal-heading">
                  <h2>{authMode === "login" ? "Welcome back" : "Create your account"}</h2>
                  <p>{authMode === "login" ? "Sign in to access your knowledge base" : "Start indexing your documents for free"}</p>
                </div>

                {/* Tabs */}
                <div className="auth-tabs">
                  <button
                    className={`auth-tab ${authMode === "login" ? "active" : ""}`}
                    onClick={() => { setAuthMode("login"); setAuthError(""); }}
                  >
                    Log In
                  </button>
                  <button
                    className={`auth-tab ${authMode === "register" ? "active" : ""}`}
                    onClick={() => { setAuthMode("register"); setAuthError(""); }}
                  >
                    Sign Up
                  </button>
                </div>

                {/* Form */}
                <form onSubmit={handleAuth} className="auth-modal-form">
                  <div className="auth-input-group">
                    <label className="auth-input-label">Username</label>
                    <div className="auth-input-wrapper">
                      <User size={16} className="auth-input-icon" />
                      <input
                        type="text"
                        placeholder="Enter your username"
                        value={authUsername}
                        onChange={(e) => setAuthUsername(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <div className="auth-input-group">
                    <label className="auth-input-label">Password</label>
                    <div className="auth-input-wrapper">
                      <Shield size={16} className="auth-input-icon" />
                      <input
                        type="password"
                        placeholder="Enter your password"
                        value={authPassword}
                        onChange={(e) => setAuthPassword(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  {authError && <div className="auth-error-msg">{authError}</div>}

                  <button type="submit" className="auth-submit-btn" disabled={isAuthenticating}>
                    {isAuthenticating ? (
                      <><Loader2 className="spinner" size={18} /> Please wait...</>
                    ) : (
                      <>{authMode === "login" ? "Sign In" : "Create Account"} <ArrowRight size={16} /></>
                    )}
                  </button>
                </form>
              </div>

              <div className="auth-modal-footer">
                {authMode === "login" ? "Don't have an account? " : "Already have an account? "}
                <span onClick={() => { setAuthMode(authMode === "login" ? "register" : "login"); setAuthError(""); }}>
                  {authMode === "login" ? "Sign up for free" : "Log in instead"}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* LEFT SIDEBAR - Document Ingestion */}
      <aside className="sidebar glass-panel">
        <div className="sidebar-header" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', padding: '0.5rem 0' }}>
          <div style={{ 
            background: 'var(--primary)', 
            padding: '8px', 
            borderRadius: '10px', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            boxShadow: '0 4px 15px var(--primary-glow)' 
          }}>
            <Database size={20} color="white" />
          </div>
          <h2 style={{ 
            margin: 0, 
            fontSize: '1.5rem', 
            fontWeight: 800, 
            letterSpacing: '-0.5px',
            fontFamily: 'Manrope, sans-serif',
            background: 'linear-gradient(135deg, var(--text-main), var(--primary))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            SourceSeek
          </h2>
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
                    <button className="doc-action-btn" onClick={() => downloadDocument(doc.id, doc.filename)} title="Download file">
                      <DownloadCloud size={16} />
                    </button>
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ 
              background: 'var(--bg-color)', 
              padding: '6px', 
              borderRadius: '8px', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              border: '1px solid var(--border)'
            }}>
              <Sparkles size={16} color="var(--primary)" />
            </div>
            <h3 style={{ 
              margin: 0, 
              fontSize: '1.1rem', 
              fontWeight: 700, 
              letterSpacing: '-0.3px',
              color: 'var(--text-main)',
              fontFamily: 'Manrope, sans-serif'
            }}>
              {currentContextFile ? (
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>Chat /</span> {currentContextFile}
                </span>
              ) : 'DeepInsight'}
            </h3>
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
            <button 
              className="btn-secondary" 
              onClick={toggleTheme}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}
              title="Toggle Theme"
            >
              {theme === 'dark' ? <Moon size={16} /> : theme === 'light' ? <Sun size={16} /> : <Monitor size={16} />}
              {theme === 'system' ? 'System' : theme === 'dark' ? 'Dark' : 'Light'}
            </button>
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

        <div className="chat-window glass-panel" ref={chatWindowRef}>
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
              ) : showInsights && insights && (insights.insights.length > 0 || insights.suggestions.length > 0) ? (
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
                  <p>
                    {currentContextFile 
                      ? `Ask a question about ${currentContextFile}` 
                      : "Ask a question about your uploaded documents."}
                  </p>
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
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxWidth: msg.role === 'assistant' ? '85%' : '75%' }}>
                    <div className={`message-bubble ${msg.role}`}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                    {msg.role === 'assistant' && (
                      <button
                        onClick={() => {
                          setShowExportModal(true);
                          setExportError("");
                          setExportSuccess("");
                        }}
                        style={{
                          alignSelf: 'flex-start',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          background: 'none',
                          border: '1px solid var(--border)',
                          borderRadius: '6px',
                          padding: '0.25rem 0.6rem',
                          fontSize: '0.75rem',
                          color: 'var(--text-muted)',
                          cursor: 'pointer',
                          transition: 'all 0.2s',
                        }}
                        onMouseEnter={e => {
                          (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--primary)';
                          (e.currentTarget as HTMLButtonElement).style.color = 'var(--primary)';
                        }}
                        onMouseLeave={e => {
                          (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)';
                          (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)';
                        }}
                        title="Export this conversation"
                      >
                        <DownloadCloud size={12} /> Export chat
                      </button>
                    )}
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
                    {Array.from(new Set(chatHistories.flatMap(h => h.associated_filename ? h.associated_filename.split(',').map((f: string) => f.trim()) : []))).map((filename: any, idx) => (
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
                                  backgroundColor: 'var(--bg-secondary)', 
                                  color: 'var(--text-muted)', 
                                  padding: '0.1rem 0.4rem', 
                                  borderRadius: '4px',
                                  border: '1px solid var(--border)',
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
          background: var(--bg-secondary);
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
        .doc-item { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; border-radius: 6px; background: var(--bg-secondary); transition: all 0.2s; }
        .doc-item:hover { background: var(--border); }
        .doc-info { display: flex; align-items: center; gap: 0.5rem; overflow: hidden; }
        .doc-name { font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
        .doc-action-btn { background: transparent; border: none; color: var(--text-muted); cursor: pointer; padding: 0.25rem; border-radius: 4px; display: flex; opacity: 0.5; transition: all 0.2s; }
        .doc-item:hover .doc-action-btn { opacity: 1; }
        .doc-action-btn:hover { color: var(--primary); background: var(--primary-glow); }
        .doc-action-btn.delete:hover { color: var(--danger); background: rgba(196, 91, 91, 0.1); }
        .doc-item.active { background: var(--primary-glow); border-left: 2px solid var(--primary); }
        .right-sidebar { width: 300px; flex-shrink: 0; }
        .history-list .doc-info { align-items: flex-start; margin-top: 0.2rem; }
        
        .insights-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem; color: var(--text-muted); padding: 3rem 0; width: 100%; height: 100%; }
        .insights-container { width: 100%; max-width: 800px; text-align: left; padding: 2rem; display: flex; flex-direction: column; align-items: stretch; justify-content: flex-start; height: 100%; }
        .insights-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; }
        .insights-header h2 { margin: 0; font-size: 1.5rem; color: var(--text-main); }
        .insights-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-bottom: 2rem; width: 100%; }
        .insight-card { padding: 1.25rem; border-radius: 12px; background: var(--bg-secondary); backdrop-filter: blur(12px); border: 1px solid var(--border); display: flex; flex-direction: column; justify-content: space-between; transition: all 0.3s ease; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }
        .insight-card:hover { transform: translateY(-2px); border-color: var(--primary-glow); box-shadow: 0 8px 24px rgba(0,0,0,0.05); }
        .insight-card p { margin: 0; font-size: 0.95rem; line-height: 1.5; color: var(--text-main); margin-bottom: 0.75rem; }
        .insight-source { display: flex; align-items: center; gap: 0.25rem; font-size: 0.75rem; color: var(--text-muted); padding-top: 0.5rem; border-top: 1px solid var(--border); font-style: italic; }
        .suggestions-section { display: flex; flex-direction: column; gap: 1rem; }
        .suggestions-header { display: flex; align-items: center; gap: 0.5rem; }
        .suggestions-header h4 { margin: 0; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }
        .suggestions-chips { display: flex; flex-wrap: wrap; gap: 0.75rem; }
        .suggestion-chip { background: var(--bg-secondary); backdrop-filter: blur(8px); border: 1px solid var(--border); padding: 0.75rem 1rem; border-radius: 20px; font-size: 0.9rem; color: var(--text-main); cursor: pointer; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); text-align: left; line-height: 1.3; max-width: 100%; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
        .suggestion-chip:hover { background: var(--card-bg); border-color: var(--primary); transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.06); }
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

      {/* Export Modal */}
      {showExportModal && (
        <div className="modal-overlay" onClick={() => setShowExportModal(false)}>
          <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '400px' }}>
            <h3 style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <DownloadCloud color="var(--primary)" size={20} /> Export Conversation
            </h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Format selection */}
              <div>
                <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '0.5rem' }}>
                  Choose Format
                </label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button 
                    type="button" 
                    className={`btn-secondary ${exportFormat === 'pdf' ? 'active' : ''}`}
                    onClick={() => setExportFormat('pdf')}
                    style={{ flex: 1, padding: '0.6rem', border: exportFormat === 'pdf' ? '1px solid var(--primary)' : '1px solid var(--border)', background: exportFormat === 'pdf' ? 'var(--primary-glow)' : 'transparent' }}
                  >
                    PDF Document
                  </button>
                  <button 
                    type="button" 
                    className={`btn-secondary ${exportFormat === 'docx' ? 'active' : ''}`}
                    onClick={() => setExportFormat('docx')}
                    style={{ flex: 1, padding: '0.6rem', border: exportFormat === 'docx' ? '1px solid var(--primary)' : '1px solid var(--border)', background: exportFormat === 'docx' ? 'var(--primary-glow)' : 'transparent' }}
                  >
                    Word (DOCX)
                  </button>
                </div>
              </div>

              {/* Save to B2 Cloud Toggle */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem', background: 'var(--bg-secondary)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                  <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Save to Cloud</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Store in Backblaze B2</span>
                </div>
                <input 
                  type="checkbox" 
                  checked={exportSaveToB2} 
                  onChange={(e) => setExportSaveToB2(e.target.checked)}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
              </div>

              {exportError && <div style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>{exportError}</div>}
              {exportSuccess && <div style={{ color: 'var(--primary)', fontSize: '0.85rem', fontWeight: 500 }}>{exportSuccess}</div>}

              {/* Action buttons */}
              <div className="modal-actions" style={{ marginTop: '0.5rem' }}>
                <button 
                  className="btn-secondary" 
                  onClick={() => setShowExportModal(false)}
                  disabled={isExporting}
                >
                  Cancel
                </button>
                <button 
                  className="btn-primary" 
                  onClick={handleExport}
                  disabled={isExporting}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}
                >
                  {isExporting ? (
                    <><Loader2 className="spinner" size={16} /> Exporting...</>
                  ) : (
                    <>Confirm Export</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
