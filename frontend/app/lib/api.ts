/**
 * Central API configuration.
 *
 * The backend base URL is persisted in localStorage so users can point the
 * frontend at their own self-hosted backend instance without rebuilding.
 *
 * Usage:
 *   import { api } from '@/app/lib/api';
 *   axios.get(api('/api/v1/config'))
 */

const DEFAULT_API_BASE =
  (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_URL) ||
  'http://localhost:8000';

/** Return the backend base URL (no trailing slash). */
export function getApiBase(): string {
  if (typeof window === 'undefined') return DEFAULT_API_BASE;
  return localStorage.getItem('depfix_api_base') || DEFAULT_API_BASE;
}

/** Persist a new backend base URL. */
export function setApiBase(url: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('depfix_api_base', url.replace(/\/$/, ''));
  }
}

/** Build a full URL from a relative path. */
export function api(path: string): string {
  return `${getApiBase()}${path}`;
}
