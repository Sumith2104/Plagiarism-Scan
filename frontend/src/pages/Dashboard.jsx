import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { documentsAPI, scansAPI } from '../api';
import { Upload, FileText, LogOut, Search, CheckCircle, Clock, AlertCircle, Sparkles, TrendingUp } from 'lucide-react';

export default function Dashboard() {
    const [documents, setDocuments] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const navigate = useNavigate();

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
                navigate('/');
            }
        }
    };

    const handleFileChange = (e) => {
        setSelectedFile(e.target.files[0]);
    };

    const handleUpload = async () => {
        if (!selectedFile) return;

        setUploading(true);
        try {
            await documentsAPI.upload(selectedFile);
            setSelectedFile(null);
            loadDocuments();
            alert('Document uploaded successfully!');
        } catch (err) {
            alert('Upload failed: ' + (err.response?.data?.detail || 'Unknown error'));
        } finally {
            setUploading(false);
        }
    };

    const handleScan = async (documentId) => {
        try {
            const response = await scansAPI.initiate(documentId);
            alert(`Scan initiated! Scan ID: ${response.data.scan_id}`);
            navigate(`/report/${response.data.scan_id}`);
        } catch (err) {
            alert('Scan failed: ' + (err.response?.data?.detail || 'Unknown error'));
        }
    };

    const handleDelete = async (documentId) => {
        if (!window.confirm('Are you sure you want to delete this document?')) return;

        try {
            await documentsAPI.delete(documentId);
            setDocuments(documents.filter(d => d.id !== documentId));
            alert('Document deleted successfully');
        } catch (err) {
            alert('Failed to delete document: ' + (err.response?.data?.detail || 'Unknown error'));
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
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

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
            {/* Modern Navbar */}
            <nav className="bg-white/80 backdrop-blur-lg shadow-sm border-b border-gray-200/50 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                                <Sparkles className="h-6 w-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                                    PlagiaScan
                                </h1>
                                <p className="text-xs text-gray-500">Dashboard</p>
                            </div>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-all"
                        >
                            <LogOut className="h-5 w-5" />
                            <span className="font-medium">Logout</span>
                        </button>
                    </div>
                </div>
            </nav>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl p-6 text-white shadow-xl transform hover:scale-105 transition-transform">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-indigo-100 text-sm font-medium">Total Documents</p>
                                <p className="text-4xl font-bold mt-2">{documents.length}</p>
                            </div>
                            <FileText className="h-12 w-12 text-white/30" />
                        </div>
                    </div>

                    <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200 transform hover:scale-105 transition-transform">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-gray-600 text-sm font-medium">Indexed</p>
                                <p className="text-4xl font-bold mt-2 text-emerald-600">
                                    {documents.filter(d => d.status === 'indexed').length}
                                </p>
                            </div>
                            <CheckCircle className="h-12 w-12 text-emerald-200" />
                        </div>
                    </div>

                    <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200 transform hover:scale-105 transition-transform">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-gray-600 text-sm font-medium">Processing</p>
                                <p className="text-4xl font-bold mt-2 text-amber-600">
                                    {documents.filter(d => d.status === 'processing').length}
                                </p>
                            </div>
                            <TrendingUp className="h-12 w-12 text-amber-200" />
                        </div>
                    </div>
                </div>

                {/* Upload Card */}
                <div className="bg-white rounded-2xl shadow-xl p-8 mb-8 border border-gray-200">
                    <h2 className="text-2xl font-bold mb-6 flex items-center gap-3 text-gray-800">
                        <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
                            <Upload className="h-5 w-5 text-white" />
                        </div>
                        Upload Document
                    </h2>
                    <div className="flex gap-4 items-end">
                        <div className="flex-1">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Select File (PDF, DOCX, TXT, HTML)
                            </label>
                            <input
                                type="file"
                                onChange={handleFileChange}
                                accept=".pdf,.docx,.txt,.html"
                                className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                            />
                        </div>
                        <button
                            onClick={handleUpload}
                            disabled={!selectedFile || uploading}
                            className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-xl font-semibold disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all"
                        >
                            {uploading ? 'Uploading...' : 'Upload'}
                        </button>
                    </div>
                </div>

                {/* Documents List */}
                <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200">
                    <h2 className="text-2xl font-bold mb-6 flex items-center gap-3 text-gray-800">
                        <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
                            <FileText className="h-5 w-5 text-white" />
                        </div>
                        Your Documents
                    </h2>
                    <div className="space-y-4">
                        {documents.length === 0 ? (
                            <div className="text-center py-16">
                                <FileText className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                                <p className="text-gray-500 text-lg">No documents uploaded yet</p>
                                <p className="text-gray-400 text-sm mt-2">Upload your first document to get started</p>
                            </div>
                        ) : (
                            documents.map((doc) => (
                                <div
                                    key={doc.id}
                                    className="flex items-center justify-between p-5 border-2 border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-md transition-all group"
                                >
                                    <div className="flex items-center gap-4">
                                        {getStatusIcon(doc.status)}
                                        <div>
                                            <p className="font-semibold text-gray-800 group-hover:text-indigo-600 transition-colors">
                                                {doc.filename}
                                            </p>
                                            <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium border mt-1 ${getStatusBadge(doc.status)}`}>
                                                {doc.status}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={() => handleScan(doc.id)}
                                            disabled={doc.status !== 'indexed'}
                                            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg transition-all text-sm"
                                        >
                                            <Search className="h-4 w-4" />
                                            Scan
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
        </div>
    );
}
