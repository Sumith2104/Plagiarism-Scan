import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { documentsAPI, scansAPI } from '../api';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import {
    Upload,
    FileText,
    LogOut,
    Search,
    CheckCircle,
    Clock,
    AlertCircle,
    Sparkles,
    TrendingUp,
    Users,
    Grid,
    AlertTriangle,
    X,
    Check,
    Layers,
    ShieldAlert
} from 'lucide-react';

export default function Dashboard() {
    const [documents, setDocuments] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState('');
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [showCollusionModal, setShowCollusionModal] = useState(false);
    const [collusionData, setCollusionData] = useState(null);
    const [loadingCollusion, setLoadingCollusion] = useState(false);
    const [selectedDocIdsForCollusion, setSelectedDocIdsForCollusion] = useState([]);
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const notify = useNotification();

    useEffect(() => {
        loadDocuments();
        // Poll every 3 seconds to keep status updated
        const interval = setInterval(loadDocuments, 3000);
        return () => clearInterval(interval);
    }, []);

    const loadDocuments = async () => {
        try {
            const response = await documentsAPI.list();
            setDocuments(response.data);
        } catch (err) {
            if (err.response?.status === 401) {
                logout();
                navigate('/');
            }
        }
    };

    const handleFileChange = (e) => {
        const files = Array.from(e.target.files);
        setSelectedFiles(files);
    };

    const handleUpload = async () => {
        if (!selectedFiles.length) return;

        setUploading(true);
        notify.info('Upload Started', `Transferring ${selectedFiles.length} file(s) to processing engine...`);
        let successCount = 0;
        let failCount = 0;

        for (let i = 0; i < selectedFiles.length; i++) {
            const file = selectedFiles[i];
            setUploadProgress(`Uploading ${i + 1} of ${selectedFiles.length}: ${file.name}...`);
            try {
                await documentsAPI.upload(file);
                successCount++;
            } catch (err) {
                console.error(`Failed to upload ${file.name}:`, err);
                failCount++;
            }
        }

        setSelectedFiles([]);
        setUploadProgress('');
        setUploading(false);
        loadDocuments();

        if (failCount === 0) {
            notify.success('Upload Complete', `Successfully uploaded and indexed ${successCount} document(s)!`);
        } else {
            notify.warning('Upload Partially Succeeded', `Uploaded ${successCount} document(s). ${failCount} failed.`);
        }
    };

    const handleScan = async (documentId, scanMode = 'standard') => {
        try {
            notify.info('Scan Initiated', 'Running dual-engine vector search & web distillation...');
            const response = await scansAPI.initiate(documentId, scanMode);
            navigate(`/report/${response.data.scan_id}`);
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || 'Unknown error occurred';
            notify.error('Scan Failed', errorMsg);
        }
    };

    const handleDelete = async (documentId) => {
        if (!window.confirm('Are you sure you want to delete this document?')) return;

        try {
            await documentsAPI.delete(documentId);
            setDocuments(documents.filter(d => d.id !== documentId));
            notify.success('Document Deleted', 'Document and vector embeddings removed successfully.');
        } catch (err) {
            notify.error('Delete Failed', err.response?.data?.detail || 'Unknown error');
        }
    };

    const handleOpenCollusionModal = async () => {
        setShowCollusionModal(true);
        const indexedDocs = documents.filter(d => d.status === 'indexed');
        const docIds = indexedDocs.map(d => d.id);
        setSelectedDocIdsForCollusion(docIds);
        fetchCollusionMatrix(docIds);
    };

    const fetchCollusionMatrix = async (docIds) => {
        setLoadingCollusion(true);
        try {
            const res = await scansAPI.collusionMatrix(docIds && docIds.length >= 2 ? docIds : undefined);
            setCollusionData(res.data);
            notify.success('Collusion Matrix Ready', 'Pairwise document similarity analyzed.');
        } catch (err) {
            console.error('Failed to load collusion matrix:', err);
            notify.warning('Collusion Matrix Info', err.response?.data?.detail || 'Collusion matrix requires at least 2 indexed documents.');
        } finally {
            setLoadingCollusion(false);
        }
    };

    const toggleDocForCollusion = (id) => {
        let updated;
        if (selectedDocIdsForCollusion.includes(id)) {
            updated = selectedDocIdsForCollusion.filter(x => x !== id);
        } else {
            updated = [...selectedDocIdsForCollusion, id];
        }
        setSelectedDocIdsForCollusion(updated);
    };

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'indexed':
                return <CheckCircle className="h-5 w-5 text-emerald-500" />;
            case 'processing':
                return <Clock className="h-5 w-5 text-amber-500 animate-spin" />;
            case 'failed':
                return <AlertCircle className="h-5 w-5 text-red-500" />;
            default:
                return <Clock className="h-5 w-5 text-gray-500" />;
        }
    };

    const getStatusBadge = (status) => {
        const styles = {
            indexed: 'bg-emerald-100 text-emerald-700 border-emerald-200',
            processing: 'bg-amber-100 text-amber-700 border-amber-200',
            failed: 'bg-red-100 text-red-700 border-red-200',
            pending: 'bg-gray-100 text-gray-700 border-gray-200'
        };
        return styles[status] || styles.pending;
    };

    const indexedDocsCount = documents.filter(d => d.status === 'indexed').length;

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
            {/* Modern Navbar */}
            <nav className="bg-white/85 backdrop-blur-xl shadow-sm border-b border-gray-200/60 sticky top-0 z-40">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5">
                    <div className="flex justify-between items-center flex-wrap gap-4">
                        <div className="flex items-center gap-3.5">
                            <div className="w-11 h-11 rounded-2xl bg-white p-1 shadow-md border border-gray-200/80 flex items-center justify-center overflow-hidden ring-2 ring-indigo-500/20">
                                <img
                                    src="/logo-icon.png"
                                    alt="PlagiaScan Logo"
                                    className="w-full h-full object-contain"
                                    onError={(e) => { e.target.src = '/logo.png'; }}
                                />
                            </div>
                            <div>
                                <h1 className="text-2xl font-extrabold bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-700 bg-clip-text text-transparent">
                                    PlagiaScan
                                </h1>
                                <p className="text-[11px] text-gray-500 font-medium">Academic &amp; Forensic Integrity Platform</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            {/* Peer-to-Peer Collusion Matrix Trigger */}
                            <button
                                onClick={handleOpenCollusionModal}
                                disabled={indexedDocsCount < 2}
                                className="flex items-center gap-2 px-3.5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl text-xs font-bold shadow-sm hover:shadow transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                title={indexedDocsCount < 2 ? 'Upload at least 2 indexed documents to run collusion matrix' : 'Compare all documents pairwise for student collusion'}
                            >
                                <Users className="h-4 w-4" />
                                <span className="hidden sm:inline">Peer Collusion Matrix</span>
                                <span className="bg-white/20 px-1.5 py-0.5 rounded text-[10px]">NEW</span>
                            </button>

                            {/* Authenticated User Profile Badge */}
                            {user && (
                                <div className="flex items-center gap-2.5 px-3 py-1.5 bg-slate-100/80 border border-slate-200/80 rounded-xl shadow-xs">
                                    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 text-white font-bold text-xs flex items-center justify-center shadow-xs">
                                        {(user.full_name || user.email || 'U')[0].toUpperCase()}
                                    </div>
                                    <div className="text-left hidden md:block">
                                        <p className="text-xs font-bold text-slate-800 leading-tight truncate max-w-[130px]">
                                            {user.full_name || user.email.split('@')[0]}
                                        </p>
                                        <p className="text-[10px] text-slate-500 truncate max-w-[130px]">
                                            {user.email}
                                        </p>
                                    </div>
                                    <span className="text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 border border-indigo-200/60 hidden sm:inline-block">
                                        {user.role || 'user'}
                                    </span>
                                </div>
                            )}

                            <button
                                onClick={handleLogout}
                                className="flex items-center gap-1.5 px-3 py-2 text-rose-600 hover:text-rose-700 hover:bg-rose-50 border border-rose-200/60 rounded-xl transition-all text-xs font-bold shadow-xs"
                                title="Sign out"
                            >
                                <LogOut className="h-3.5 w-3.5" />
                                <span className="hidden sm:inline">Logout</span>
                            </button>
                        </div>
                    </div>
                </div>
            </nav>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl p-6 text-white shadow-xl transform hover:scale-[1.02] transition-transform">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-indigo-100 text-sm font-medium">Total Documents</p>
                                <p className="text-4xl font-bold mt-2">{documents.length}</p>
                            </div>
                            <FileText className="h-12 w-12 text-white/30" />
                        </div>
                    </div>

                    <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200 transform hover:scale-[1.02] transition-transform">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-gray-600 text-sm font-medium">Indexed for Fast Audit</p>
                                <p className="text-4xl font-bold mt-2 text-emerald-600">
                                    {indexedDocsCount}
                                </p>
                            </div>
                            <CheckCircle className="h-12 w-12 text-emerald-200" />
                        </div>
                    </div>

                    <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200 transform hover:scale-[1.02] transition-transform">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-gray-600 text-sm font-medium">Processing / Indexing</p>
                                <p className="text-4xl font-bold mt-2 text-amber-600">
                                    {documents.filter(d => d.status === 'processing').length}
                                </p>
                            </div>
                            <TrendingUp className="h-12 w-12 text-amber-200" />
                        </div>
                    </div>
                </div>

                {/* Upload Card: Multi-File Batch Support */}
                <div className="bg-white rounded-2xl shadow-xl p-8 mb-8 border border-gray-200">
                    <div className="flex items-center justify-between flex-wrap gap-2 mb-6">
                        <h2 className="text-2xl font-bold flex items-center gap-3 text-gray-800">
                            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
                                <Upload className="h-5 w-5 text-white" />
                            </div>
                            Multi-File Batch Document Upload
                        </h2>
                        <span className="text-xs font-semibold px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full border border-indigo-200">
                            Batch Queue Enabled
                        </span>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-4 items-stretch sm:items-end">
                        <div className="flex-1">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Select One or Multiple Files (PDF, DOCX, TXT, HTML)
                            </label>
                            <input
                                type="file"
                                onChange={handleFileChange}
                                accept=".pdf,.docx,.txt,.html"
                                multiple
                                className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 text-sm"
                            />
                            {selectedFiles.length > 0 && (
                                <p className="text-xs text-indigo-600 font-semibold mt-2">
                                    ✓ {selectedFiles.length} file(s) selected: {selectedFiles.map(f => f.name).join(', ')}
                                </p>
                            )}
                        </div>
                        <button
                            onClick={handleUpload}
                            disabled={!selectedFiles.length || uploading}
                            className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-xl font-semibold disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all text-sm shrink-0"
                        >
                            {uploading ? (uploadProgress || 'Uploading...') : selectedFiles.length > 1 ? `Upload ${selectedFiles.length} Files` : 'Upload'}
                        </button>
                    </div>
                </div>

                {/* Documents List */}
                <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200">
                    <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
                        <h2 className="text-2xl font-bold flex items-center gap-3 text-gray-800">
                            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
                                <FileText className="h-5 w-5 text-white" />
                            </div>
                            Your Documents Library
                        </h2>

                        {indexedDocsCount >= 2 && (
                            <button
                                onClick={handleOpenCollusionModal}
                                className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg border border-indigo-200 transition-all"
                            >
                                <Grid className="h-3.5 w-3.5" />
                                <span>Check Peer Collusion Matrix ({indexedDocsCount} docs)</span>
                            </button>
                        )}
                    </div>

                    <div className="space-y-4">
                        {documents.length === 0 ? (
                            <div className="text-center py-16">
                                <FileText className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                                <p className="text-gray-500 text-lg">No documents uploaded yet</p>
                                <p className="text-gray-400 text-sm mt-2">Upload your first document or batch of papers to get started</p>
                            </div>
                        ) : (
                            documents.map((doc) => (
                                <div
                                    key={doc.id}
                                    className="flex items-center justify-between p-5 border-2 border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-md transition-all group flex-wrap sm:flex-nowrap gap-4"
                                >
                                    <div className="flex items-center gap-4">
                                        {getStatusIcon(doc.status)}
                                        <div>
                                            <p className="font-semibold text-gray-800 group-hover:text-indigo-600 transition-colors">
                                                {doc.filename}
                                            </p>
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusBadge(doc.status)}`}>
                                                    {doc.status}
                                                </span>
                                                <span className="text-xs text-gray-400">Doc ID: #{doc.id}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => handleScan(doc.id)}
                                            disabled={doc.status !== 'indexed'}
                                            className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow transition-all text-xs"
                                            title="Run Plagiarism & AI Integrity Scan"
                                        >
                                            <Search className="h-3.5 w-3.5" />
                                            Scan Document
                                        </button>
                                        <button
                                            onClick={() => handleDelete(doc.id)}
                                            className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-all"
                                            title="Delete Document"
                                        >
                                            <LogOut className="h-5 w-5 rotate-180" />
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* Peer-to-Peer Collusion Matrix Modal */}
            {showCollusionModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-3xl shadow-2xl border border-gray-200 max-w-5xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                        {/* Header */}
                        <div className="p-6 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
                            <div className="flex items-center gap-3">
                                <div className="p-2.5 bg-purple-500/20 text-purple-400 rounded-xl border border-purple-500/30">
                                    <Users className="h-5 w-5" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-bold text-white">Peer-to-Peer Collusion Matrix</h3>
                                    <p className="text-xs text-slate-400">
                                        Pairwise semantic &amp; n-gram cross-matching across student submissions.
                                    </p>
                                </div>
                            </div>

                            <button
                                onClick={() => setShowCollusionModal(false)}
                                className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition-all"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        {/* Body */}
                        <div className="p-6 overflow-y-auto flex-1 space-y-6 bg-slate-50">
                            {/* Document Selector Pills */}
                            <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm">
                                <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                                    <span className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                                        Select Documents to Cross-Compare ({selectedDocIdsForCollusion.length} selected)
                                    </span>
                                    <button
                                        onClick={() => fetchCollusionMatrix(selectedDocIdsForCollusion)}
                                        disabled={selectedDocIdsForCollusion.length < 2 || loadingCollusion}
                                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold transition-all disabled:opacity-50"
                                    >
                                        {loadingCollusion ? 'Recalculating Matrix...' : 'Update Matrix'}
                                    </button>
                                </div>

                                <div className="flex flex-wrap gap-2">
                                    {documents.filter(d => d.status === 'indexed').map(doc => {
                                        const isChecked = selectedDocIdsForCollusion.includes(doc.id);
                                        return (
                                            <button
                                                key={doc.id}
                                                onClick={() => toggleDocForCollusion(doc.id)}
                                                className={`px-3 py-1 rounded-xl text-xs font-semibold border transition-all flex items-center gap-1.5 ${
                                                    isChecked
                                                        ? 'bg-indigo-50 border-indigo-300 text-indigo-800 shadow-sm'
                                                        : 'bg-gray-100 border-gray-200 text-gray-500 hover:bg-gray-200'
                                                }`}
                                            >
                                                <span className={`w-2 h-2 rounded-full ${isChecked ? 'bg-indigo-600' : 'bg-gray-400'}`}></span>
                                                <span className="truncate max-w-[150px]">{doc.filename}</span>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            {loadingCollusion ? (
                                <div className="py-20 text-center">
                                    <Clock className="h-10 w-10 text-indigo-600 animate-spin mx-auto mb-3" />
                                    <p className="text-sm font-semibold text-gray-700">Computing pairwise semantic &amp; vector cross-matrix...</p>
                                </div>
                            ) : collusionData ? (
                                <>
                                    {/* Collusion Alert Warnings if any flagged pairs */}
                                    {collusionData.flagged_pairs && collusionData.flagged_pairs.length > 0 ? (
                                        <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-5 shadow-sm space-y-3">
                                            <div className="flex items-center gap-2 text-red-900 font-bold text-sm">
                                                <ShieldAlert className="h-5 w-5 text-red-600" />
                                                <span>Collusion Warning: {collusionData.flagged_pairs.length} Document Pair(s) Flagged</span>
                                            </div>
                                            <p className="text-xs text-red-700">
                                                High cosine similarity detected between independent student submissions exceeding the 40% institutional collusion threshold.
                                            </p>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                                                {collusionData.flagged_pairs.map((fp, i) => (
                                                    <div key={i} className="bg-white p-3.5 rounded-xl border border-red-200 shadow-sm flex items-center justify-between gap-2">
                                                        <div>
                                                            <p className="text-xs font-bold text-gray-900">
                                                                {fp.doc1_name} <span className="text-red-600">↔</span> {fp.doc2_name}
                                                            </p>
                                                            <p className="text-[11px] text-gray-500 mt-0.5">
                                                                Doc #{fp.doc1_id} vs Doc #{fp.doc2_id}
                                                            </p>
                                                        </div>
                                                        <span className="px-2.5 py-1 bg-red-100 text-red-800 text-xs font-black rounded-lg border border-red-200">
                                                            {fp.similarity}% Overlap
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex items-center gap-3 text-emerald-900">
                                            <CheckCircle className="h-5 w-5 text-emerald-600 shrink-0" />
                                            <div>
                                                <p className="text-xs font-bold">Zero High-Risk Peer Collusion Caught</p>
                                                <p className="text-xs text-emerald-700 mt-0.5">
                                                    All evaluated document pairs showed independent writing styles below the 40% similarity threshold.
                                                </p>
                                            </div>
                                        </div>
                                    )}

                                    {/* Pairwise Heatmap Grid */}
                                    <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm overflow-x-auto">
                                        <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-1.5">
                                            <Grid className="h-4 w-4 text-indigo-600" />
                                            Pairwise Similarity Heatmap (%)
                                        </h4>

                                        <table className="w-full text-xs text-center border-collapse">
                                            <thead>
                                                <tr>
                                                    <th className="p-2 text-left font-bold text-gray-500 border-b border-gray-200 max-w-[120px]">
                                                        Document
                                                    </th>
                                                    {collusionData.documents.map((d) => (
                                                        <th key={d.id} className="p-2 font-bold text-gray-700 border-b border-gray-200 max-w-[100px] truncate" title={d.filename}>
                                                            {d.filename.length > 12 ? d.filename.slice(0, 12) + '...' : d.filename}
                                                        </th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {collusionData.matrix.map((row, i) => (
                                                    <tr key={i} className="hover:bg-slate-50 transition-colors">
                                                        <td className="p-2 text-left font-bold text-gray-900 border-b border-gray-100 max-w-[120px] truncate" title={collusionData.documents[i]?.filename}>
                                                            {collusionData.documents[i]?.filename}
                                                        </td>
                                                        {row.map((score, j) => {
                                                            const isSelf = i === j;
                                                            let cellStyle = 'bg-emerald-50 text-emerald-800';
                                                            if (isSelf) {
                                                                cellStyle = 'bg-gray-100 text-gray-400 font-normal';
                                                            } else if (score >= 50) {
                                                                cellStyle = 'bg-red-500 text-white font-black';
                                                            } else if (score >= 40) {
                                                                cellStyle = 'bg-amber-400 text-amber-950 font-bold';
                                                            } else if (score >= 20) {
                                                                cellStyle = 'bg-amber-100 text-amber-900 font-semibold';
                                                            }

                                                            return (
                                                                <td
                                                                    key={j}
                                                                    className={`p-2 border border-gray-200 rounded-lg text-xs transition-all ${cellStyle}`}
                                                                    title={`${collusionData.documents[i]?.filename} vs ${collusionData.documents[j]?.filename}: ${score}%`}
                                                                >
                                                                    {isSelf ? '—' : `${score}%`}
                                                                </td>
                                                            );
                                                        })}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>

                                        <div className="mt-4 flex items-center justify-between text-[11px] text-gray-500 flex-wrap gap-2">
                                            <div className="flex items-center gap-3">
                                                <span className="flex items-center gap-1">
                                                    <span className="w-2.5 h-2.5 bg-emerald-100 rounded"></span> &lt;20% Independent
                                                </span>
                                                <span className="flex items-center gap-1">
                                                    <span className="w-2.5 h-2.5 bg-amber-100 rounded"></span> 20-40% Moderate
                                                </span>
                                                <span className="flex items-center gap-1">
                                                    <span className="w-2.5 h-2.5 bg-red-500 rounded"></span> &gt;50% Critical Collusion
                                                </span>
                                            </div>
                                            <span>Values denote pairwise token &amp; vector cosine overlap</span>
                                        </div>
                                    </div>
                                </>
                            ) : null}
                        </div>

                        {/* Footer */}
                        <div className="p-4 bg-white border-t border-gray-200 flex items-center justify-end">
                            <button
                                onClick={() => setShowCollusionModal(false)}
                                className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold transition-all"
                            >
                                Close Matrix
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
