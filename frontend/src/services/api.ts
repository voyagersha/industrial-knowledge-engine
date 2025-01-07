import axios from 'axios';

// Create an axios instance with default config
const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

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
  const response = await api.post('/validate-ontology', {
    ontology,
  });

  return response.data;
};

export const exportToNeo4j = async (graph: any) => {
  const response = await api.post('/export-neo4j', {
    graph,
  });

  return response.data;
};

// Add a test endpoint call
export const testAPI = async () => {
  const response = await api.get('/test');
  return response.data;
};