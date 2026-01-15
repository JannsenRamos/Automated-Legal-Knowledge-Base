import React, { useState } from 'react';
import axios from 'axios';
import { Upload, Scale, FileJson, CheckCircle, AlertCircle, Bookmark } from 'lucide-react';

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [articles, setArticles] = useState([]);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
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
          <div className="md:col-span-1 bg-white p-6 rounded-xl shadow-lg border border-slate-200 h-fit sticky top-28">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2 uppercase tracking-wide text-[#002b47]">
              <Upload size={18} /> Import Code
            </h2>
            <div className="border-2 border-dashed border-slate-200 rounded-lg p-4 hover:border-[#a87a4d] transition-colors">
                <input 
                  type="file" 
                  accept=".pdf"
                  onChange={handleFileChange}
                  className="block w-full text-xs text-slate-500 file:mr-2 file:py-1 file:px-3 file:rounded-full file:border-0 file:bg-[#002b47] file:text-white cursor-pointer"
                />
            </div>
            <button 
              onClick={uploadAndParse}
              disabled={!file || loading}
              className="w-full mt-6 bg-[#a87a4d] text-white py-4 rounded-lg font-bold hover:brightness-110 disabled:opacity-50 transition-all shadow-md active:scale-95"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin text-lg">🌀</span> Analyzing...
                </span>
              ) : 'Analyze & Store'}
            </button>
            {error && <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded text-red-600 text-xs flex items-center gap-2 font-sans"><AlertCircle size={14}/> {error}</div>}
          </div>

          {/* Results Section */}
          <div className="md:col-span-2 space-y-6">
            <div className="flex justify-between items-center border-b border-slate-200 pb-2">
                <h2 className="text-lg font-bold uppercase tracking-widest text-slate-500">Validated Articles</h2>
                <span className="bg-slate-200 text-slate-700 text-[10px] font-bold px-2 py-0.5 rounded-full">{articles.length} Detected</span>
            </div>
            
            {articles.length === 0 ? (
              <div className="bg-white border-2 border-dashed border-slate-200 rounded-xl p-24 text-center text-slate-400 font-sans shadow-inner">
                <Bookmark className="mx-auto mb-4 opacity-20" size={48} />
                Upload a Labor Code PDF to begin AI extraction.
              </div>
            ) : (
              articles.map((art, i) => (
                <div key={i} className="bg-white p-6 rounded-xl border-l-8 border-l-[#a87a4d] border border-slate-200 shadow-md hover:shadow-xl transition-all group animate-in slide-in-from-bottom-2">
                  <div className="flex justify-between items-start">
                    <div className="w-full">
                      <div className="flex items-center gap-2">
                        <span className="text-[#a87a4d] font-black text-sm uppercase">Art. {art.article_number}</span>
                        {art.old_article_number && (
                            <span className="text-slate-400 text-xs italic">[Old Art. {art.old_article_number}]</span>
                        )}
                        {art.is_repealed && (
                            <span className="bg-red-100 text-red-700 text-[10px] font-black px-2 py-0.5 rounded uppercase ml-auto">REPEALED</span>
                        )}
                      </div>
                      
                      <h3 className="text-xl font-bold mt-2 text-[#002b47] border-b border-slate-100 pb-2">{art.title}</h3>
                      
                      {/* Safety: Use whitespace-pre-wrap to maintain PDF paragraph structure */}
                      <p className="mt-4 text-slate-700 leading-relaxed font-sans text-sm whitespace-pre-wrap">{art.content}</p>
                      
                      <div className="mt-6 flex items-center gap-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                        <span className="flex items-center gap-1 bg-slate-100 px-2 py-1 rounded">
                           <FileJson size={12}/> {art.metadata?.corpus_category || 'General'}
                        </span>
                        <span className="flex items-center gap-1">
                           📄 Page {art.metadata?.page_number || 0}
                        </span>
                      </div>
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