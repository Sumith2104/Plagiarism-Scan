import axios from 'axios';

const isDevServer = typeof window !== 'undefined' && (
    Boolean(window.location.port && (window.location.port.startsWith('517') || window.location.port === '3000'))
);
const protocol = typeof window !== 'undefined' ? window.location.protocol : 'http:';
const API_BASE_URL = import.meta.env.VITE_API_URL || (isDevServer ? `${protocol}//${window.location.hostname}:8000/api/v1` : '/api/v1');

const api = axios.create({
    baseURL: API_BASE_URL,
});

// Add auth token to requests
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const authAPI = {
    login: (email, password) => {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);
        return api.post('/auth/login', formData);
    },
    register: (email, password, fullName) =>
        api.post('/auth/register', null, { params: { email, password, full_name: fullName } }),
    getMe: () => api.get('/auth/me'),
};

export const documentsAPI = {
    upload: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/documents/', formData);
    },
    list: () => api.get('/documents/'),
    get: (id) => api.get(`/documents/${id}`),
    delete: (id) => api.delete(`/documents/${id}`),
};

export const scansAPI = {
    initiate: (documentId, scanMode = 'standard') =>
        api.post('/scans/', { document_id: documentId, scan_mode: scanMode }),
    get: (id) => api.get(`/scans/${id}`),
    getTrace: (id) => api.get(`/scans/${id}/trace`),
    verify: (id) => api.get(`/scans/${id}/verify`),
    collusionMatrix: (documentIds) => api.post('/scans/collusion-matrix', { document_ids: documentIds }),
};

export default api;
