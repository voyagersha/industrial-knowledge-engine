import axios from 'axios';

// Create an axios instance with default config
const api = axios.create({
    baseURL: '/api',  // This will be properly proxied by Vite
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000, // Increased timeout to 30 seconds
    withCredentials: true
});

// Add response interceptor for better error handling
api.interceptors.response.use(
    response => response,
    error => {
        console.error('API Error:', error.response?.data || error.message);
        console.error('Full error details:', error);
        if (error.response?.status === 404) {
            console.error('Endpoint not found. Please check the URL and try again.');
        } else if (error.response?.status === 405) {
            console.error('Method not allowed. Please check the request method.');
        }
        throw error;
    }
);

export const uploadFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await axios.post('/api/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            timeout: 30000, // Increased timeout for file upload
        });
        return response.data;
    } catch (error) {
        console.error('Upload failed:', error);
        throw error;
    }
};

export const validateOntology = async (ontology: any) => {
    const response = await api.post('/validate-ontology', { ontology });
    return response.data;
};

export const chat = async (query: string) => {
    const response = await api.post('/chat', { query });
    return response.data;
};