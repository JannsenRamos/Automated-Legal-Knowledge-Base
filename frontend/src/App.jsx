import React, { useState } from 'react';
import axios from 'axios';
import { Upload, Scale, FileJson, CheckCircle, AlertCircle, Bookmark, File, ArrowRight } from 'lucide-react';

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [articles, setArticles] = useState([]);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      if (e.dataTransfer.files[0].type === 'application/pdf') {
        setFile(e.dataTransfer.files[0]);
        setError(null);
      } else {
        setError('Please drop a PDF file');
      }
    }
  };

  const uploadAndParse = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Points to the /api route defined in your vercel.json
      const response = await axios.post('/api/upload', formData);
      
      // Ensure we access the 'articles' key from the backend response
      if (response.data.success) {
        setArticles(response.data.articles || []);
      } else {
        throw new Error(response.data.detail || "Analysis failed");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Regex failed to find articles. Check the backend terminal.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-serif">
      {/* Navigation */}
      <nav className="bg-[#002b47] text-white p-6 border-b-4 border-[#a87a4d] sticky top-0 z-50 shadow-md">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Scale className="text-[#a87a4d]" size={32} />
            <h1 className="text-2xl font-bold tracking-tight">Labor Law AI Cloud</h1>
          </div>
          <div className="text-xs text-[#a87a4d] font-mono uppercase bg-slate-900 px-3 py-1 rounded">
             V2.0 Cloud Connected
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto p-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          
          {/* Upload Section */}
          <div className="md:col-span-1 h-fit sticky top-28">
            <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8 overflow-hidden">
              <h2 className="text-lg font-bold mb-6 flex items-center gap-2 uppercase tracking-wide text-[#002b47]">
                <Upload size={20} className="text-[#a87a4d]" /> Import Document
              </h2>
              
              {/* Drag & Drop Zone */}
              <div 
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                  dragActive 
                    ? 'border-[#a87a4d] bg-amber-50 scale-105' 
                    : 'border-slate-300 bg-slate-50 hover:border-[#a87a4d] hover:bg-amber-50'
                }`}
              >
                <input 
                  type="file" 
                  accept=".pdf"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                
                <div className="flex flex-col items-center gap-3">
                  <div className={`p-4 rounded-lg transition-colors ${dragActive ? 'bg-[#a87a4d]' : 'bg-slate-200'}`}>
                    <Upload size={32} className={dragActive ? 'text-white' : 'text-slate-600'} />
                  </div>
                  <div>
                    <p className="font-bold text-slate-700">Drag & drop your PDF</p>
                    <p className="text-xs text-slate-500 mt-1">or click to browse</p>
                  </div>
                </div>
              </div>

              {/* File Selected Display */}
              {file && (
                <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
                  <CheckCircle size={16} className="text-green-600" />
                  <span className="text-sm text-green-700 font-medium truncate">{file.name}</span>
                </div>
              )}

              {/* Analyze Button */}
              <button 
                onClick={uploadAndParse}
                disabled={!file || loading}
                className="w-full mt-6 bg-gradient-to-r from-[#a87a4d] to-[#c49566] text-white py-3 rounded-lg font-bold hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md active:scale-95 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <span className="animate-spin text-lg">⚡</span> Analyzing...
                  </>
                ) : (
                  <>
                    Analyze & Store
                    <ArrowRight size={16} />
                  </>
                )}
              </button>

              {/* Error Display */}
              {error && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs flex items-start gap-2 font-sans">
                  <AlertCircle size={14} className="mt-0.5 flex-shrink-0" /> 
                  <span>{error}</span>
                </div>
              )}

              {/* Help Text */}
              <div className="mt-6 pt-6 border-t border-slate-200">
                <p className="text-xs text-slate-500 leading-relaxed font-sans">
                  📄 Supports PDF files • 🔍 AI-powered extraction • ⚖️ Labor law specialized
                </p>
              </div>
            </div>
          </div>

          {/* Results Section */}
          <div className="md:col-span-2 space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-bold uppercase tracking-widest text-slate-700">Extracted Articles</h2>
              <span className="bg-gradient-to-r from-[#a87a4d] to-[#c49566] text-white text-xs font-bold px-3 py-1 rounded-full">
                {articles.length} Found
              </span>
            </div>
            
            {articles.length === 0 ? (
              <div className="bg-gradient-to-br from-slate-50 to-amber-50 border-2 border-dashed border-slate-300 rounded-2xl p-16 text-center">
                <div className="flex justify-center mb-6">
                  <div className="p-4 bg-white rounded-full shadow-md">
                    <Bookmark className="text-slate-300" size={56} />
                  </div>
                </div>
                <h3 className="text-xl font-bold text-slate-700 mb-2">No Articles Yet</h3>
                <p className="text-slate-600 font-sans mb-4">
                  Upload a Labor Code PDF to begin AI-powered article extraction and analysis.
                </p>
                <div className="inline-block bg-blue-50 border border-blue-200 rounded-lg p-3 text-left mt-4">
                  <p className="text-xs text-blue-800 font-mono">
                    <span className="font-bold">💡 Tip:</span> Our AI identifies articles, extracts titles and content, and highlights repealed sections.
                  </p>
                </div>
              </div>
            ) : (
              articles.map((art, i) => (
                <div 
                  key={i} 
                  className="bg-white rounded-2xl border border-slate-200 shadow-md hover:shadow-xl transition-all overflow-hidden group animate-in slide-in-from-bottom-3"
                >
                  {/* Article Header with Left Accent */}
                  <div className="h-1 bg-gradient-to-r from-[#a87a4d] to-[#c49566]"></div>
                  
                  <div className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="bg-[#a87a4d] text-white font-black text-sm px-3 py-1 rounded-lg">
                          Article {art.article_number}
                        </span>
                        {art.old_article_number && (
                          <span className="text-slate-500 text-xs italic bg-slate-100 px-2 py-1 rounded">
                            Old: {art.old_article_number}
                          </span>
                        )}
                        {art.is_repealed && (
                          <span className="bg-red-100 text-red-700 text-xs font-bold px-3 py-1 rounded-lg ml-auto">
                            ⚠️ REPEALED
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <h3 className="text-lg font-bold text-[#002b47] mb-4 leading-snug">
                      {art.title}
                    </h3>
                    
                    <p className="text-slate-700 leading-relaxed font-sans text-sm whitespace-pre-wrap mb-6 text-justify">
                      {art.content}
                    </p>
                    
                    <div className="flex items-center gap-3 text-xs font-semibold text-slate-500 uppercase tracking-wide pt-4 border-t border-slate-100">
                      <span className="flex items-center gap-1 bg-amber-50 px-3 py-2 rounded-lg text-[#a87a4d]">
                        <FileJson size={14} /> {art.metadata?.corpus_category || 'General'}
                      </span>
                      <span className="flex items-center gap-1 bg-blue-50 px-3 py-2 rounded-lg text-blue-700">
                        📄 Page {art.metadata?.page_number || 0}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}