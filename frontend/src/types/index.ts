// Types mirror the FastAPI backend's actual JSON shapes exactly
// (finance-controller/api/main.py) -- not a design aspiration, the real
// contract. Field names match the backend 1:1 so there is no translation
// layer to keep in sync by hand.

// ============================================================================
// Raw record shapes (mirror pipeline/loader.py / the source CSVs)
// ============================================================================

export interface BankRecord {
  bank_txn_id: string;
  date: string;
  amount: number;
  utr: string;
  narration: string;
}

export interface SettlementRecord {
  settlement_id: string;
  payment_id: string;
  utr: string;
  settlement_date: string;
  gross_amount: number;
  fee: number;
  fee_gst: number;
  tds: number;
  net_amount: number;
  chargeback: boolean;
}

export interface LedgerRecord {
  ledger_id: string;
  invoice_date: string;
  customer: string;
  invoice_amount: number;
  status: string;
}

// ============================================================================
// GET /overview
// ============================================================================

export interface PerSourceStats {
  total_records: number;
  matched_records: number;
  match_rate_pct: number;
}

export interface OverviewData {
  match_rate_pct: number;
  reconciled_value_rupees: number;
  total_value_rupees: number;
  reconciled_value_pct: number;
  value_at_risk_rupees: number;
  open_exceptions_count: number;
  precision_pct: number;
  recall_pct: number;
  false_match_rate_pct: number;
  per_source: {
    bank: PerSourceStats;
    settlement: PerSourceStats;
    ledger: PerSourceStats;
  };
  tier_breakdown: Record<string, number>;
  ai_available: boolean;
  ai_provider: string | null;
}

// ============================================================================
// GET /transactions, GET /transactions/{id}/audit
// ============================================================================

export type TransactionStatus = 'matched' | 'exception';

export interface TransactionRow {
  id: string;
  status: TransactionStatus;
  tiers: string[];
  confidence: number;
  bank: BankRecord[] | null;
  settlement: SettlementRecord[] | null;
  ledger: LedgerRecord[] | null;
  record_ids: {
    bank: string[];
    settlement: string[];
    ledger: string[];
  };
}

export interface FilterCounts {
  all: number;
  matched: number;
  exception: number;
}

export interface TransactionsResponse {
  total: number;
  page: number;
  page_size: number;
  filter_counts: FilterCounts;
  items: TransactionRow[];
}

export interface DecisionStep {
  record_id: string;
  tier: string;
  outcome: 'matched' | 'unresolved';
  matched_against: string[];
  confidence: number;
  reasoning: string;
  exception_reason: string;
}

export interface TransactionAuditDetail {
  transaction_id: string;
  status: TransactionStatus;
  comparison: {
    bank: BankRecord[];
    settlement: SettlementRecord[];
    ledger: LedgerRecord[];
  };
  decision_tree: DecisionStep[];
  reasoning_summary: string;
}

// ============================================================================
// GET /exceptions, POST /exceptions/{id}/resolve
// ============================================================================

export interface ExceptionSummaryBucket {
  reason_code: string;
  count: number;
  value_at_risk_rupees: number;
}

export interface ExceptionResolution {
  record_id: string;
  resolved: true;
  resolved_at: string;
  resolved_by: string;
  note: string;
}

export type ExceptionSource = 'bank' | 'settlement' | 'ledger';

export interface ExceptionItem {
  record_id: string;
  source: ExceptionSource;
  reason_code: string;
  reason_detail: string;
  amount: number;
  record_date: string | null;
  age_days: number | null;
  resolved: boolean;
  resolution: ExceptionResolution | null;
}

export interface ExceptionsResponse {
  as_of_date: string | null;
  summary: ExceptionSummaryBucket[];
  total_count: number;
  total_value_at_risk_rupees: number;
  page: number;
  page_size: number;
  filtered_count: number;
  items: ExceptionItem[];
}

// ============================================================================
// GET /audit-log
// ============================================================================

export interface RunHistoryEntry {
  run_at: string;
  seed: number;
  match_rate_pct: number;
  reconciled_value_rupees: number;
  total_value_rupees: number;
  exceptions_count: number;
  precision_pct: number;
  recall_pct: number;
  false_match_rate_pct: number;
  ai_available: boolean;
  ai_provider: string | null;
}

export interface AuditLogResponse {
  runs: RunHistoryEntry[];
}
