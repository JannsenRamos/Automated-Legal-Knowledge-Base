import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [file, setFile] = useState(null);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null); // 'loading', 'success', 'error'
  const [error, setError] = useState(null);

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setStatus('loading');
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post('/api/upload', formData);
      setArticles(res.data.articles);
      setStatus('success');
    } catch (err) {
      setError(err.response?.data?.detail || "Parsing failed");
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-[#002b47] text-white p-6 border-b-4 border-[#a87a4d] shadow-lg">
        <h1 className="text-3xl font-bold tracking-tight">Labor Law AI Cloud</h1>
      </nav>

      <main className="max-w-6xl mx-auto p-8 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-1 bg-white p-6 rounded-xl shadow-md border border-slate-200">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">Import Code</h2>
          <input 
            type="file" 
            onChange={(e) => setFile(e.target.files[0])}
            className="block w-full text-sm text-slate-500 mb-4 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-slate-100 file:text-[#002b47] hover:file:bg-slate-200"
          />
          <button 
            onClick={handleUpload}
            disabled={loading || !file}
            className="w-full bg-[#a87a4d] text-white py-3 rounded-lg font-bold hover:bg-[#8e6641] disabled:opacity-50 transition-all"
          >
            {loading ? 'Analyzing...' : 'Analyze & Store'}
          </button>
        </div>

        <div className="md:col-span-2">
          {status === 'loading' && (
            <div className="bg-blue-50 border-l-4 border-[#002b47] p-4 mb-6 animate-pulse">
              <p className="text-[#002b47] font-bold">AI is extracting articles... please wait.</p>
            </div>
          )}
          {status === 'error' && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
              <p className="text-red-700 font-bold">Error: {error}</p>
            </div>
          )}
          {status === 'success' && (
            <div className="bg-green-50 border-l-4 border-green-500 p-4 mb-6">
              <p className="text-green-700 font-bold">Success! Document stored in Supabase.</p>
            </div>
          )}

          <h2 className="text-2xl font-bold text-[#002b47] mb-4 border-b pb-2">Validated Articles</h2>
          <div className="space-y-4">
            {articles.length > 0 ? articles.map((art, i) => (
              <div key={i} className="bg-white p-4 rounded-lg shadow border-l-4 border-[#a87a4d]">
                <h3 className="font-bold text-lg">{art.title}</h3>
                <p className="text-slate-600 mt-2">{art.content}</p>
                <span className="inline-block mt-3 px-2 py-1 bg-slate-100 text-xs font-bold rounded uppercase">{art.category}</span>
              </div>
            )) : <p className="text-slate-400 italic">No articles extracted yet.</p>}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;