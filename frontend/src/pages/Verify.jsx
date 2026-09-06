import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { scansAPI } from '../api';
import {
    ShieldCheck,
    CheckCircle2,
    Copy,
    Download,
    FileText,
    Calendar,
    Hash,
    Award,
    ExternalLink,
    AlertCircle,
    BookOpen,
    Bot,
    Globe
} from 'lucide-react';

export default function Verify() {
    const { scanId } = useParams();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [copiedHash, setCopiedHash] = useState(false);

    useEffect(() => {
        const fetchVerification = async () => {
            try {
                const res = await scansAPI.verify(scanId);
                setData(res.data);
            } catch (err) {
                console.error('Verification lookup failed:', err);
                setError(err.response?.data?.detail || 'Scan verification record not found or expired.');
            } finally {
                setLoading(false);
            }
        };
        fetchVerification();
    }, [scanId]);

    const handleCopyHash = () => {
        if (data?.sha256_hash) {
            navigator.clipboard.writeText(data.sha256_hash);
            setCopiedHash(true);
            setTimeout(() => setCopiedHash(false), 2000);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center p-4">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-slate-300 font-semibold text-lg">Querying PlagiaScan Trust Authority...</p>
                    <p className="text-slate-500 text-xs mt-1">Verifying cryptographic scan ledger #{scanId}</p>
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center p-4">
                <div className="max-w-md w-full bg-slate-800 border border-slate-700 rounded-2xl p-8 text-center shadow-2xl">
                    <div className="w-16 h-16 bg-red-500/20 text-red-400 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-red-500/30">
                        <AlertCircle className="w-8 h-8" />
                    </div>
                    <h2 className="text-xl font-bold text-white mb-2">Record Verification Failed</h2>
                    <p className="text-slate-400 text-sm mb-6">{error || 'This scan reference does not exist or has been removed.'}</p>
                    <Link
                        to="/"
                        className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-sm transition-all"
                    >
                        Return to Home
                    </Link>
                </div>
            </div>
        );
    }

    const read = data.readability || {};

    return (
        <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
                {/* Authority Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold uppercase tracking-wider mb-4 shadow-sm">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        Official Digital Verification Certificate
                    </div>
                    <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
                        PlagiaScan Authenticity Trust Authority
                    </h1>
                    <p className="text-slate-400 text-sm mt-2 max-w-xl mx-auto">
                        Cryptographic verification of plagiarism audit and statistical AI evaluation record.
                    </p>
                </div>

                {/* Main Certificate Card */}
                <div className="bg-slate-900/90 border border-slate-700/80 rounded-3xl shadow-2xl overflow-hidden backdrop-blur-xl">
                    {/* Certificate Top Banner */}
                    <div className="bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 p-6 text-white flex flex-wrap items-center justify-between gap-4">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-2xl bg-white/20 flex items-center justify-center backdrop-blur-md">
                                <Award className="w-7 h-7 text-white" />
                            </div>
                            <div>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-black uppercase tracking-wider bg-white/20 px-2.5 py-0.5 rounded-full">
                                        Verified Authentic
                                    </span>
                                    <span className="text-xs text-white/80">Scan #{data.scan_id}</span>
                                </div>
                                <h2 className="text-xl font-bold text-white mt-0.5 truncate max-w-md">
                                    {data.document_name}
                                </h2>
                            </div>
                        </div>

                        <a
                            href={`http://${window.location.hostname}:8000/api/v1/scans/${data.scan_id}/pdf`}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-2 px-4 py-2 bg-white text-slate-900 hover:bg-slate-100 rounded-xl text-xs font-bold shadow-md transition-all"
                        >
                            <Download className="w-4 h-4" />
                            Download Certified PDF
                        </a>
                    </div>

                    <div className="p-6 sm:p-8 space-y-8">
                        {/* Scores Grid */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                            <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-5 text-center">
                                <div className="flex items-center justify-center gap-1.5 text-xs text-slate-400 mb-1">
                                    <Globe className="w-3.5 h-3.5 text-red-400" />
                                    <span>Plagiarism Index</span>
                                </div>
                                <p className={`text-4xl font-extrabold ${data.overall_score > 20 ? 'text-red-400' : 'text-emerald-400'}`}>
                                    {data.overall_score}%
                                </p>
                                <p className="text-[11px] text-slate-500 mt-1">
                                    {data.overall_score > 20 ? 'Significant Duplication' : 'Clean / Original'}
                                </p>
                            </div>

                            <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-5 text-center">
                                <div className="flex items-center justify-center gap-1.5 text-xs text-slate-400 mb-1">
                                    <Bot className="w-3.5 h-3.5 text-purple-400" />
                                    <span>AI Probability</span>
                                </div>
                                <p className={`text-4xl font-extrabold ${data.ai_probability > 50 ? 'text-purple-400' : 'text-blue-400'}`}>
                                    {data.ai_probability}%
                                </p>
                                <p className="text-[11px] text-slate-500 mt-1">
                                    {data.ai_probability > 50 ? 'Synthetic LLM Markers' : 'Human Author Style'}
                                </p>
                            </div>

                            <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-5 text-center">
                                <div className="flex items-center justify-center gap-1.5 text-xs text-slate-400 mb-1">
                                    <FileText className="w-3.5 h-3.5 text-amber-400" />
                                    <span>Verbatim Overlap</span>
                                </div>
                                <p className="text-4xl font-extrabold text-amber-400">
                                    {data.verbatim_score}%
                                </p>
                                <p className="text-[11px] text-slate-500 mt-1">Exact identical phrasing</p>
                            </div>

                            <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-5 text-center">
                                <div className="flex items-center justify-center gap-1.5 text-xs text-slate-400 mb-1">
                                    <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                                    <span>Paraphrase / Mosaic</span>
                                </div>
                                <p className="text-4xl font-extrabold text-indigo-400">
                                    {data.paraphrase_score}%
                                </p>
                                <p className="text-[11px] text-slate-500 mt-1">Structural rework match</p>
                            </div>
                        </div>

                        {/* Readability & Stylometrics */}
                        {read && read.flesch_reading_ease !== undefined && (
                            <div className="bg-slate-800/50 border border-slate-700/80 rounded-2xl p-5">
                                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
                                    <BookOpen className="w-4 h-4 text-indigo-400" />
                                    Readability & Stylometrics Breakdown
                                </h3>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                                    <div className="p-3 bg-slate-800 rounded-xl border border-slate-700/60">
                                        <p className="text-xs text-slate-400">Reading Ease (FRE)</p>
                                        <p className="text-xl font-bold text-white mt-1">{read.flesch_reading_ease}</p>
                                        <p className="text-[10px] text-indigo-400 mt-0.5">{read.reading_ease_level}</p>
                                    </div>
                                    <div className="p-3 bg-slate-800 rounded-xl border border-slate-700/60">
                                        <p className="text-xs text-slate-400">Grade Level (FKGL)</p>
                                        <p className="text-xl font-bold text-white mt-1">Grade {read.flesch_kincaid_grade}</p>
                                        <p className="text-[10px] text-slate-400 mt-0.5">Flesch-Kincaid</p>
                                    </div>
                                    <div className="p-3 bg-slate-800 rounded-xl border border-slate-700/60">
                                        <p className="text-xs text-slate-400">Gunning Fog</p>
                                        <p className="text-xl font-bold text-white mt-1">{read.gunning_fog_index}</p>
                                        <p className="text-[10px] text-indigo-400 mt-0.5">{read.fog_reading_level}</p>
                                    </div>
                                    <div className="p-3 bg-slate-800 rounded-xl border border-slate-700/60">
                                        <p className="text-xs text-slate-400">Lexical Richness (TTR)</p>
                                        <p className="text-xl font-bold text-white mt-1">{read.lexical_diversity_ttr}%</p>
                                        <p className="text-[10px] text-slate-400 mt-0.5">Unique vocabulary</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Cryptographic Ledger Details */}
                        <div className="bg-slate-800/50 border border-slate-700/80 rounded-2xl p-5 space-y-3 text-xs">
                            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-2">
                                <Hash className="w-4 h-4 text-emerald-400" />
                                Cryptographic Fingerprint & Metadata
                            </h3>

                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 py-2 border-b border-slate-700/60">
                                <span className="text-slate-400">SHA-256 Checksum:</span>
                                <div className="flex items-center gap-2">
                                    <code className="font-mono text-emerald-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-700 break-all text-[11px]">
                                        {data.sha256_hash}
                                    </code>
                                    <button
                                        onClick={handleCopyHash}
                                        className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-700 transition-all"
                                        title="Copy Hash"
                                    >
                                        {copiedHash ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                                    </button>
                                </div>
                            </div>

                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 py-2 border-b border-slate-700/60">
                                <span className="text-slate-400">Audit Timestamp:</span>
                                <span className="font-medium text-white flex items-center gap-1">
                                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                                    {new Date(data.created_at).toUTCString()}
                                </span>
                            </div>

                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 py-2 border-b border-slate-700/60">
                                <span className="text-slate-400">Audit Engine:</span>
                                <span className="font-medium text-white">{data.engine_version}</span>
                            </div>

                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pt-1">
                                <span className="text-slate-400">Issuing Authority:</span>
                                <span className="font-bold text-emerald-400">{data.issuer}</span>
                            </div>
                        </div>

                        {/* Footnote */}
                        <div className="pt-4 text-center text-xs text-slate-500 border-t border-slate-800">
                            <p>
                                This digital verification record is publicly auditable and serves as non-repudiable proof of document integrity at the timestamp recorded.
                            </p>
                            <div className="mt-4 flex items-center justify-center gap-4">
                                <Link to="/" className="text-indigo-400 hover:text-indigo-300 font-semibold">
                                    PlagiaScan Home
                                </Link>
                                <span>•</span>
                                <Link to="/dashboard" className="text-indigo-400 hover:text-indigo-300 font-semibold">
                                    User Dashboard
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
