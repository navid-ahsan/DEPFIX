import axios from 'axios';
import { AnalysisRequest, AnalysisResult, PullRequest } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
export const setAuthToken = (token: string) => {
  apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
};

// Analysis endpoints
export const analyzeLogsAPI = async (request: AnalysisRequest, token: string) => {
  setAuthToken(token);
  const response = await apiClient.post<AnalysisResult>('/api/analyze', request);
  return response.data;
};

export const getAnalysesAPI = async (token: string) => {
  setAuthToken(token);
  const response = await apiClient.get<AnalysisResult[]>('/api/analyses');
  return response.data;
};

export const getAnalysisAPI = async (id: string, token: string) => {
  setAuthToken(token);
  const response = await apiClient.get<AnalysisResult>(`/api/analyses/${id}`);
  return response.data;
};

// PR endpoints
export const createPullRequestAPI = async (
  analysisId: string,
  data: Partial<PullRequest>,
  token: string
) => {
  setAuthToken(token);
  const response = await apiClient.post<PullRequest>(
    `/api/pull-requests`,
    { ...data, analysis_id: analysisId }
  );
  return response.data;
};

export const getPullRequestsAPI = async (token: string) => {
  setAuthToken(token);
  const response = await apiClient.get<PullRequest[]>('/api/pull-requests');
  return response.data;
};

// Error handling
export const handleAPIError = (error: any) => {
  if (error.response) {
    return {
      message: error.response.data?.detail || 'An error occurred',
      status: error.response.status,
    };
  }
  return {
    message: error.message || 'Network error',
    status: 0,
  };
};
