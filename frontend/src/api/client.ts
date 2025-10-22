import { ApiQuestionRequest, ApiQuestionResponse, ApiErrorResponse } from './types';
import { config } from '../config/environment';

const API_BASE_URL = config.apiUrl;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: string,
    public fallbackAnswer?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class ApiClient {
  private baseUrl: string;
  private maxRetries: number = 2;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetchWithRetry(url: string, options: RequestInit, retries: number = this.maxRetries): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.requestTimeout);

    const fetchOptions: RequestInit = {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, fetchOptions);
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof Error && error.name === 'AbortError') {
        throw new ApiError(
          'La solicitud ha superado el tiempo límite. Intente nuevamente.',
          0,
          'Timeout error'
        );
      }

      if (retries > 0 && error instanceof TypeError) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        return this.fetchWithRetry(url, options, retries - 1);
      }

      throw error;
    }
  }

  async askQuestion(request: ApiQuestionRequest): Promise<ApiQuestionResponse> {
    try {
      const response = await this.fetchWithRetry(`${this.baseUrl}/question`, {
        method: 'POST',
        body: JSON.stringify(request),
      });

      const data = await response.json();

      if (!response.ok) {
        const errorData = data as ApiErrorResponse;
        let errorMessage = errorData.error || 'La solicitud falló';
        
        switch (response.status) {
          case 400:
            errorMessage = 'Solicitud inválida. Verifique que su pregunta sea válida.';
            break;
          case 500:
            errorMessage = 'Error interno del servidor. Intente nuevamente en unos momentos.';
            break;
          case 503:
            errorMessage = 'El servicio no está disponible temporalmente. Intente nuevamente más tarde.';
            break;
        }

        throw new ApiError(
          errorMessage,
          response.status,
          errorData.details,
          errorData.fallback_answer
        );
      }

      return data as ApiQuestionResponse;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        throw new ApiError(
          'No se puede conectar al servidor. Verifique su conexión a internet.',
          0,
          'Error de conexión de red'
        );
      }

      throw new ApiError(
        'Ocurrió un error inesperado. Intente nuevamente.',
        0,
        error instanceof Error ? error.message : String(error)
      );
    }
  }

  async healthCheck(): Promise<{ status: string; message: string }> {
    try {
      const response = await this.fetchWithRetry(`${this.baseUrl}/health`, {
        method: 'GET',
      });
      
      if (!response.ok) {
        throw new Error(`Verificación de salud falló: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      throw new ApiError(
        'La verificación de salud del servidor falló',
        0,
        error instanceof Error ? error.message : String(error)
      );
    }
  }
}

export const apiClient = new ApiClient();