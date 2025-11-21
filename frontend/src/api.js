import axios from 'axios';

const API_BASE_URL = `http://${window.location.hostname}:8000/api/v1`;

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
    initiate: (documentId) => api.post('/scans/', { document_id: documentId }),
    get: (id) => api.get(`/scans/${id}`),
};

export default api;
