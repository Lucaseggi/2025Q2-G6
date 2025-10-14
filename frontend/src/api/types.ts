export interface ApiQuestionRequest {
  question: string;
}

export interface ApiSource {
  id: string;
  title: string;
  type: string;
  date?: string;
  score: number;
}

export interface ApiQuestionResponse {
  answer: string;
  question: string;
  sources: ApiSource[];
  documents_found: number;
  processing_time: number;
}

export interface ApiErrorResponse {
  error: string;
  details?: string;
  fallback_answer?: string;
  question?: string;
  sources?: ApiSource[];
}

export interface Message {
  role: "agent" | "user";
  content: string;
  timestamp: string;
  sources?: ApiSource[];
  processing_time?: number;
  documents_found?: number;
  isLoading?: boolean;
  error?: string;
}