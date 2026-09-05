import {
  ExceptionItem,
  EngineRunLog,
  IngestionFeed,
  TransactionRecord
} from '../types/legacy';

// ============================================================================
// SINGLE SOURCE OF TRUTH METRICS (STRICT MATHEMATICAL CONSISTENCY)
// ============================================================================
export const SYSTEM_METRICS = {
  totalTransactions: 12482,
  reconciledCount: 12444, // 10784 + 1110 + 550
  unmatchedBreaksCount: 38, // 12482 - 12444 = 38
  
  matchRatePercent: 97.42,
  targetMatchRatePercent: 98.0,
  matchRateDelta: '+0.8%',
  
  totalGrossVolumeINR: 502180000, // ₹50,21,80,000
  reconciledVolumeINR: 489240150, // ₹48,92,40,150
  valueAtRiskINR: 12939850,       // ₹1,29,39,850 (48,92,40,150 + 1,29,39,850 = 50,21,80,000)
  volumeReconciledPercent: 97.4,
  valueAtRiskPercentOfGross: 0.26,

  // Confidence threshold unified everywhere
  confidenceThreshold: 0.75, // 75%
  
  // Tier breakdown (sums to 12,482 txns and ₹50,21,80,000)
  tiers: [
    {
      id: 'tier1_exact',
      name: 'Tier 1: Exact Hash & UTR Match',
      description: 'Deterministic 1:1 bilateral ledger match',
      records: 10784,
      percentage: 86.4,
      settledAmountINR: 422310000,
      confidenceLabel: '100%',
      status: 'Auto-Settled',
      color: '#0F172A'
    },
    {
      id: 'tier2_fuzzy',
      name: 'Tier 2: Deterministic Rule / Fuzzy',
      description: 'Timestamp jitter window (±180s) + MDR fee offset',
      records: 1110,
      percentage: 8.9,
      settledAmountINR: 44700000,
      confidenceLabel: '≥75%',
      status: 'Auto-Settled',
      color: '#006398'
    },
    {
      id: 'tier3_ai',
      name: 'Tier 3: AI Inference Model',
      description: 'Counterparty alias, split payment batch, truncated UTR',
      records: 550,
      percentage: 4.4,
      settledAmountINR: 22230150,
      confidenceLabel: '75–94%',
      status: 'Auto-Settled',
      color: '#5bb8fe'
    },
    {
      id: 'tier4_exceptions',
      name: 'Tier 4: Exceptions Queue',
      description: 'Unresolved ledger mismatch or gateway discrepancy',
      records: 38,
      percentage: 0.3,
      settledAmountINR: 12939850,
      confidenceLabel: 'Review',
      status: 'Review in Queue',
      color: '#ba1a1a'
    }
  ],

  // Exception categories (sums to 38 records and ₹1,29,39,850)
  exceptionCategories: [
    {
      id: 'no_counterpart',
      label: 'No Counterpart Found',
      count: 16,
      amountINR: 5420000,
      amountFormatted: '₹54,20,000'
    },
    {
      id: 'amount_mismatch',
      label: 'Amount Mismatch',
      count: 11,
      amountINR: 3815450,
      amountFormatted: '₹38,15,450'
    },
    {
      id: 'low_ai_confidence',
      label: 'Low AI Confidence (<75%)',
      count: 7,
      amountINR: 2480000,
      amountFormatted: '₹24,80,000'
    },
    {
      id: 'duplicate_split',
      label: 'Duplicate / Split Ambiguity',
      count: 4,
      amountINR: 1224000,
      amountFormatted: '₹12,24,000'
    }
  ]
};

// ============================================================================
// CONNECTED FEEDS
// ============================================================================
export const CONNECTED_FEEDS: IngestionFeed[] = [
  {
    id: 'feed_hdfc',
    name: 'HDFC Corporate Current A/C',
    type: 'Direct Core Banking API Feed (Host-to-Host)',
    icon: 'account_balance',
    status: 'healthy',
    lastSync: 'Synced 12m ago',
    batchInfo: 'Last batch #HDFC-441',
    volumeLabel: '4,210 txns'
  },
  {
    id: 'feed_razorpay',
    name: 'Razorpay Settlement Gateway',
    type: 'Merchant Payouts, Refunds & UPI Captures',
    icon: 'payments',
    status: 'healthy',
    lastSync: 'Synced 8m ago',
    batchInfo: 'Webhook payload ACK: 200',
    volumeLabel: '7,120 txns'
  },
  {
    id: 'feed_sap',
    name: 'SAP ERP Ledger Integration',
    type: 'Internal General Ledger & Journal Vouchers',
    icon: 'table_chart',
    status: 'healthy',
    lastSync: 'Synced 4m ago',
    batchInfo: 'RFC connection active',
    volumeLabel: '12,482 jnls'
  }
];

// ============================================================================
// SEED TRANSACTIONS
// ============================================================================
export const INITIAL_TRANSACTIONS: TransactionRecord[] = [
  {
    id: 'REC-9821',
    timestamp: '2024-10-31 14:12:05',
    tier: 'tier3_ai',
    confidenceScore: 0.91,
    status: 'AI Resolved (91%)',
    bank: {
      entity: 'INFOSYS BUSINESS PROCESS',
      amount: 1480000,
      utr: 'HDFCN98210398',
      type: 'CR',
      account: 'HDFC-9201'
    },
    gateway: {
      id: 'pout_98210',
      amount: 1480000,
      status: 'Captured'
    },
    ledger: {
      invoiceRef: 'INV-2024-881',
      amount: 1480000,
      accountCode: '#10200',
      vendorOrCustomer: 'Infosys BPM Ltd'
    },
    auditTrail: {
      executionId: 'exe_9821a_fin_close',
      reconciledAmount: 1480000,
      settledDate: 'Oct 31, 2024 · Value Date Confirmed',
      decisionTree: [
        {
          time: '14:12:01.120',
          type: 'failed',
          title: 'Exact Match Failed',
          description: 'Exact string comparison failed between Bank entity (INFOSYS BUSINESS PROCESS) and Ledger vendor (Infosys BPM Ltd).'
        },
        {
          time: '14:12:02.004',
          type: 'fuzzy',
          title: 'Fuzzy Match Triggered',
          description: 'Evaluated candidate pairs: Transaction amount ₹14,80,000 matches exactly (delta 0.00). Value date differential: 0 business days.'
        },
        {
          time: '14:12:03.245',
          type: 'ai',
          title: 'AI Alias Resolution',
          description: 'Cross-referenced corporate entity dictionary & PAN AAACI1234F. Semantic confidence calculated at 0.9142.',
          metadata: { pan: 'AAACI1234F', confidence: 0.9142 }
        },
        {
          time: '14:12:04.011',
          type: 'policy',
          title: 'Policy Auto-Applied',
          description: 'Rule applied based on validated corporate vendor match policy.',
          metadata: {
            ruleId: 'RULE-CORP-B2B-AUTOPASS',
            criteria: 'Vendor Conf >= 0.75 && Variance == 0'
          }
        }
      ]
    }
  },
  {
    id: 'REC-9820',
    timestamp: '2024-10-31 13:58:22',
    tier: 'tier2_fuzzy',
    confidenceScore: 0.95,
    status: 'Deterministic Fuzzy (95%)',
    bank: {
      entity: 'Tata Consultancy Services',
      amount: 320500,
      utr: 'HDFCN98208819',
      type: 'CR'
    },
    gateway: {
      id: 'pay_Tcs820',
      amount: 320500,
      status: 'Processed'
    },
    ledger: {
      invoiceRef: 'INV-2024-880',
      amount: 320500,
      accountCode: '#10200',
      vendorOrCustomer: 'Tata Consultancy Services'
    },
    auditTrail: {
      executionId: 'exe_9820b_sys',
      reconciledAmount: 320500,
      settledDate: 'Oct 31, 2024 · Value Date Confirmed',
      decisionTree: [
        {
          time: '13:58:20.100',
          type: 'exact',
          title: 'UTR Partial Hash Match',
          description: 'Bank UTR prefix matched gateway settlement report reference within 180s jitter window.'
        },
        {
          time: '13:58:21.050',
          type: 'policy',
          title: 'Deterministic Settlement Auto-Lock',
          description: 'Zero rupee variance against General Ledger voucher INV-2024-880.'
        }
      ]
    }
  },
  {
    id: 'REC-9819',
    timestamp: '2024-10-31 13:45:10',
    tier: 'tier1_exact',
    confidenceScore: 1.0,
    status: 'Exact Match (100%)',
    bank: {
      entity: 'Wipro Technologies',
      amount: 88400,
      utr: 'HDFCN98197712',
      type: 'CR'
    },
    gateway: {
      id: 'pay_Wip919',
      amount: 88400,
      status: 'Processed'
    },
    ledger: {
      invoiceRef: 'INV-2024-879',
      amount: 88400,
      accountCode: '#20100',
      vendorOrCustomer: 'Wipro Technologies'
    },
    auditTrail: {
      executionId: 'exe_9819c_sys',
      reconciledAmount: 88400,
      settledDate: 'Oct 31, 2024 · Value Date Confirmed',
      decisionTree: [
        {
          time: '13:45:10.002',
          type: 'exact',
          title: 'Bilateral Hash 100% Match',
          description: 'Direct bilateral key match between Bank UTR and Gateway Settlement ID.'
        }
      ]
    }
  },
  {
    id: 'REC-9818',
    timestamp: '2024-10-31 12:20:00',
    tier: 'tier4_exceptions',
    confidenceScore: 0.12,
    status: 'Exception Break',
    isUnsettled: true,
    bank: {
      entity: 'Missing Bank Credit',
      amount: 0,
      utr: 'Unsettled at clearing house',
      missing: true
    },
    gateway: {
      id: 'pay_Z9021a',
      amount: 1200000,
      status: 'Processed'
    },
    ledger: {
      invoiceRef: 'INV-2024-879',
      amount: 1200000,
      accountCode: '#11000',
      vendorOrCustomer: 'Bharti Enterprises'
    },
    auditTrail: {
      executionId: 'exe_9818_break',
      reconciledAmount: 1200000,
      settledDate: 'Unsettled · Pending Bank Credit Verification',
      decisionTree: [
        {
          time: '12:20:00.010',
          type: 'failed',
          title: 'Bank Ingestion Break',
          description: 'No corresponding bank statement credit found for payout pay_Z9021a within T+2 settlement window.'
        },
        {
          time: '12:20:00.450',
          type: 'failed',
          title: 'Routed to Exceptions Queue',
          description: 'Flagged as Exception Break #EXP-402 for treasury investigation.'
        }
      ]
    }
  },
  {
    id: 'REC-9817',
    timestamp: '2024-10-31 11:15:44',
    tier: 'tier1_exact',
    confidenceScore: 1.0,
    status: 'Exact Match (100%)',
    bank: {
      entity: 'Reliance Retail Ltd',
      amount: 450000,
      utr: 'HDFCN98171120',
      type: 'CR'
    },
    gateway: {
      id: 'pay_Rel9928',
      amount: 441000,
      fee: 9000,
      feePercentage: 2.0,
      status: 'Processed'
    },
    ledger: {
      invoiceRef: 'INV-2024-878',
      amount: 450000,
      accountCode: '#30200',
      vendorOrCustomer: 'Supply Order'
    },
    auditTrail: {
      executionId: 'exe_9817d_sys',
      reconciledAmount: 450000,
      settledDate: 'Oct 31, 2024 · Value Date Confirmed',
      decisionTree: [
        {
          time: '11:15:44.008',
          type: 'exact',
          title: 'Fee Tolerant Exact Match',
          description: 'Bank credit matches gross ledger amount minus standard 2.0% MDR gateway fee.'
        }
      ]
    }
  },
  {
    id: 'REC-9816',
    timestamp: '2024-10-31 10:04:19',
    tier: 'tier3_ai',
    confidenceScore: 0.89,
    status: 'AI Resolved (89%)',
    bank: {
      entity: 'Larsen & Toubro Ltd',
      amount: 615200,
      utr: 'HDFCN98160012',
      type: 'CR'
    },
    gateway: {
      id: 'bth_LT991',
      amount: 615200,
      status: 'Aggregated Payout'
    },
    ledger: {
      invoiceRef: '2 Invoices Split',
      amount: 615200,
      accountCode: '#40100',
      vendorOrCustomer: '#INV-875 (₹4L) + #INV-876 (₹2.15L)'
    },
    auditTrail: {
      executionId: 'exe_9816e_ai',
      reconciledAmount: 615200,
      settledDate: 'Oct 31, 2024 · Value Date Confirmed',
      decisionTree: [
        {
          time: '10:04:19.120',
          type: 'fuzzy',
          title: 'Subset-Sum Grouping Evaluated',
          description: 'Aggregated bank credit matches sum of 2 open ledger invoices #INV-875 (₹4,00,000) and #INV-876 (₹2,15,200).'
        },
        {
          time: '10:04:19.890',
          type: 'ai',
          title: 'AI Split Allocation Confirmed',
          description: 'High semantic confidence (0.89) linking common corporate GSTIN and invoice dates.'
        }
      ]
    }
  },
  {
    id: 'REC-9815',
    timestamp: '2024-10-31 09:40:12',
    tier: 'tier1_exact',
    confidenceScore: 1.0,
    status: 'Exact Match (100%)',
    bank: {
      entity: 'Zomato Media Pvt Ltd',
      amount: 112000,
      utr: 'HDFCN98159930',
      type: 'CR'
    },
    gateway: {
      id: 'pay_Zom1001',
      amount: 109760,
      fee: 2240,
      status: 'Captured'
    },
    ledger: {
      invoiceRef: 'INV-2024-874',
      amount: 112000,
      accountCode: '#40100',
      vendorOrCustomer: 'B2B Corporate Dining'
    },
    auditTrail: {
      executionId: 'exe_9815f_sys',
      reconciledAmount: 112000,
      settledDate: 'Oct 31, 2024 · Value Date Confirmed',
      decisionTree: [
        {
          time: '09:40:12.001',
          type: 'exact',
          title: 'Exact Match Bilateral Verified',
          description: 'Payment verified with exact UTR and known contractual fee schedule.'
        }
      ]
    }
  }
];

// ============================================================================
// SEED EXCEPTIONS QUEUE (38 OPEN RECORDS, ₹1,29,39,850 VALUE AT RISK)
// ============================================================================
export const INITIAL_EXCEPTIONS: ExceptionItem[] = [
  {
    id: 'EXP-402',
    category: 'no_counterpart',
    categoryLabel: 'No Counterpart Found',
    reference: 'HDFC00029482103',
    valueAtRisk: 1840000,
    ageDays: 5,
    dateOpened: 'Oct 26, 2024',
    title: 'Bank debit of ₹18,40,000 without corresponding SAP purchase order or Gateway payout',
    reviewer: 'Unassigned',
    status: 'open',
    bankRecord: {
      label: 'Bank (HDFC 9201):',
      amount: '₹18,40,000.00 [DR]'
    },
    gatewayRecord: {
      label: 'Gateway:',
      amount: 'None (0 matches)'
    },
    ledgerRecord: {
      label: 'ERP Ledger:',
      amount: 'None (Unrecorded)'
    },
    aiDiagnostics: {
      probableCause: 'Probable direct tax payment or manual treasury transfer not recorded in ERP. Narration string matches standard CBDT advance tax pattern: ITNS280-TIN-8930214.',
      referenceCode: 'ITNS280-TIN-8930214'
    },
    availableActions: ['Mark Resolved', 'Assign to ERP Team', 'Ignore / Write-off']
  },
  {
    id: 'EXP-401',
    category: 'amount_mismatch',
    categoryLabel: 'Amount Mismatch',
    reference: 'RZP-BATCH-892418',
    valueAtRisk: 4850,
    ageDays: 2,
    dateOpened: 'Oct 29, 2024',
    title: '₹4,850 variance between Gateway captured net and Bank credit settlement',
    reviewer: 'Vikram Rao (Treasury)',
    status: 'open',
    bankRecord: {
      label: 'Bank Credit:',
      amount: '₹12,45,150.00'
    },
    gatewayRecord: {
      label: 'Gateway Net:',
      amount: '₹12,50,000.00'
    },
    variance: {
      amount: -4850,
      label: '-₹4,850.00 (Unrec. GST)'
    },
    aiDiagnostics: {
      probableCause: 'Gateway applied 18% GST on platform fee which was not factored into automated ERP journal. Recommending auto-posting adjustment journal to account #2104-INPUT-TAX.',
      suggestedAccount: '#2104-INPUT-TAX'
    },
    availableActions: ['Auto-Post Adjustment Journal', 'Mark Resolved', 'Escalate to Tax']
  },
  {
    id: 'EXP-400',
    category: 'low_ai_confidence',
    categoryLabel: 'Low AI Confidence (<75%)',
    reference: 'NEFT-CR-AXIS-992019',
    valueAtRisk: 820000,
    ageDays: 1,
    dateOpened: 'Oct 30, 2024',
    title: 'Ambiguous entity match: Bank counterparty string conflicts with vendor master ledger',
    reviewer: 'Priya Sharma (Lead)',
    status: 'open',
    bankRecord: {
      label: 'Bank Record Narration:',
      amount: '"RTL TECH PVT" (₹8,20,000)'
    },
    ledgerRecord: {
      label: 'ERP Candidate:',
      amount: '"Retail Technology Labs"'
    },
    aiDiagnostics: {
      probableCause: 'Two possible counterpart vendor accounts with identical balances. Human confirmation required to bind GSTIN.',
      candidateVendors: ['Vendor #4092 (Retail Tech Ltd)', 'Vendor #8112 (RTL Logistics)'],
      confidence: 0.58
    },
    availableActions: ['Link to Vendor #4092', 'Link to Vendor #8112', 'Flag Exception']
  },
  {
    id: 'EXP-399',
    category: 'duplicate_split',
    categoryLabel: 'Duplicate / Split Ambiguity',
    reference: 'RTGS-SBIN-882190',
    valueAtRisk: 1500000,
    ageDays: 8,
    dateOpened: 'Oct 23, 2024',
    isOverdue: true,
    title: 'Single bank credit matching two separate customer invoices with split risk',
    reviewer: 'Unassigned',
    status: 'open',
    bankRecord: {
      label: 'Bank Inward:',
      amount: '₹15,00,000.00'
    },
    ledgerRecord: {
      label: 'Ledger Candidates:',
      amount: 'Inv #104: ₹7,50,000.00 · Inv #105: ₹7,50,000.00'
    },
    aiDiagnostics: {
      probableCause: 'Client consolidated two payments into one single RTGS payment without reference tag. High probability 1:2 split match.',
      confidence: 0.88
    },
    availableActions: ['Merge & Reconcile', 'Split Payment', 'Escalate']
  },
  {
    id: 'EXP-398',
    category: 'amount_mismatch',
    categoryLabel: 'Amount Mismatch',
    reference: 'CITINAAX49021',
    valueAtRisk: 12800,
    ageDays: 3,
    dateOpened: 'Oct 28, 2024',
    title: 'Foreign exchange conversion variance of ₹12,800 on USD remittance',
    reviewer: 'Ananya Sen (AP Ops)',
    status: 'open',
    bankRecord: {
      label: 'Bank Realized:',
      amount: '₹34,22,800.00'
    },
    ledgerRecord: {
      label: 'ERP Booked Rate:',
      amount: '₹34,10,000.00'
    },
    variance: {
      amount: 12800,
      label: '+₹12,800.00 (Unrealized FX Gain)'
    },
    aiDiagnostics: {
      probableCause: 'Exchange rate fluctuation between invoice date (₹83.15/USD) and settlement realization (₹83.46/USD). Standard Forex gain entry required.',
      confidence: 0.96
    },
    availableActions: ['Post FX Gain/Loss', 'Mark Resolved']
  }
];

// ============================================================================
// ENGINE RUN LOGS & AUDIT TRAIL
// ============================================================================
export const INITIAL_AUDIT_LOGS: EngineRunLog[] = [
  {
    runId: '#RUN-8492',
    runType: 'Daily EOD Batch',
    timestamp: '2024-10-31 23:59:58 IST (UTC +05:30)',
    triggerType: 'cron',
    triggeredBy: 'System Cron',
    triggerDetail: 'Scheduler daemon v2.4',
    processedTxns: 12482,
    exactCount: 10498,
    fuzzyCount: 1110,
    aiCount: 550,
    exceptionCount: 38,
    matchRate: 97.42,
    latencySeconds: 3.84,
    blockHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    status: 'Completed'
  },
  {
    runId: '#RUN-8491',
    runType: 'Settlement Ingestion',
    timestamp: '2024-10-31 18:00:15 IST (UTC +05:30)',
    triggerType: 'webhook',
    triggeredBy: 'Razorpay Webhook',
    triggerDetail: 'event.settlement_closed (Gateway nodal feed)',
    processedTxns: 3410,
    exactCount: 3290,
    fuzzyCount: 82,
    aiCount: 0,
    exceptionCount: 38,
    matchRate: 98.88,
    latencySeconds: 1.12,
    blockHash: 'a6b4c10298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852c921',
    status: 'Completed'
  },
  {
    runId: '#RUN-8490',
    runType: 'Manual Re-trigger',
    timestamp: '2024-10-31 14:15:02 IST (UTC +05:30)',
    triggerType: 'user',
    triggeredBy: 'Priya Sharma',
    triggerDetail: 'Lead Finance Controller (Targeted queue re-run)',
    processedTxns: 38,
    exactCount: 4,
    fuzzyCount: 0,
    aiCount: 0,
    exceptionCount: 34,
    matchRate: 10.52,
    latencySeconds: 0.45,
    blockHash: '7c89f41298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852f114',
    status: 'Completed'
  },
  {
    runId: '#RUN-8489',
    runType: 'Hourly Micro-batch',
    timestamp: '2024-10-31 12:00:00 IST (UTC +05:30)',
    triggerType: 'cron',
    triggeredBy: 'System Cron',
    triggerDetail: 'Interval worker #3 (Delta window: 60m)',
    processedTxns: 480,
    exactCount: 476,
    fuzzyCount: 0,
    aiCount: 0,
    exceptionCount: 4,
    matchRate: 99.17,
    latencySeconds: 0.28,
    blockHash: '5e41a88298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852e933',
    status: 'Completed'
  },
  {
    runId: '#RUN-8488',
    runType: 'Daily EOD Batch',
    timestamp: '2024-10-30 23:59:59 IST (UTC +05:30)',
    triggerType: 'cron',
    triggeredBy: 'System Cron',
    triggerDetail: 'Scheduler daemon v2.4 (3 core feeds)',
    processedTxns: 11920,
    exactCount: 10012,
    fuzzyCount: 1120,
    aiCount: 418,
    exceptionCount: 370,
    matchRate: 96.89,
    latencySeconds: 4.10,
    blockHash: '3b190f7298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852a441',
    status: 'Completed'
  },
  {
    runId: '#RUN-8487',
    runType: 'ERP Ingestion',
    timestamp: '2024-10-30 16:22:10 IST (UTC +05:30)',
    triggerType: 'sync',
    triggeredBy: 'Oracle NetSuite Sync',
    triggerDetail: 'SuiteTalk REST API worker (Ledger batch v10.3)',
    processedTxns: 11920,
    exactCount: 11920,
    fuzzyCount: 0,
    aiCount: 0,
    exceptionCount: 0,
    matchRate: 100.0,
    latencySeconds: 6.82,
    blockHash: '1a90c23298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852d119',
    status: 'Completed'
  }
];

// ============================================================================
// BACKEND API INTEGRATION HOOKS (PLACEHOLDERS READY FOR REAL ENDPOINTS)
// ============================================================================
// To swap with live Python backend (e.g. FastAPI serving finance-controller pipeline):
// Simply change these functions to call fetch('http://localhost:8000/api/...')

export async function fetchReconciliationOverview() {
  // Real API: return await (await fetch('/api/overview')).json();
  return {
    metrics: SYSTEM_METRICS,
    feeds: CONNECTED_FEEDS,
    recentRuns: INITIAL_AUDIT_LOGS.slice(0, 3)
  };
}

export async function fetchTransactions(filters?: {
  search?: string;
  tier?: string;
  scope?: string;
}) {
  // Real API: return await (await fetch('/api/transactions?...')).json();
  let results = [...INITIAL_TRANSACTIONS];
  if (filters?.tier && filters.tier !== 'all') {
    results = results.filter(t => t.tier === filters.tier);
  }
  if (filters?.search) {
    const q = filters.search.toLowerCase();
    results = results.filter(t => 
      t.id.toLowerCase().includes(q) ||
      t.bank.entity.toLowerCase().includes(q) ||
      t.bank.utr.toLowerCase().includes(q) ||
      t.gateway.id.toLowerCase().includes(q) ||
      t.ledger.invoiceRef.toLowerCase().includes(q)
    );
  }
  return results;
}

export async function fetchExceptionsQueue(filters?: {
  category?: string;
  age?: string;
  reviewer?: string;
}) {
  // Real API: return await (await fetch('/api/exceptions?...')).json();
  let results = [...INITIAL_EXCEPTIONS];
  if (filters?.category && filters.category !== 'all') {
    results = results.filter(e => e.category === filters.category);
  }
  if (filters?.age === 'gt7') {
    results = results.filter(e => e.ageDays > 7);
  } else if (filters?.age === 'gt30') {
    results = results.filter(e => e.ageDays > 30 || e.isCriticalOverdue);
  }
  if (filters?.reviewer && filters.reviewer !== 'All Reviewers') {
    results = results.filter(e => e.reviewer.includes(filters.reviewer!));
  }
  return results;
}

export async function triggerReconciliationRun(batchNumber = '8492') {
  // Real API: return await (await fetch('/api/run_reconciliation', { method: 'POST' })).json();
  return {
    success: true,
    runId: `#RUN-${batchNumber}`,
    timestamp: new Date().toISOString(),
    message: `Batch #${batchNumber} reconciliation completed with 97.42% match rate.`
  };
}

export async function verifyMerkleIntegrity() {
  // Real API: return await (await fetch('/api/audit/verify_merkle')).json();
  return {
    verified: true,
    merkleRoot: '0x8f28b49e612cb3501a4e59178cc0209f87c53641b9a2c3d4e5f6a7b8c9d0e1f2',
    timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }) + ' IST',
    status: 'PASS',
    totalEntriesChecked: 186
  };
}
