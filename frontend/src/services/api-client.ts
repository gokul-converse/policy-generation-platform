/**
 * Centralized Axios instance for all API communication.
 *
 * Configuration is driven by environment variables:
 *   NEXT_PUBLIC_API_BASE_URL – base URL of the backend API (e.g. http://localhost:8000)
 *
 * Usage:
 *   import apiClient from '@/services/api-client';
 *   const data = await apiClient.get('/some-endpoint');
 *
 * Interceptors can be added here when authentication or global error
 * handling is required in the future.
 */

import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

/** 15-second default timeout – adjust per environment as needed. */
const DEFAULT_TIMEOUT_MS = 15_000;

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: DEFAULT_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// ---------------------------------------------------------------------------
// Request interceptor – extend here to attach auth tokens, trace IDs, etc.
// ---------------------------------------------------------------------------
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => config,
  (error: AxiosError) => Promise.reject(error),
);

// ---------------------------------------------------------------------------
// Response interceptor – extend here for global error handling / token refresh.
// ---------------------------------------------------------------------------
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => Promise.reject(error),
);

export default apiClient;
