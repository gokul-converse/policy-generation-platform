/**
 * Shared TypeScript types and interfaces.
 *
 * Place domain-wide types here as the application grows.
 * Prefer co-locating feature-specific types next to the feature they belong to.
 *
 * Example:
 *   export interface User {
 *     id: string;
 *     email: string;
 *   }
 */

// ---------------------------------------------------------------------------
// Common API response envelope – update to match your actual backend shape.
// ---------------------------------------------------------------------------

/** Generic success wrapper returned by the backend. */
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

/** Generic paginated list response. */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

// ---------------------------------------------------------------------------
// Re-export domain types
// ---------------------------------------------------------------------------
export * from './policy';
