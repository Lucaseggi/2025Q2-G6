interface EnvironmentConfig {
  apiUrl: string;
  isDevelopment: boolean;
  isProduction: boolean;
  requestTimeout: number;
}

function detectEnvironment(): EnvironmentConfig {
  const hostname = window.location.hostname;
  const isDevelopment = hostname === 'localhost' || hostname === '127.0.0.1';
  const isProduction = !isDevelopment;

  let apiUrl: string;
  
  if (import.meta.env.VITE_API_URL) {
    apiUrl = import.meta.env.VITE_API_URL;
  } else if (isDevelopment) {
    apiUrl = 'http://localhost:8010';
  } else {
    apiUrl = `${window.location.protocol}//${hostname}:8010`;
  }

  return {
    apiUrl,
    isDevelopment,
    isProduction,
    requestTimeout: 30000,
  };
}

export const config = detectEnvironment();