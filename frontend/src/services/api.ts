import axios from 'axios';

const API_BASE_URL = '/api';

export const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const validateOntology = async (ontology: any) => {
  const response = await axios.post(`${API_BASE_URL}/validate-ontology`, {
    ontology,
  });

  return response.data;
};

export const exportToNeo4j = async (graph: any) => {
  const response = await axios.post(`${API_BASE_URL}/export-neo4j`, {
    graph,
  });

  return response.data;
};