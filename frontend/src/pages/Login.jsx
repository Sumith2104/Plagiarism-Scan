import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { Lock, Mail, User, ShieldCheck, ArrowRight, Sparkles } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const { login, register } = useAuth();
  const notify = useNotification();
  const navigate = useNavigate();

  const handleFillDemo = () => {
    setEmail('testuser1@example.com');
    setPassword('password123');
    setIsRegister(false);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      if (isRegister) {
        await register(email, password, fullName);
        navigate('/dashboard');
      } else {
        await login(email, password);
        navigate('/dashboard');
      }
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        (isRegister ? 'Registration failed.' : 'Incorrect email or password.');
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden selection:bg-indigo-500 selection:text-white">
      {/* Dynamic Background Glows */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl animate-pulse" />
        <div
          className="absolute -bottom-40 -left-40 w-96 h-96 bg-cyan-600/20 rounded-full blur-3xl animate-pulse"
          style={{ animationDelay: '2s' }}
        />
        <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] opacity-30" />
      </div>

      <div className="relative bg-slate-900/80 backdrop-blur-2xl rounded-3xl shadow-2xl w-full max-w-md p-8 border border-slate-700/60 transition-all duration-300">
        {/* Brand Header with Custom Project Logo */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center mb-3">
            <div className="w-20 h-20 rounded-2xl bg-white/95 p-2 shadow-xl border border-white/20 flex items-center justify-center ring-4 ring-indigo-500/20 transform hover:scale-105 transition-transform duration-300">
              <img
                src="/logo-icon.png"
                alt="PlagiaScan Logo"
                className="w-full h-full object-contain"
                onError={(e) => {
                  e.target.src = '/logo.png';
                }}
              />
            </div>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Plagia<span className="text-indigo-400">Scan</span>
          </h1>
          <p className="text-slate-400 text-xs mt-1 font-medium">
            Forensic &amp; AI-Powered Academic Integrity
          </p>
        </div>

        {/* Mode Switcher Tabs */}
        <div className="flex bg-slate-800/80 p-1 rounded-xl mb-6 border border-slate-700/50">
          <button
            type="button"
            onClick={() => {
              setIsRegister(false);
              setError('');
            }}
            className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
              !isRegister
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setIsRegister(true);
              setError('');
            }}
            className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
              isRegister
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Auth Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <div className="animate-fadeIn">
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-800/90 border border-slate-700 rounded-xl text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                  placeholder="e.g. Shree Hari"
                  required={isRegister}
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-800/90 border border-slate-700 rounded-xl text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                placeholder="name@university.edu"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-800/90 border border-slate-700 rounded-xl text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          {error && (
            <div className="bg-rose-500/15 border border-rose-500/40 text-rose-300 text-xs px-3.5 py-2.5 rounded-xl flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full mt-2 bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold py-3 px-4 rounded-xl transition-all duration-200 disabled:opacity-50 shadow-lg shadow-indigo-600/25 flex items-center justify-center gap-2 text-sm"
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <svg
                  className="animate-spin h-4 w-4 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Processing...
              </span>
            ) : (
              <>
                <span>{isRegister ? 'Create Account & Continue' : 'Sign In to Workspace'}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Quick Demo Fill Shortcut for Reviewers */}
        <div className="mt-6 pt-5 border-t border-slate-800 text-center">
          <button
            type="button"
            onClick={handleFillDemo}
            className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium py-1 px-2.5 rounded-lg hover:bg-slate-800/60 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Use Demo Account: testuser1@example.com</span>
          </button>
        </div>
      </div>
    </div>
  );
}
