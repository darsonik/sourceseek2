"use client";

import { useState } from "react";
import { UploadCloud, Search, FileText, Loader2, Sparkles, Database } from "lucide-react";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResult, setSearchResult] = useState("");

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
      // Direct call to FastAPI running on 8000
      const res = await fetch("http://127.0.0.1:8000/api/v1/documents/upload", {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setUploadMessage(`✅ Success! Indexed ${data.chunks_saved} chunks from ${data.filename}`);
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

    setIsSearching(true);
    setSearchResult("");

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/search/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: searchQuery }),
      });

      const data = await res.json();
      
      if (res.ok) {
        setSearchResult(data.answer);
      } else {
        setSearchResult(`Error: ${data.detail || 'Search failed'}`);
      }
    } catch (error) {
      setSearchResult("Connection error. Is the backend running?");
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <main className="container">
      <header className="header animate-fade-in" style={{ textAlign: "center", marginBottom: "4rem", marginTop: "2rem" }}>
        <h1 className="text-gradient" style={{ fontSize: "3.5rem", marginBottom: "1rem", display: "inline-flex", alignItems: "center", gap: "1rem" }}>
          <Database size={48} color="var(--primary)" /> SourceSeek
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "1.2rem", maxWidth: "600px", margin: "0 auto" }}>
          Upload your documents, Excel sheets, and images, then instantly query them using our LangGraph AI Search Agent.
        </p>
      </header>

      <div className="layout-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "2rem" }}>
        
        {/* Upload Section */}
        <section className="glass-panel animate-fade-in" style={{ padding: "2rem", animationDelay: "0.1s" }}>
          <h2 style={{ fontSize: "1.8rem", marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <UploadCloud color="var(--secondary)" /> Ingest Documents
          </h2>
          
          <div className="upload-dropzone" style={{ 
            border: "2px dashed var(--border)", 
            borderRadius: "12px", 
            padding: "3rem 2rem", 
            textAlign: "center",
            background: "rgba(255,255,255,0.02)",
            transition: "all 0.3s ease",
            marginBottom: "1.5rem",
            position: "relative"
          }}>
            <input 
              type="file" 
              onChange={handleFileChange} 
              accept=".pdf,.docx,.xlsx,image/*"
              style={{
                position: "absolute",
                top: 0, left: 0, width: "100%", height: "100%",
                opacity: 0, cursor: "pointer"
              }}
            />
            {file ? (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
                <FileText size={48} color="var(--primary)" />
                <p style={{ fontWeight: 600, fontSize: "1.1rem" }}>{file.name}</p>
                <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
                <UploadCloud size={48} color="var(--text-muted)" style={{ opacity: 0.5 }} />
                <p style={{ fontWeight: 500, fontSize: "1.1rem" }}>Click or drag a file here</p>
                <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>Supports PDF, DOCX, XLSX, Images</p>
              </div>
            )}
          </div>

          <button 
            className="btn-primary" 
            onClick={handleUpload} 
            disabled={!file || isUploading}
            style={{ width: "100%" }}
          >
            {isUploading ? <><Loader2 className="spinner" size={20} /> Indexing & Embedding...</> : "Upload & Vectorize"}
          </button>

          {uploadMessage && (
            <div style={{ 
              marginTop: "1.5rem", 
              padding: "1rem", 
              borderRadius: "8px", 
              background: uploadMessage.includes("❌") ? "rgba(239, 68, 68, 0.1)" : "rgba(16, 185, 129, 0.1)",
              border: `1px solid ${uploadMessage.includes("❌") ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.2)"}`,
              color: uploadMessage.includes("❌") ? "var(--danger)" : "var(--success)",
              fontSize: "0.95rem"
            }}>
              {uploadMessage}
            </div>
          )}
        </section>

        {/* Search Section */}
        <section className="glass-panel animate-fade-in" style={{ padding: "2rem", animationDelay: "0.2s", display: "flex", flexDirection: "column" }}>
          <h2 style={{ fontSize: "1.8rem", marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Sparkles color="var(--primary)" /> AI Search Agent
          </h2>
          
          <form onSubmit={handleSearch} style={{ marginBottom: "2rem", display: "flex", gap: "0.5rem" }}>
            <input 
              type="text" 
              className="input-field" 
              placeholder="Ask anything (e.g. 'What is ID1234?')" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              disabled={isSearching}
            />
            <button type="submit" className="btn-primary" disabled={isSearching || !searchQuery.trim()} style={{ padding: "0 1.5rem" }}>
              {isSearching ? <Loader2 className="spinner" size={20} /> : <Search size={20} />}
            </button>
          </form>

          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <h3 style={{ fontSize: "1rem", color: "var(--text-muted)", marginBottom: "1rem", textTransform: "uppercase", letterSpacing: "1px" }}>
              Agent Response
            </h3>
            
            <div className="search-results" style={{ 
              flex: 1,
              background: "rgba(0,0,0,0.2)", 
              borderRadius: "12px", 
              padding: "1.5rem",
              border: "1px solid var(--border)",
              overflowY: "auto",
              minHeight: "250px",
              lineHeight: "1.6",
              whiteSpace: "pre-wrap"
            }}>
              {isSearching ? (
                <div style={{ display: "flex", gap: "1rem", alignItems: "center", color: "var(--text-muted)", height: "100%", justifyContent: "center" }}>
                  <Loader2 className="spinner" size={24} /> 
                  <span>Consulting LangGraph state machine...</span>
                </div>
              ) : searchResult ? (
                <div style={{ animation: "fadeIn 0.4s ease-out" }}>
                  {searchResult}
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", height: "100%", opacity: 0.5, gap: "1rem" }}>
                  <Search size={48} />
                  <p>Awaiting query...</p>
                </div>
              )}
            </div>
          </div>
        </section>

      </div>

      <style jsx global>{`
        .spinner {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </main>
  );
}
