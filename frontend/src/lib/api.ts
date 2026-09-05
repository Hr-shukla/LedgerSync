// Thin fetch wrapper around the FastAPI reconciliation backend
// (finance-controller/api/main.py). No mock data, no fabricated fallbacks --
// every function here either returns real backend data or throws ApiError.

import type {
  OverviewData,
  TransactionsResponse,
  TransactionAuditDetail,
  ExceptionsResponse,
  ExceptionResolution,
  AuditLogResponse,
} from '../types';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status?: number;
  isNetworkError: boolean;

  constructor(message: string, status?: number, isNetworkError = false) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.isNetworkError = isNetworkError;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    });
  } catch {
    throw new ApiError(
      `Could not reach the backend at ${API_BASE_URL}. Is \`uvicorn api.main:app --reload --port 8000\` running?`,
      undefined,
      true
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response body wasn't JSON -- fall back to statusText
    }
    throw new ApiError(detail, response.status);
  }

  return response.json() as Promise<T>;
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '');
  if (entries.length === 0) return '';
  return '?' + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join('&');
}

export function getOverview(): Promise<OverviewData> {
  return apiFetch<OverviewData>('/overview');
}

export interface TransactionFilters {
  status?: 'matched' | 'exception';
  source?: 'bank' | 'settlement' | 'ledger';
  search?: string;
  page?: number;
  page_size?: number;
  [key: string]: string | number | undefined;
}

export function getTransactions(filters: TransactionFilters = {}): Promise<TransactionsResponse> {
  return apiFetch<TransactionsResponse>(`/transactions${qs(filters)}`);
}

export function getTransactionAudit(id: string): Promise<TransactionAuditDetail> {
  return apiFetch<TransactionAuditDetail>(`/transactions/${encodeURIComponent(id)}/audit`);
}

export interface ExceptionFilters {
  reason_code?: string;
  min_age_days?: number;
  include_resolved?: boolean;
  page?: number;
  page_size?: number;
  [key: string]: string | number | boolean | undefined;
}

export function getExceptions(filters: ExceptionFilters = {}): Promise<ExceptionsResponse> {
  return apiFetch<ExceptionsResponse>(`/exceptions${qs(filters)}`);
}

export function resolveException(
  recordId: string,
  body: { note?: string; resolved_by?: string } = {}
): Promise<{ status: string; record_id: string; resolution: ExceptionResolution }> {
  return apiFetch(`/exceptions/${encodeURIComponent(recordId)}/resolve`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function unresolveException(recordId: string): Promise<{ status: string; record_id: string }> {
  return apiFetch(`/exceptions/${encodeURIComponent(recordId)}/unresolve`, { method: 'POST' });
}

export function getAuditLog(limit = 50): Promise<AuditLogResponse> {
  return apiFetch<AuditLogResponse>(`/audit-log${qs({ limit })}`);
}

// Re-runs the real pipeline against the existing dataset (~15s, live Tier 4
// call included if a key is configured) -- not a simulated progress bar.
export function runReconcile(): Promise<{ status: string; log_tail: string }> {
  return apiFetch('/reconcile', { method: 'POST' });
}
