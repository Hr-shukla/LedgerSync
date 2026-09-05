// Original mock-only types, kept for the still-decorative, out-of-scope
// parts of the UI (mockData.ts, GlobalSearchModal, JournalPreviewModal,
// PlatformPages) that were not part of this integration pass. See the four
// real screens (Overview/Transactions/Exceptions/AuditLog) and ../types
// for the types that now mirror the actual backend contract.

export type ReconciliationTier = 'tier1_exact' | 'tier2_fuzzy' | 'tier3_ai' | 'tier4_exceptions';

export type TransactionStatus =
  | 'Exact Match (100%)'
  | 'Deterministic Fuzzy (95%)'
  | 'AI Resolved (91%)'
  | 'AI Resolved (89%)'
  | 'AI Resolved (78%)'
  | 'Exception Break';

export interface DecisionStep {
  time: string;
  type: 'failed' | 'fuzzy' | 'ai' | 'policy' | 'exact';
  title: string;
  description: string;
  metadata?: {
    ruleId?: string;
    criteria?: string;
    pan?: string;
    confidence?: number;
  };
}

export interface TransactionRecord {
  id: string;
  timestamp: string;
  tier: ReconciliationTier;
  confidenceScore: number;
  status: TransactionStatus;
  isUnsettled?: boolean;

  bank: {
    entity: string;
    amount: number;
    utr: string;
    type?: 'DR' | 'CR';
    account?: string;
    missing?: boolean;
  };

  gateway: {
    id: string;
    amount: number;
    fee?: number;
    feePercentage?: number;
    status: string;
    missing?: boolean;
  };

  ledger: {
    invoiceRef: string;
    amount: number;
    accountCode: string;
    vendorOrCustomer: string;
    missing?: boolean;
  };

  auditTrail: {
    executionId: string;
    reconciledAmount: number;
    settledDate: string;
    decisionTree: DecisionStep[];
  };
}

export type ExceptionCategory =
  | 'no_counterpart'
  | 'amount_mismatch'
  | 'low_ai_confidence'
  | 'duplicate_split';

export interface ExceptionItem {
  id: string;
  category: ExceptionCategory;
  categoryLabel: string;
  reference: string;
  valueAtRisk: number;
  ageDays: number;
  dateOpened: string;
  isOverdue?: boolean;
  isCriticalOverdue?: boolean;
  title: string;
  reviewer: string;
  status: 'open' | 'resolved' | 'escalated' | 'assigned';

  bankRecord?: {
    label: string;
    amount: string;
    note?: string;
  };
  gatewayRecord?: {
    label: string;
    amount: string;
    note?: string;
  };
  ledgerRecord?: {
    label: string;
    amount: string;
    note?: string;
  };
  variance?: {
    amount: number;
    label: string;
  };

  aiDiagnostics: {
    probableCause: string;
    referenceCode?: string;
    suggestedAccount?: string;
    candidateVendors?: string[];
    confidence?: number;
  };

  availableActions: string[];
}

export interface EngineRunLog {
  runId: string;
  runType: 'Daily EOD Batch' | 'Settlement Ingestion' | 'Manual Re-trigger' | 'Hourly Micro-batch' | 'ERP Ingestion';
  timestamp: string;
  triggerType: 'cron' | 'webhook' | 'user' | 'sync';
  triggeredBy: string;
  triggerDetail: string;
  processedTxns: number;
  exactCount: number;
  fuzzyCount: number;
  aiCount: number;
  exceptionCount: number;
  matchRate: number;
  latencySeconds: number;
  blockHash: string;
  status: 'Completed' | 'Partial' | 'In Progress';
}

export interface IngestionFeed {
  id: string;
  name: string;
  type: string;
  icon: string;
  status: 'healthy' | 'warning' | 'error';
  lastSync: string;
  batchInfo: string;
  volumeLabel: string;
}
