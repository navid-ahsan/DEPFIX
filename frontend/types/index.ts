export interface AnalysisRequest {
  logs: string;
  repository?: string;
  branch?: string;
}

export interface AnalysisResult {
  id: string;
  status: 'pending' | 'completed' | 'failed';
  error: string;
  error_type?: string;
  solution: string;
  confidence: number;
  code_snippet?: string;
  timestamp: string;
  metadata?: {
    duration: number;
    model_used: string;
    source_documents: string[];
  };
}

export interface PullRequest {
  id: string;
  title: string;
  body: string;
  files: {
    filename: string;
    additions: number;
    deletions: number;
    changes: number;
  }[];
  analysis_id: string;
  status: 'draft' | 'submitted' | 'reviewed' | 'merged';
  url?: string;
}

export interface User {
  id: string;
  login: string;
  email?: string;
  avatar_url?: string;
  repositories?: string[];
}
