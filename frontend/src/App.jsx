import React, { useState } from 'react';
import axios from 'axios';
import { Upload, Scale, FileJson, CheckCircle, AlertCircle } from 'lucide-react';

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
      setArticles(response.data.articles);
      setLoading(false);
    } catch (err) {
      setError(err.response?.data?.detail || "Parsing failed. Ensure the file is a legal PDF.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-serif">
      {/* Navigation */}
      <nav className="bg-[#002b47] text-white p-6 border-b-4 border-[#a87a4d]">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <Scale className="text-[#a87a4d]" size={32} />
          <h1 className="text-2xl font-bold tracking-tight">Labor Law AI Cloud</h1>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto p-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          
          {/* Upload Section */}
          <div className="md:col-span-1 bg-white p-6 rounded-xl shadow-sm border border-slate-200 h-fit">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2 uppercase tracking-wide">
              <Upload size={18} /> Import Code
            </h2>
            <input 
              type="file" 
              accept=".pdf"
              onChange={handleFileChange}
              className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-[#002b47] file:text-white hover:file:bg-slate-700 cursor-pointer"
            />
            <button 
              onClick={uploadAndParse}
              disabled={!file || loading}
              className="w-full mt-6 bg-[#a87a4d] text-white py-3 rounded-lg font-bold hover:brightness-110 disabled:opacity-50 transition-all"
            >
              {loading ? 'AI Parsing...' : 'Analyze & Store'}
            </button>
            {error && <p className="mt-4 text-red-600 text-sm flex items-center gap-1"><AlertCircle size={14}/> {error}</p>}
          </div>

          {/* Results Section */}
          <div className="md:col-span-2 space-y-4">
            <h2 className="text-lg font-bold uppercase tracking-wide">Validated Articles</h2>
            {articles.length === 0 ? (
              <div className="bg-white border-2 border-dashed border-slate-200 rounded-xl p-20 text-center text-slate-400">
                Upload a Labor Code PDF to begin AI extraction.
              </div>
            ) : (
              articles.map((art, i) => (
                <div key={i} className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:border-[#a87a4d] transition-all group">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-[#a87a4d] font-bold text-xs uppercase">Article {art.article_number}</span>
                      <h3 className="text-xl font-bold mt-1 text-slate-800">{art.title}</h3>
                      <p className="mt-3 text-slate-600 leading-relaxed line-clamp-3">{art.content}</p>
                    </div>
                    <FileJson className="text-slate-300 group-hover:text-[#002b47] transition-colors" />
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