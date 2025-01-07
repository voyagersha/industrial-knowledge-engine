import axios from 'axios';

// Create an axios instance with default config
const api = axios.create({
    baseURL: '/api',  // This will be properly proxied by Vite
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 10000,
    withCredentials: true
});

// Add response interceptor for better error handling
api.interceptors.response.use(
    response => response,
    error => {
        console.error('API Error:', error.response?.data || error.message);
        if (error.response?.status === 404) {
            console.error('Endpoint not found. Please check the URL and try again.');
        }
        throw error;
    }
);

// API endpoints
export const testAPI = async () => {
    try {
        const response = await api.get('/test');
        return response.data;
    } catch (error) {
        console.error('Test API call failed:', error);
        throw error;
    }
};

export const uploadFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });

    return response.data;
};

export const validateOntology = async (ontology: any) => {
    const response = await api.post('/validate-ontology', { ontology });
    return response.data;
};

export const exportToNeo4j = async (graph: any) => {
    const response = await api.post('/export-neo4j', {
        graph,
    });

    return response.data;
};