import React, { useState, useEffect } from 'react';
import { Moon, Sun, Mail, Lock, Upload, Search, FileText, LogOut, X, Loader2, BookOpen, Copy, Check } from 'lucide-react';
import './index.css';
import { searchNotes, uploadFile, getMyFiles } from './services/api';

const ThemeToggle = ({ isDark, toggle }) => (
  <button
    onClick={toggle}
    className="fixed top-6 right-6 p-3 rounded-full bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors shadow-lg z-50"
  >
    {isDark ? <Sun className="w-5 h-5 text-yellow-500" /> : <Moon className="w-5 h-5 text-gray-600" />}
  </button>
);

const Login = ({ onLogin }) => {
  const [isSignUp, setIsSignUp] = useState(false);
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    
    try {
      let response;
      if (isSignUp) {
        response = await fetch('http://127.0.0.1:8000/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            username: form.email, 
            password: form.password 
          }),
        });
      } else {
        response = await fetch('http://127.0.0.1:8000/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({
            username: form.email,
            password: form.password,
          }),
        });
      }

      const data = await response.json();

      if (response.ok) {
        if (isSignUp) {
          alert(data.message || "Account created! Login karo.");
          setIsSignUp(false);
          setForm({ email: '', password: '' });
        } else {
          localStorage.setItem('token', data.access_token);
          onLogin();
        }
      } else {
        let errorMsg = "Kuch toh gadbad hai!";
        if (data.detail && Array.isArray(data.detail)) {
          errorMsg = data.detail[0].msg;
        } else if (data.detail) {
          errorMsg = data.detail;
        } else if (data.error) {
          errorMsg = data.error;
        }
        setError(errorMsg);
      }
    } catch (err) {
      setError('Backend connection error!');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-white dark:bg-gray-900">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-white mb-2">Semantic Search</h1>
          <p className="text-gray-600 dark:text-gray-400">
            {isSignUp ? 'Naya account bana le' : 'Sign in kar le bhai'}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800 p-8 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="p-3 text-sm font-medium text-red-500 bg-red-50 dark:bg-red-900/30 rounded-lg border border-red-200 dark:border-red-800">
                ⚠️ {error}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Email / Username</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  required
                  value={form.email}
                  onChange={(e) => setForm({...form, email: e.target.value})}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="password"
                  required
                  value={form.password}
                  onChange={(e) => setForm({...form, password: e.target.value})}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg flex items-center justify-center transition-all"
            >
              {isLoading ? <Loader2 className="animate-spin w-5 h-5" /> : (isSignUp ? 'Account Banao' : 'Sign In Karo')}
            </button>
          </form>
          <div className="mt-6 text-center">
            <button 
              onClick={() => { setIsSignUp(!isSignUp); setError(''); }}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              {isSignUp ? 'Already account? Login kar' : "Naya hai? Signup kar"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const Dashboard = ({ onLogout }) => {
  const [files, setFiles] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState([]); 
  const [aiAnswer, setAiAnswer] = useState(''); 
  const [isDragOver, setIsDragOver] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const loadFiles = async () => {
      try {
        const fileList = await getMyFiles();
        setFiles(fileList.map(name => ({ id: Math.random(), name })));
      } catch (err) {
        console.error("Initial file load failed");
      }
    };
    loadFiles();
  }, []);

  const handleCopy = () => {
    navigator.clipboard.writeText(aiAnswer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFiles = async (newFiles) => {
    setIsUploading(true);
    for (const file of newFiles) {
      try {
        const data = await uploadFile(file);
        if (data.filename) {
          setFiles(prev => [...prev, { id: Date.now(), name: file.name }]);
        }
      } catch (err) {
        console.error("Upload fail:", file.name);
      }
    }
    setIsUploading(false);
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    setAiAnswer('');
    try {
      const data = await searchNotes(searchQuery);
      if (data.matches) setResults(data.matches);
      if (data.ai_answer) setAiAnswer(data.ai_answer);
    } catch (err) {
      console.error("Search error:", err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700 h-16 flex items-center px-6 justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Semantic Search</h1>
        <button onClick={() => { localStorage.removeItem('token'); onLogout(); }} className="flex items-center space-x-2 text-gray-600 dark:text-gray-300 hover:text-red-500 transition-colors">
          <LogOut className="w-4 h-4" /> <span>Sign Out</span>
        </button>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border dark:border-gray-700 h-fit">
          <h2 className="text-lg font-medium mb-4 dark:text-white">Upload Documents</h2>
          <div 
            className={`border-2 border-dashed p-6 rounded-lg text-center transition-all ${isDragOver ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-700'}`}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setIsDragOver(false); handleFiles(Array.from(e.dataTransfer.files)); }}
          >
            <Upload className="mx-auto h-10 w-10 text-gray-400 mb-2" />
            {isUploading ? (
              <div className="flex flex-col items-center">
                <Loader2 className="animate-spin text-blue-600 mb-2" />
                <p className="text-xs dark:text-gray-400">Embedding Vectors...</p>
              </div>
            ) : (
              <label className="cursor-pointer text-blue-600 font-medium">
                Browse Files
                <input type="file" multiple className="hidden" onChange={(e) => handleFiles(Array.from(e.target.files))} />
              </label>
            )}
          </div>
          <div className="mt-4 space-y-2">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">My Library</h3>
            {files.length === 0 ? (
              <p className="text-sm text-gray-400 italic">No files indexed yet.</p>
            ) : (
              files.map(f => (
                <div key={f.id} className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg border dark:border-gray-600 text-sm dark:text-white group">
                  <div className="flex items-center space-x-2 truncate">
                    <FileText className="w-4 h-4 text-blue-400" />
                    <span className="truncate">{f.name}</span>
                  </div>
                  <button onClick={() => setFiles(prev => prev.filter(file => file.id !== f.id))} className="opacity-0 group-hover:opacity-100 transition-opacity">
                    <X className="w-4 h-4 text-gray-400 hover:text-red-500" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border dark:border-gray-700 shadow-sm">
            <h2 className="text-lg font-medium mb-4 dark:text-white">Ask your Notes</h2>
            <form onSubmit={handleSearch} className="flex space-x-2">
              <input 
                type="text" 
                value={searchQuery} 
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 p-3 border dark:border-gray-600 rounded-lg bg-transparent dark:text-white outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                placeholder="What does your data say?..."
              />
              <button type="submit" disabled={isSearching} className="px-6 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center">
                {isSearching ? <Loader2 className="animate-spin" /> : <Search className="w-5 h-5" />}
              </button>
            </form>
          </div>

          {/* AI Answer Section - Formatted for clean pointers */}
          {aiAnswer && (
            <div className="bg-white dark:bg-gray-800 border-l-4 border-blue-500 p-6 rounded-r-xl shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-500 relative group">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400">
                  <BookOpen className="w-5 h-5" />
                  <h3 className="font-bold uppercase text-xs tracking-widest">AI Analysis</h3>
                </div>
                <button 
                  onClick={handleCopy}
                  className="p-2 text-gray-400 hover:text-blue-500 transition-colors rounded-lg bg-gray-50 dark:bg-gray-700 opacity-0 group-hover:opacity-100"
                  title="Copy to clipboard"
                >
                  {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <div className="text-gray-800 dark:text-gray-200 leading-relaxed text-sm space-y-3">
                {aiAnswer.split('\n').map((line, i) => {
                  const isBullet = line.trim().startsWith('*') || line.trim().startsWith('-') || /^\d+\./.test(line.trim());
                  const isHeader = line.trim().startsWith('#');
                  
                  if (isHeader) return <h4 key={i} className="font-bold text-blue-600 dark:text-blue-400 mt-4 uppercase text-xs tracking-wider">{line.replace(/#/g, '').trim()}</h4>;
                  
                  return (
                    <p key={i} className={`${isBullet ? "ml-4 pl-3 border-l-2 border-blue-100 dark:border-gray-700 italic text-gray-700 dark:text-gray-300" : ""} ${line.trim() === "" ? "h-2" : ""}`}>
                      {line.replace(/^[*|-]\s*/, '')}
                    </p>
                  );
                })}
              </div>
            </div>
          )}

          {results.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-[0.2em] ml-1">Evidence Chunks</h3>
              {results.map((match, i) => (
                <div key={i} className="p-4 bg-white dark:bg-gray-800 rounded-xl border dark:border-gray-700 shadow-sm hover:border-blue-400/50 transition-colors group">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center space-x-2">
                       <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/40 px-2 py-1 rounded-full uppercase tracking-tighter">
                         {match.source}
                       </span>
                    </div>
                    <span className="text-[10px] text-gray-400 font-mono">Rank #{i + 1}</span>
                  </div>
                  <p className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed whitespace-pre-wrap italic">
                    {match.text.length > 300 ? `${match.text.substring(0, 300)}...` : match.text}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('theme');
    if (saved) setIsDark(saved === 'dark');
    if (localStorage.getItem('token')) setIsAuthenticated(true);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  return (
    <>
      <ThemeToggle isDark={isDark} toggle={() => setIsDark(!isDark)} />
      {isAuthenticated ? <Dashboard onLogout={() => setIsAuthenticated(false)} /> : <Login onLogin={() => setIsAuthenticated(true)} />}
    </>
  );
};

export default App;