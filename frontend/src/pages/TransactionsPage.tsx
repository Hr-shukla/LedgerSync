import React, { useEffect, useMemo, useState } from 'react';
import { getTransactions, getTransactionAudit, resolveException } from '../lib/api';
import { useApiData } from '../hooks/useApiData';
import { ApiError } from '../lib/api';
import { TransactionRow, TransactionAuditDetail } from '../types';
import { CopyButton } from '../components/common/CopyButton';
import { LoadingState, ErrorState, EmptyState } from '../components/common/AsyncState';
import { useToast } from '../components/common/ToastContext';

interface TransactionsPageProps {
  selectedTransactionId?: string;
  onSelectTransactionId?: (id: string) => void;
}

const PAGE_SIZE = 25;

function statusLabel(row: TransactionRow): string {
  if (row.status === 'exception') return 'Exception Break';
  const pct = Math.round(row.confidence * 100);
  const tier = row.tiers[0] || '';
  if (tier.startsWith('tier1')) return `Exact Match (${pct}%)`;
  if (tier === 'tier2_fuzzy') return `Deterministic Fuzzy (${pct}%)`;
  if (tier === 'tier3_grouping') return `Subset-Sum Grouped (${pct}%)`;
  if (tier === 'tier4_ai') return `AI Resolved (${pct}%)`;
  return `Matched (${pct}%)`;
}

function rowsToCsv(rows: TransactionRow[]): string {
  const header = ['id', 'status', 'tiers', 'confidence', 'bank_ids', 'settlement_ids', 'ledger_ids'];
  const lines = rows.map((r) =>
    [
      r.id, r.status, r.tiers.join('|'), r.confidence,
      r.record_ids.bank.join('|'), r.record_ids.settlement.join('|'), r.record_ids.ledger.join('|'),
    ].map((v) => JSON.stringify(v)).join(',')
  );
  return [header.join(','), ...lines].join('\n');
}

export const TransactionsPage: React.FC<TransactionsPageProps> = ({
  selectedTransactionId,
  onSelectTransactionId,
}) => {
  const [status, setStatus] = useState<'all' | 'matched' | 'exception'>('all');
  const [source, setSource] = useState<'all' | 'bank' | 'settlement' | 'ledger'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerTab, setDrawerTab] = useState<'decision' | 'json'>('decision');
  const { addToast } = useToast();

  const { data, loading, error, reload } = useApiData(
    () =>
      getTransactions({
        status: status === 'all' ? undefined : status,
        source: source === 'all' ? undefined : source,
        search: searchQuery.trim() || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    [status, source, searchQuery, page]
  );

  const [auditDetail, setAuditDetail] = useState<TransactionAuditDetail | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedTransactionId) {
      setAuditDetail(null);
      return;
    }
    let cancelled = false;
    setAuditLoading(true);
    setAuditError(null);
    getTransactionAudit(selectedTransactionId)
      .then((detail) => {
        if (!cancelled) setAuditDetail(detail);
      })
      .catch((e: unknown) => {
        if (!cancelled) setAuditError(e instanceof ApiError ? e.message : 'Failed to load audit detail');
      })
      .finally(() => {
        if (!cancelled) setAuditLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedTransactionId]);

  const items = useMemo(() => data?.items ?? [], [data]);

  const handleSelectRow = (row: TransactionRow) => {
    if (onSelectTransactionId) onSelectTransactionId(row.id);
    setIsDrawerOpen(true);
  };

  const handleExportCsv = () => {
    const blob = new Blob([rowsToCsv(items)], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'transactions.csv';
    a.click();
    URL.revokeObjectURL(url);
    addToast({ type: 'success', title: `Exported ${items.length} rows to CSV` });
  };

  // For an exception-status transaction, the single underlying record can be
  // marked resolved through the same real endpoint the Exceptions Queue uses.
  const soleExceptionRecordId = (row: TransactionRow | undefined): string | null => {
    if (!row || row.status !== 'exception') return null;
    const ids = [...row.record_ids.bank, ...row.record_ids.settlement, ...row.record_ids.ledger];
    return ids.length === 1 ? ids[0] : null;
  };

  const activeRow = items.find((t) => t.id === selectedTransactionId);

  const handleResolveFromDrawer = async () => {
    const recordId = soleExceptionRecordId(activeRow);
    if (!recordId) return;
    try {
      await resolveException(recordId, { resolved_by: 'ui' });
      addToast({ type: 'success', title: `Record ${recordId} marked resolved` });
      await reload();
    } catch (e) {
      addToast({ type: 'error', title: 'Failed to resolve', message: e instanceof Error ? e.message : 'Unknown error' });
    }
  };

  if (loading && !data) return <LoadingState label="Loading transactions..." />;
  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="flex flex-col w-full min-h-[calc(100vh-56px)] bg-surface relative">
      {/* Sub-Header & Metric Ribbon */}
      <div className="px-spacing-xl py-spacing-md bg-surface-container-lowest border-b border-outline-variant flex flex-col gap-spacing-md shadow-2xs">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-baseline gap-spacing-md">
            <h1 className="font-headline-lg text-headline-lg text-on-surface tracking-tight font-semibold">
              Transaction Matching
            </h1>
            <div className="flex items-center gap-spacing-xs">
              <span className="font-label-mono-xs text-label-mono-xs text-on-surface-variant font-semibold uppercase tracking-wider">Queue:</span>
              <span className="font-label-mono-sm text-label-mono-sm text-on-surface font-semibold tabular-nums">
                {data.filter_counts.all} Total Transactions
              </span>
              <span className="text-outline-variant">/</span>
              <span className="font-label-mono-sm text-label-mono-sm text-error font-semibold tabular-nums">
                {data.filter_counts.exception} Unmatched Breaks
              </span>
            </div>
          </div>

          <div className="flex items-center gap-spacing-sm flex-wrap">
            <button
              onClick={handleExportCsv}
              className="h-8 px-spacing-sm border border-outline-variant rounded bg-surface-container-lowest hover:bg-surface-container-low text-on-surface font-body-medium text-body-medium flex items-center gap-spacing-xs shadow-xs transition-colors text-xs active:scale-[0.98]"
              type="button"
            >
              <span className="material-symbols-outlined text-[16px] text-secondary">download</span>
              <span>Matching Report (CSV)</span>
            </button>
            <button
              disabled
              title="No backend endpoint to re-run Tier 4 on demand for a subset -- run the full pipeline via run_reconciliation.py instead."
              className="h-8 px-spacing-sm bg-surface-container-low text-on-surface-variant rounded font-body-medium text-body-medium flex items-center gap-spacing-xs text-xs font-semibold opacity-60 cursor-not-allowed"
              type="button"
            >
              <span className="material-symbols-outlined text-[16px]">psychology</span>
              <span>Re-run Confidence Model (not implemented)</span>
            </button>
          </div>
        </div>

        {/* Filter Control Matrix */}
        <div className="flex items-center justify-between gap-spacing-md pt-spacing-xs flex-wrap">
          <div className="flex items-center gap-spacing-sm flex-1 flex-wrap">
            <div className="relative w-72">
              <span className="material-symbols-outlined absolute left-spacing-sm top-2 text-on-surface-variant text-[16px]">search</span>
              <input
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
                className="w-full h-8 pl-8 pr-7 font-body-sm text-body-sm bg-surface-container-low border border-outline-variant rounded focus:border-secondary focus:ring-1 focus:ring-secondary focus:outline-none placeholder:text-outline text-on-surface"
                placeholder="Filter by record id (UTR, invoice #, settlement id)..."
                type="text"
              />
              {searchQuery && (
                <button onClick={() => { setSearchQuery(''); setPage(1); }} className="absolute right-2 top-2 text-on-surface-variant hover:text-on-surface">
                  <span className="material-symbols-outlined text-[14px]">close</span>
                </button>
              )}
            </div>

            <select
              value={source}
              onChange={(e) => { setSource(e.target.value as typeof source); setPage(1); }}
              className="h-8 px-spacing-sm bg-surface-container-low border border-outline-variant rounded font-body-sm text-body-sm text-on-surface cursor-pointer"
            >
              <option value="all">All Sources (Bank + Settlement + Ledger)</option>
              <option value="bank">Bank only</option>
              <option value="settlement">Settlement only</option>
              <option value="ledger">Ledger only</option>
            </select>
          </div>

          <div className="flex items-center gap-spacing-xs font-label-mono-xs text-label-mono-xs text-on-surface-variant">
            <span className="tabular-nums">Showing {items.length} of {data.total}</span>
          </div>
        </div>

        {/* Status Tabs Row */}
        <div className="flex items-center gap-spacing-xs overflow-x-auto border-t border-outline-variant/60 pt-spacing-sm">
          {(['all', 'matched', 'exception'] as const).map((s) => (
            <button
              key={s}
              onClick={() => { setStatus(s); setPage(1); }}
              className={`px-spacing-sm py-1 rounded font-body-medium text-body-xs flex items-center gap-spacing-xs flex-shrink-0 transition-colors ${
                status === s
                  ? 'bg-surface-container text-on-surface font-semibold border border-outline-variant'
                  : 'text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface'
              }`}
              type="button"
            >
              <span>{s === 'all' ? 'All' : s === 'matched' ? 'Matched' : 'Exceptions'}</span>
              <span className="font-label-mono-xs text-label-mono-xs bg-surface-container-lowest text-on-surface px-spacing-2xs rounded tabular-nums border border-outline-variant/60 font-medium">
                {data.filter_counts[s]}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Primary Workspace */}
      <div className="flex w-full items-start overflow-hidden flex-1">
        <div className="flex-1 min-w-0 bg-surface-container-lowest overflow-x-auto border-r border-outline-variant">
          {items.length === 0 ? (
            <EmptyState
              icon="search_off"
              title="No transactions match your current filters"
              description="Try a different search term, or reset your filters."
              action={{ label: 'Reset All Filters', onClick: () => { setSearchQuery(''); setStatus('all'); setSource('all'); setPage(1); } }}
            />
          ) : (
            <table className="w-full text-left border-collapse border-spacing-0">
              <thead>
                <tr className="h-8 bg-surface-container-low border-b border-outline-variant text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider select-none">
                  <th className="px-spacing-sm py-spacing-xs font-body-xs text-body-xs font-semibold border-r border-outline-variant/60 whitespace-nowrap">Match ID</th>
                  <th className="px-spacing-md py-spacing-xs border-r border-outline-variant/60 bg-surface-container/30 min-w-[220px]">1. Bank Record</th>
                  <th className="px-spacing-md py-spacing-xs border-r border-outline-variant/60 bg-surface-container/30 min-w-[220px]">2. Settlement (Razorpay)</th>
                  <th className="px-spacing-md py-spacing-xs border-r border-outline-variant/60 bg-surface-container/30 min-w-[220px]">3. Internal Ledger</th>
                  <th className="px-spacing-sm py-spacing-xs min-w-[160px] border-r border-outline-variant/60 font-semibold">Status &amp; Confidence</th>
                  <th className="w-12 px-spacing-sm py-spacing-xs text-center font-semibold">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/60 font-body-sm text-body-sm text-on-surface">
                {items.map((tx) => {
                  const isSelected = selectedTransactionId === tx.id;
                  const isException = tx.status === 'exception';
                  return (
                    <tr
                      key={tx.id}
                      onClick={() => handleSelectRow(tx)}
                      className={`h-11 transition-colors cursor-pointer ${
                        isException
                          ? 'bg-red-50/40 hover:bg-red-50/70 border-l-4 border-l-red-500'
                          : isSelected
                          ? 'bg-secondary-fixed/30 border-l-4 border-l-secondary'
                          : 'hover:bg-surface-container-low/60'
                      }`}
                    >
                      <td className="px-spacing-sm py-spacing-xs font-label-mono-sm text-label-mono-sm font-semibold text-secondary border-r border-outline-variant/40 whitespace-nowrap">
                        <div className="flex items-center gap-1">
                          <span>#{tx.id}</span>
                          <CopyButton text={tx.id} />
                        </div>
                      </td>
                      <td className="px-spacing-md py-spacing-xs border-r border-outline-variant/40">
                        {tx.bank && tx.bank.length > 0 ? (
                          <div className="flex flex-col">
                            <div className="flex items-center justify-between">
                              <span className="font-label-mono-xs text-label-mono-xs text-on-surface-variant truncate">
                                {tx.bank.length > 1 ? `${tx.bank.length} bank credits` : tx.bank[0].bank_txn_id}
                              </span>
                              <span className="font-label-mono-sm text-label-mono-sm font-semibold text-on-surface tabular-nums">
                                &#8377;{tx.bank.reduce((s, b) => s + b.amount, 0).toLocaleString('en-IN')}
                              </span>
                            </div>
                            <span className="font-label-mono-xs text-label-mono-xs text-on-surface-variant truncate">
                              UTR: {tx.bank[0].utr}
                            </span>
                          </div>
                        ) : (
                          <span className="font-body-medium text-error font-medium italic text-xs">No bank leg</span>
                        )}
                      </td>
                      <td className="px-spacing-md py-spacing-xs border-r border-outline-variant/40">
                        {tx.settlement && tx.settlement.length > 0 ? (
                          <div className="flex flex-col">
                            <div className="flex items-center justify-between">
                              <span className="font-label-mono-xs text-label-mono-xs text-on-surface-variant truncate">
                                {tx.settlement.length > 1 ? `${tx.settlement.length} settlements` : tx.settlement[0].settlement_id}
                              </span>
                              <span className="font-label-mono-sm text-label-mono-sm font-semibold text-on-surface tabular-nums">
                                &#8377;{tx.settlement.reduce((s, r) => s + r.net_amount, 0).toLocaleString('en-IN')}
                              </span>
                            </div>
                            <span className="font-label-mono-xs text-label-mono-xs text-on-surface-variant truncate">
                              {tx.settlement[0].payment_id}
                            </span>
                          </div>
                        ) : (
                          <span className="font-body-medium text-error font-medium italic text-xs">No settlement leg</span>
                        )}
                      </td>
                      <td className="px-spacing-md py-spacing-xs border-r border-outline-variant/40">
                        {tx.ledger && tx.ledger.length > 0 ? (
                          <div className="flex flex-col">
                            <div className="flex items-center justify-between">
                              <span className="font-body-default text-body-default text-on-surface truncate font-medium">
                                {tx.ledger.length > 1 ? `${tx.ledger.length} invoices` : tx.ledger[0].ledger_id}
                              </span>
                              <span className="font-label-mono-sm text-label-mono-sm font-semibold text-on-surface tabular-nums">
                                &#8377;{tx.ledger.reduce((s, l) => s + l.invoice_amount, 0).toLocaleString('en-IN')}
                              </span>
                            </div>
                            <span className="font-label-mono-xs text-label-mono-xs text-on-surface-variant truncate">
                              {tx.ledger[0].customer}
                            </span>
                          </div>
                        ) : (
                          <span className="font-body-medium text-error font-medium italic text-xs">No ledger leg</span>
                        )}
                      </td>
                      <td className="px-spacing-sm py-spacing-xs border-r border-outline-variant/40">
                        {isException ? (
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-red-50 text-red-900 border border-red-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-red-600"></span>
                            <span>Exception Break</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-secondary-fixed text-on-secondary-fixed border border-secondary-fixed-dim">
                            <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
                            <span>{statusLabel(tx)}</span>
                          </span>
                        )}
                      </td>
                      <td className="px-spacing-sm py-spacing-xs text-center" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleSelectRow(tx)}
                          className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
                          type="button"
                          title="Inspect Record Audit Trail"
                        >
                          <span className="material-symbols-outlined text-[18px]">dock_to_left</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          {items.length > 0 && (
            <div className="p-spacing-sm bg-surface-container-low border-t border-outline-variant flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-spacing-md font-label-mono-xs text-label-mono-xs text-on-surface-variant">
                <span>Page {page} of {totalPages}</span>
                <span>&middot;</span>
                <span>{PAGE_SIZE} rows per page</span>
              </div>
              <div className="flex items-center gap-spacing-xs">
                <button
                  disabled={page === 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="h-7 px-spacing-sm rounded border border-outline-variant/60 bg-surface-container-lowest text-on-surface-variant font-body-xs text-body-xs disabled:opacity-50 disabled:cursor-not-allowed hover:bg-surface-container transition-colors"
                  type="button"
                >
                  Previous
                </button>
                <span className="px-2 font-label-mono-xs text-label-mono-xs text-on-surface font-semibold">{page}</span>
                <button
                  disabled={page === totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="h-7 px-spacing-sm rounded border border-outline-variant bg-surface-container-lowest hover:bg-surface-container text-on-surface font-body-xs text-body-xs disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  type="button"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Side Drawer: Audit Trail Inspector */}
        {isDrawerOpen && selectedTransactionId && (
          <div className="w-[440px] flex-shrink-0 bg-surface-container-lowest flex flex-col justify-between self-stretch border-l border-outline-variant shadow-sm h-full max-h-[calc(100vh-170px)] overflow-hidden">
            <div className="flex flex-col overflow-y-auto">
              <div className="p-spacing-md border-b border-outline-variant flex items-center justify-between bg-surface-container-low">
                <div className="flex flex-col">
                  <div className="flex items-center gap-2">
                    <span className="font-headline-sm text-headline-sm text-on-surface tracking-tight font-semibold">
                      Record Audit Trail: #{selectedTransactionId}
                    </span>
                    <CopyButton text={selectedTransactionId} />
                  </div>
                </div>
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
                  type="button"
                  title="Close Inspector"
                >
                  <span className="material-symbols-outlined text-[20px]">close</span>
                </button>
              </div>

              {auditLoading ? (
                <LoadingState label="Loading audit trail..." />
              ) : auditError ? (
                <ErrorState message={auditError} />
              ) : auditDetail ? (
                <>
                  <div className="flex items-center border-b border-outline-variant px-3 bg-surface-container-low text-[11px] font-mono">
                    <button
                      onClick={() => setDrawerTab('decision')}
                      className={`py-2 px-2.5 font-semibold transition-colors border-b-2 ${drawerTab === 'decision' ? 'border-secondary text-secondary' : 'border-transparent text-on-surface-variant hover:text-on-surface'}`}
                    >
                      Decision Tree
                    </button>
                    <button
                      onClick={() => setDrawerTab('json')}
                      className={`py-2 px-2.5 font-semibold transition-colors border-b-2 ${drawerTab === 'json' ? 'border-secondary text-secondary' : 'border-transparent text-on-surface-variant hover:text-on-surface'}`}
                    >
                      Raw JSON
                    </button>
                  </div>

                  {/* Multi-Way Comparison */}
                  <div className="p-spacing-base border-b border-outline-variant space-y-2 bg-surface-container-low/30">
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
                      Multi-Way Source Comparison
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="p-2 bg-surface-container-lowest rounded border border-outline-variant/60 text-xs">
                        <div className="text-[10px] font-semibold text-secondary">1. Bank</div>
                        {auditDetail.comparison.bank.length === 0 ? (
                          <div className="font-mono text-on-surface-variant mt-0.5">None</div>
                        ) : (
                          auditDetail.comparison.bank.map((b) => (
                            <div key={b.bank_txn_id} className="mt-0.5">
                              <div className="font-mono font-semibold text-on-surface">&#8377;{b.amount.toLocaleString('en-IN')}</div>
                              <div className="text-[10px] text-on-surface-variant truncate">{b.date} &middot; {b.utr}</div>
                            </div>
                          ))
                        )}
                      </div>
                      <div className="p-2 bg-surface-container-lowest rounded border border-outline-variant/60 text-xs">
                        <div className="text-[10px] font-semibold text-secondary">2. Settlement</div>
                        {auditDetail.comparison.settlement.length === 0 ? (
                          <div className="font-mono text-on-surface-variant mt-0.5">None</div>
                        ) : (
                          auditDetail.comparison.settlement.map((s) => (
                            <div key={s.settlement_id} className="mt-0.5">
                              <div className="font-mono font-semibold text-on-surface">&#8377;{s.net_amount.toLocaleString('en-IN')}</div>
                              <div className="text-[10px] text-on-surface-variant truncate">{s.settlement_date} &middot; {s.utr}</div>
                            </div>
                          ))
                        )}
                      </div>
                      <div className="p-2 bg-surface-container-lowest rounded border border-outline-variant/60 text-xs">
                        <div className="text-[10px] font-semibold text-secondary">3. Ledger</div>
                        {auditDetail.comparison.ledger.length === 0 ? (
                          <div className="font-mono text-on-surface-variant mt-0.5">None</div>
                        ) : (
                          auditDetail.comparison.ledger.map((l) => (
                            <div key={l.ledger_id} className="mt-0.5">
                              <div className="font-mono font-semibold text-on-surface">&#8377;{l.invoice_amount.toLocaleString('en-IN')}</div>
                              <div className="text-[10px] text-on-surface-variant truncate">{l.invoice_date} &middot; {l.customer}</div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>

                  {drawerTab === 'decision' && (
                    <div className="p-spacing-base">
                      <div className="flex items-center justify-between mb-spacing-md">
                        <span className="font-label-mono-xs text-label-mono-xs text-on-surface-variant uppercase font-semibold">
                          Rule Resolution Decision Tree
                        </span>
                      </div>
                      {auditDetail.decision_tree.length === 0 ? (
                        <div className="text-xs text-on-surface-variant">No audit events recorded for this transaction.</div>
                      ) : (
                        <ol className="relative border-l border-outline-variant ml-2 space-y-4 text-left">
                          {auditDetail.decision_tree.map((step, idx) => {
                            const isMatched = step.outcome === 'matched';
                            return (
                              <li key={idx} className="ml-4">
                                <span
                                  className={`absolute -left-1.5 top-0.5 flex h-3 w-3 items-center justify-center rounded-full ring-2 ring-surface-container-lowest ${
                                    isMatched ? 'bg-emerald-500' : 'bg-amber-500'
                                  }`}
                                ></span>
                                <div className="flex items-center gap-spacing-xs flex-wrap">
                                  <span className="font-label-mono-xs text-label-mono-xs text-on-surface-variant font-mono">{step.record_id}</span>
                                  <span className={`font-label-mono-xs text-label-mono-xs font-semibold uppercase ${isMatched ? 'text-emerald-800' : 'text-amber-800'}`}>
                                    {step.tier}
                                  </span>
                                  <span className="font-label-mono-xs text-[10px] text-on-surface-variant">
                                    confidence {step.confidence.toFixed(2)}
                                  </span>
                                </div>
                                <p className="font-body-xs text-body-xs text-on-surface mt-0.5 leading-relaxed">{step.reasoning}</p>
                                {step.exception_reason && (
                                  <div className="p-2 bg-surface-container-low rounded border border-outline-variant/60 font-label-mono-xs text-label-mono-xs text-on-surface-variant mt-1.5 font-mono">
                                    Exception reason: <span className="text-on-surface font-semibold">{step.exception_reason}</span>
                                  </div>
                                )}
                              </li>
                            );
                          })}
                        </ol>
                      )}
                    </div>
                  )}

                  {drawerTab === 'json' && (
                    <div className="p-spacing-base space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-mono font-semibold text-on-surface-variant uppercase">Full Audit Response</span>
                        <CopyButton text={JSON.stringify(auditDetail, null, 2)} label="Copy JSON" />
                      </div>
                      <pre className="bg-surface-container-low p-3 rounded border border-outline-variant text-[10px] font-mono text-on-surface overflow-x-auto max-h-96">
                        {JSON.stringify(auditDetail, null, 2)}
                      </pre>
                    </div>
                  )}
                </>
              ) : null}
            </div>

            {/* Bottom Actions */}
            <div className="p-spacing-base border-t border-outline-variant bg-surface-container-lowest flex flex-col gap-spacing-xs">
              {soleExceptionRecordId(activeRow) ? (
                <button
                  onClick={handleResolveFromDrawer}
                  className="w-full h-8 bg-neutral-900 hover:bg-neutral-800 text-white rounded font-body-medium text-body-medium flex items-center justify-center gap-spacing-xs shadow-xs transition-colors font-semibold text-xs active:scale-[0.98]"
                  type="button"
                >
                  <span className="material-symbols-outlined text-[16px] text-emerald-400">check</span>
                  <span>Mark Resolved</span>
                </button>
              ) : (
                <div className="text-center text-[11px] text-on-surface-variant py-1">
                  {activeRow?.status === 'matched' ? 'Already reconciled -- no action needed.' : 'Spans multiple records -- resolve individually from the Exceptions Queue.'}
                </div>
              )}
              <div className="grid grid-cols-2 gap-spacing-xs">
                <button
                  disabled
                  title="No backend endpoint for flagging a matched transaction -- flagged as unimplemented rather than faked."
                  className="h-8 border border-outline-variant text-on-surface-variant rounded font-body-medium text-body-xs flex items-center justify-center gap-1 opacity-50 cursor-not-allowed text-xs"
                  type="button"
                >
                  <span className="material-symbols-outlined text-[15px]">flag</span>
                  <span>Flag for Re-check</span>
                </button>
                <button
                  disabled
                  title="No backend endpoint to unlink a matched group -- flagged as unimplemented rather than faked."
                  className="h-8 border border-outline-variant text-on-surface-variant rounded font-body-medium text-body-xs flex items-center justify-center gap-1 opacity-50 cursor-not-allowed text-xs"
                  type="button"
                >
                  <span className="material-symbols-outlined text-[15px]">link_off</span>
                  <span>Unlink Sources</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
