import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { scansAPI } from '../api';
import { ArrowLeft, AlertTriangle, CheckCircle, Clock, Sparkles, TrendingDown, TrendingUp } from 'lucide-react';

export default function Report() {
    const { scanId } = useParams();
    const [scan, setScan] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        loadScan();
    }, [scanId]);

    useEffect(() => {
        let interval;
        if (scan?.status === 'scanning' || scan?.status === 'queued') {
            interval = setInterval(loadScan, 3000);
        }
        return () => clearInterval(interval);
    }, [scan?.status]);

    const loadScan = async () => {
        try {
            const response = await scansAPI.get(scanId);
            setScan(response.data);
            setLoading(false);
        } catch (err) {
            alert('Failed to load scan');
            navigate('/dashboard');
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
                <div className="text-center">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl mb-4 animate-pulse">
                        <Sparkles className="h-8 w-8 text-white" />
                    </div>
                    <p className="text-gray-600 text-lg font-medium">Loading scan results...</p>
                </div>
            </div>
        );
    }

    const getScoreColor = (score) => {
        if (score < 20) return 'text-emerald-600';
        if (score < 50) return 'text-amber-600';
        return 'text-red-600';
    };

    const getScoreBg = (score) => {
        if (score < 20) return 'from-emerald-50 to-teal-50';
        if (score < 50) return 'from-amber-50 to-yellow-50';
        return 'from-red-50 to-pink-50';
    };

    const getScoreIcon = (score) => {
        if (score < 20) return <TrendingDown className="h-16 w-16 text-emerald-600" />;
        if (score < 50) return <AlertTriangle className="h-16 w-16 text-amber-600" />;
        return <TrendingUp className="h-16 w-16 text-red-600" />;
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
            {/* Navbar */}
            <nav className="bg-white/80 backdrop-blur-lg shadow-sm border-b border-gray-200/50 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="flex items-center gap-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 px-4 py-2 rounded-lg transition-all"
                    >
                        <ArrowLeft className="h-5 w-5" />
                        <span className="font-medium">Back to Dashboard</span>
                    </button>
                </div>
            </nav>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="bg-white rounded-2xl shadow-xl p-8 mb-6 border border-gray-200">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
                            <Sparkles className="h-6 w-6 text-white" />
                        </div>
                        <h1 className="text-3xl font-bold text-gray-800">Plagiarism Report</h1>
                    </div>

                    {scan.status === 'completed' ? (
                        <>
                            <div className={`bg-gradient-to-br ${getScoreBg(scan.score)} rounded-2xl p-8 mb-6 border-2 ${scan.score < 20 ? 'border-emerald-200' : scan.score < 50 ? 'border-amber-200' : 'border-red-200'}`}>
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm font-medium text-gray-600 mb-2">Overall Plagiarism Score</p>
                                        <p className={`text-6xl font-bold ${getScoreColor(scan.score)}`}>
                                            {scan.score}%
                                        </p>
                                        <p className="text-sm text-gray-600 mt-2">
                                            {scan.score < 20 ? '✓ Excellent - Minimal plagiarism detected' :
                                                scan.score < 50 ? '⚠ Moderate - Review flagged sections' :
                                                    '⚠ High - Significant plagiarism detected'}
                                        </p>
                                    </div>
                                    {getScoreIcon(scan.score)}
                                </div>
                            </div>

                            {/* AI Detection Card */}
                            {scan.report?.ai_detection && (
                                <div className="bg-gradient-to-br from-violet-50 to-purple-50 rounded-2xl p-8 mb-6 border-2 border-violet-200">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-sm font-medium text-gray-600 mb-2">AI Content Probability</p>
                                            <p className="text-6xl font-bold text-violet-600">
                                                {scan.report.ai_detection.ai_probability}%
                                            </p>
                                            <p className="text-sm text-gray-600 mt-2">
                                                Label: <span className="font-bold text-violet-800">{scan.report.ai_detection.label}</span>
                                            </p>
                                        </div>
                                        <div className="text-right">
                                            <Sparkles className="h-16 w-16 text-violet-400" />
                                            <p className="text-xs text-gray-500 mt-2">Based on RoBERTa ML Model</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="mb-6">
                                <h2 className="text-xl font-semibold mb-4 text-gray-800">Summary</h2>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-gradient-to-br from-indigo-50 to-purple-50 p-6 rounded-xl border border-indigo-200">
                                        <p className="text-sm text-gray-600 mb-1">Total Chunks</p>
                                        <p className="text-3xl font-bold text-indigo-600">{scan.report?.total_chunks || 0}</p>
                                    </div>
                                    <div className="bg-gradient-to-br from-red-50 to-pink-50 p-6 rounded-xl border border-red-200">
                                        <p className="text-sm text-gray-600 mb-1">Matched Chunks</p>
                                        <p className="text-3xl font-bold text-red-600">{scan.report?.matched_chunks || 0}</p>
                                    </div>
                                </div>
                            </div>

                            {scan.report?.matches && scan.report.matches.length > 0 && (
                                <div>
                                    <h2 className="text-xl font-semibold mb-4 text-gray-800">Detected Matches</h2>
                                    <div className="space-y-4">
                                        {scan.report.matches.map((match, idx) => (
                                            <div key={idx} className="border-2 border-gray-200 rounded-xl p-6 hover:border-indigo-300 transition-all bg-white">
                                                <div className="flex justify-between items-start mb-4">
                                                    <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-semibold">
                                                        Chunk #{match.chunk_index + 1}
                                                    </span>
                                                    <span className="px-4 py-2 bg-gradient-to-r from-red-500 to-pink-500 text-white rounded-full text-sm font-bold shadow-lg">
                                                        {(match.best_match.score * 100).toFixed(1)}% match
                                                    </span>
                                                </div>
                                                <div className="mb-4">
                                                    <p className="text-xs font-medium text-gray-500 mb-2">YOUR TEXT:</p>
                                                    <p className="text-gray-800 bg-yellow-50 p-4 rounded-lg border-l-4 border-yellow-400 italic">
                                                        "{match.chunk_text}"
                                                    </p>
                                                </div>
                                                <div>
                                                    <p className="text-xs font-medium text-gray-500 mb-2">MATCHED WITH:</p>
                                                    <p className="text-gray-700 bg-red-50 p-4 rounded-lg border-l-4 border-red-400">
                                                        "{match.best_match.text}"
                                                    </p>
                                                    <p className="mt-3 text-xs text-gray-500 flex items-center gap-2">
                                                        <span className="px-2 py-1 bg-gray-100 rounded">Source Document ID: {match.best_match.source_doc_id}</span>
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </>
                    ) : scan.status === 'failed' ? (
                        <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-8 text-center">
                            <AlertTriangle className="h-16 w-16 text-red-600 mx-auto mb-4" />
                            <p className="text-red-700 font-bold text-xl mb-2">Scan Failed</p>
                            <p className="text-red-600">{scan.report?.error || 'Unknown error'}</p>
                        </div>
                    ) : (
                        <div className="text-center py-16">
                            <Clock className="h-16 w-16 text-indigo-600 animate-spin mx-auto mb-4" />
                            <p className="text-gray-600 text-lg font-medium">Scan in progress...</p>
                            <p className="text-gray-500 text-sm mt-2">Status: {scan.status}</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
