import React, { useMemo, useState } from 'react';
import { getExceptions, resolveException, unresolveException } from '../lib/api';
import { useApiData } from '../hooks/useApiData';
import { ExceptionItem } from '../types';
import { CopyButton } from '../components/common/CopyButton';
import { LoadingState, ErrorState, EmptyState } from '../components/common/AsyncState';
import { useToast } from '../components/common/ToastContext';

interface ExceptionsPageProps {
  onNavigateToAuditLog?: () => void;
  onUpdateOpenCount?: (count: number) => void;
}

const PAGE_SIZE = 10;

function exceptionsToCsv(rows: ExceptionItem[]): string {
  const header = ['record_id', 'source', 'reason_code', 'reason_detail', 'amount', 'age_days', 'resolved'];
  const lines = rows.map((r) =>
    header.map((h) => JSON.stringify((r as unknown as Record<string, unknown>)[h] ?? '')).join(',')
  );
  return [header.join(','), ...lines].join('\n');
}

export const ExceptionsPage: React.FC<ExceptionsPageProps> = ({ onNavigateToAuditLog, onUpdateOpenCount }) => {
  const [activeReason, setActiveReason] = useState<string>('all');
  const [ageFilter, setAgeFilter] = useState<'all' | 'gt7' | 'gt30'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [showResolved, setShowResolved] = useState(false);
  const { addToast } = useToast();

  const { data, loading, error, reload } = useApiData(
    () => getExceptions({ page_size: 1000, include_resolved: showResolved }),
    [showResolved]
  );

  const allItems = data?.items ?? [];

  const filtered = useMemo(() => {
    let list = allItems;
    if (activeReason !== 'all') list = list.filter((e) => e.reason_code === activeReason);
    if (ageFilter === 'gt7') list = list.filter((e) => (e.age_days ?? 0) > 7);
    if (ageFilter === 'gt30') list = list.filter((e) => (e.age_days ?? 0) > 30);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (e) =>
          e.record_id.toLowerCase().includes(q) ||
          e.reason_code.toLowerCase().includes(q) ||
          e.reason_detail.toLowerCase().includes(q)
      );
    }
    return list;
  }, [allItems, activeReason, ageFilter, searchQuery]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const gt7Count = allItems.filter((e) => (e.age_days ?? 0) > 7).length;
  const gt30Count = allItems.filter((e) => (e.age_days ?? 0) > 30).length;

  const doResolve = async (recordId: string) => {
    try {
      await resolveException(recordId, { resolved_by: 'ui' });
      addToast({ type: 'success', title: `Exception #${recordId} Resolved` });
      await reload();
      if (onUpdateOpenCount) onUpdateOpenCount(Math.max(0, (data?.total_count ?? 1) - 1));
    } catch (e) {
      addToast({ type: 'error', title: 'Failed to resolve', message: e instanceof Error ? e.message : 'Unknown error' });
    }
  };

  const doUnresolve = async (recordId: string) => {
    try {
      await unresolveException(recordId);
      addToast({ type: 'info', title: `Exception #${recordId} reopened` });
      await reload();
    } catch (e) {
      addToast({ type: 'error', title: 'Failed to reopen', message: e instanceof Error ? e.message : 'Unknown error' });
    }
  };

  const handleBulkResolve = async () => {
    if (selectedIds.length === 0) {
      addToast({ type: 'warning', title: 'No Selection', message: 'Please select at least one exception to resolve.' });
      return;
    }
    const ids = [...selectedIds];
    setSelectedIds([]);
    let succeeded = 0;
    for (const id of ids) {
      try {
        await resolveException(id, { resolved_by: 'ui-bulk' });
        succeeded++;
      } catch {
        // continue with the rest; report the partial result below
      }
    }
    addToast({
      type: succeeded === ids.length ? 'success' : 'warning',
      title: 'Bulk Resolve Executed',
      message: `${succeeded}/${ids.length} exceptions resolved.`,
    });
    await reload();
  };

  const handleExportCsv = () => {
    const blob = new Blob([exceptionsToCsv(filtered)], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'exceptions.csv';
    a.click();
    URL.revokeObjectURL(url);
    addToast({ type: 'success', title: `Exported ${filtered.length} exceptions to CSV` });
  };

  if (loading) return <LoadingState label="Loading exceptions queue..." />;
  if (error || !data) return <ErrorState message={error || 'No data returned'} onRetry={reload} />;

  return (
    <div className="p-spacing-xl space-y-spacing-lg max-w-[1680px] mx-auto w-full">
      <div className="bg-surface-container-lowest rounded-lg p-spacing-lg shadow-xs space-y-spacing-base border border-outline-variant">
        <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-spacing-md">
          <div className="space-y-spacing-2xs">
            <div className="flex items-center gap-spacing-sm flex-wrap">
              <span className="font-headline-lg text-headline-lg text-on-surface font-semibold tracking-tight">
                Exceptions Worklist Queue
              </span>
              <span className="inline-flex items-center gap-spacing-xs bg-error-container text-on-error-container px-spacing-sm py-spacing-2xs rounded text-label-mono-xs font-label-mono-xs uppercase tracking-wide font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-error"></span>
                {data.total_count} Open Exceptions &middot; &#8377;{data.total_value_at_risk_rupees.toLocaleString('en-IN')} Total Value at Risk
              </span>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Reason codes and ages are computed directly from the reconciliation run -- no simulated diagnostics.
            </p>
          </div>

          <div className="flex items-center gap-spacing-xs flex-wrap">
            <button
              onClick={() => { setShowResolved((v) => !v); setPage(1); }}
              className={`h-8 px-spacing-md rounded border font-body-medium text-body-medium flex items-center gap-spacing-xs shadow-xs text-xs font-medium active:scale-[0.98] transition-colors ${
                showResolved
                  ? 'bg-surface-container text-on-surface border-outline-variant'
                  : 'bg-surface-container-lowest text-on-surface-variant border-outline-variant hover:bg-surface-container-low'
              }`}
              type="button"
              title="Resolved exceptions are excluded from the queue and every count by default -- toggle this to also see them, with a Reopen option."
            >
              <span className="material-symbols-outlined text-[16px]">{showResolved ? 'visibility_off' : 'visibility'}</span>
              <span>{showResolved ? 'Hide' : 'Show'} Resolved ({data.resolved_count})</span>
            </button>
            <button
              onClick={handleBulkResolve}
              className="h-8 px-spacing-md rounded bg-secondary-fixed text-on-secondary-fixed hover:bg-secondary-fixed-dim transition-colors flex items-center gap-spacing-xs font-body-medium text-body-medium shadow-xs text-xs font-semibold border border-secondary-fixed-dim active:scale-[0.98]"
              type="button"
            >
              <span className="material-symbols-outlined text-[16px]">task_alt</span>
              <span>Bulk Resolve Selected ({selectedIds.length})</span>
            </button>
            <button
              onClick={handleExportCsv}
              className="h-8 px-spacing-md rounded bg-primary text-on-primary hover:bg-neutral-800 transition-colors flex items-center gap-spacing-xs font-body-medium text-body-medium shadow-xs text-xs font-semibold active:scale-[0.98]"
              type="button"
            >
              <span className="material-symbols-outlined text-[16px]">download</span>
              <span>Export Exceptions (CSV)</span>
            </button>
          </div>
        </div>

        {/* Root Cause Grouping Tabs -- real reason codes + real counts from the backend's own summary aggregation */}
        <div className="flex items-center gap-spacing-xs overflow-x-auto pb-1 text-body-xs font-body-medium border-b border-outline-variant/30">
          <button
            onClick={() => { setActiveReason('all'); setPage(1); }}
            className={`px-spacing-md py-spacing-xs rounded-t font-medium flex items-center gap-spacing-xs whitespace-nowrap transition-colors ${
              activeReason === 'all'
                ? 'bg-primary-container text-on-primary font-semibold shadow-xs'
                : 'bg-surface-container-low text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
            }`}
            type="button"
          >
            <span>All Open</span>
            <span className="px-1.5 py-0.5 rounded bg-surface-container-lowest/20 text-on-primary font-label-mono-xs tabular-nums font-semibold">
              {data.total_count}
            </span>
          </button>

          {data.summary.map((bucket) => (
            <button
              key={bucket.reason_code}
              onClick={() => { setActiveReason(bucket.reason_code); setPage(1); }}
              className={`px-spacing-md py-spacing-xs rounded-t font-medium flex items-center gap-spacing-xs whitespace-nowrap transition-colors ${
                activeReason === bucket.reason_code
                  ? 'bg-surface-container text-on-surface font-semibold border-b-2 border-secondary'
                  : 'bg-surface-container-low text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
              }`}
              type="button"
            >
              <span>{bucket.reason_code}</span>
              <span className="px-1.5 py-0.5 rounded font-label-mono-xs tabular-nums font-semibold bg-surface-container-high text-on-surface">
                {bucket.count} &middot; &#8377;{bucket.value_at_risk_rupees.toLocaleString('en-IN')}
              </span>
            </button>
          ))}
        </div>

        <div className="flex items-center justify-between flex-wrap gap-spacing-sm pt-spacing-2xs">
          <div className="flex items-center gap-spacing-xs flex-wrap">
            <div className="relative w-64 mr-2">
              <span className="material-symbols-outlined absolute left-2 top-1 text-on-surface-variant text-[15px]">search</span>
              <input
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
                placeholder="Filter by record id, reason..."
                className="w-full h-6 pl-7 pr-6 rounded bg-surface-container-low text-on-surface text-[11px] placeholder:text-outline border border-outline-variant focus:outline-none focus:border-secondary"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="absolute right-1.5 top-1 text-on-surface-variant hover:text-on-surface">
                  <span className="material-symbols-outlined text-xs">close</span>
                </button>
              )}
            </div>

            <span className="font-label-mono-xs text-label-mono-xs text-on-surface-variant uppercase font-semibold mr-spacing-xs">
              Age Filter:
            </span>
            <button
              onClick={() => { setAgeFilter('all'); setPage(1); }}
              className={`h-6 px-spacing-sm rounded font-label-mono-xs text-label-mono-xs font-medium transition-colors ${
                ageFilter === 'all' ? 'bg-surface-container text-on-surface font-semibold border border-outline-variant' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
              }`}
              type="button"
            >
              All Ages
            </button>
            <button
              onClick={() => { setAgeFilter('gt7'); setPage(1); }}
              className={`h-6 px-spacing-sm rounded font-label-mono-xs text-label-mono-xs transition-colors flex items-center gap-1 ${
                ageFilter === 'gt7' ? 'bg-surface-container text-on-surface font-semibold border border-outline-variant' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
              }`}
              type="button"
            >
              <span>&gt;7 Days Open</span>
              <span className="bg-error/10 text-error font-semibold px-1 rounded">{gt7Count}</span>
            </button>
            <button
              onClick={() => { setAgeFilter('gt30'); setPage(1); }}
              className={`h-6 px-spacing-sm rounded font-label-mono-xs text-label-mono-xs transition-colors flex items-center gap-1 ${
                ageFilter === 'gt30' ? 'bg-surface-container text-on-surface font-semibold border border-outline-variant' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
              }`}
              type="button"
            >
              <span>&gt;30 Days Overdue</span>
              <span className="bg-error text-on-error font-semibold px-1 rounded">{gt30Count}</span>
            </button>
          </div>
          {data.as_of_date && (
            <span className="font-body-xs text-body-xs text-on-surface-variant">
              Ages computed as of {data.as_of_date} (latest transaction date in the batch)
            </span>
          )}
        </div>
      </div>

      <div className="space-y-spacing-md">
        {filtered.length === 0 ? (
          <EmptyState
            icon="check_circle"
            title="No exceptions match your current filter"
            description="All items in this category have either been resolved or moved to another filter bucket."
            action={{
              label: 'Reset Queue Filters',
              onClick: () => { setActiveReason('all'); setAgeFilter('all'); setSearchQuery(''); setPage(1); },
            }}
          />
        ) : (
          pageItems.map((item) => {
            const isSelected = selectedIds.includes(item.record_id);
            const isOverdue = (item.age_days ?? 0) > 7;

            return (
              <div
                key={item.record_id}
                className={`bg-surface-container-lowest rounded-lg p-spacing-base shadow-xs hover:shadow-sm transition-shadow space-y-spacing-sm border ${
                  isOverdue ? 'border-l-4 border-l-error border-t-outline-variant border-r-outline-variant border-b-outline-variant' : 'border-outline-variant'
                } ${item.resolved ? 'opacity-60' : ''}`}
              >
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-spacing-sm">
                  <div className="flex items-start lg:items-center gap-spacing-sm">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={item.resolved}
                      onChange={() =>
                        setSelectedIds((prev) =>
                          prev.includes(item.record_id) ? prev.filter((i) => i !== item.record_id) : [...prev, item.record_id]
                        )
                      }
                      className="mt-1 lg:mt-0 w-4 h-4 rounded bg-surface-container-low text-primary accent-primary cursor-pointer"
                    />
                    <div className="flex items-center gap-spacing-xs flex-wrap">
                      <span className="font-label-mono-sm text-label-mono-sm font-semibold text-on-surface">#{item.record_id}</span>
                      <CopyButton text={item.record_id} />
                      <span className="inline-flex items-center gap-1 px-spacing-xs py-0.5 rounded text-label-mono-xs font-label-mono-xs font-semibold bg-error-container text-on-error-container">
                        <span className="w-1.5 h-1.5 rounded-full bg-error"></span>
                        {item.reason_code}
                      </span>
                      <span className="font-label-mono-xs text-label-mono-xs px-1.5 py-0.5 rounded bg-surface-container-high border border-outline-variant text-on-surface-variant uppercase">
                        {item.source}
                      </span>
                      {isOverdue && (
                        <span className="bg-error text-white font-mono text-[10px] uppercase font-bold px-1.5 py-0.5 rounded">
                          OVERDUE ({item.age_days}D)
                        </span>
                      )}
                      {item.resolved && (
                        <span className="bg-emerald-100 text-emerald-800 font-mono text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border border-emerald-200">
                          RESOLVED
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-spacing-md self-end lg:self-auto">
                    <div className="text-right">
                      <div className="font-label-mono-xs text-label-mono-xs text-on-surface-variant uppercase font-semibold">Value at Risk</div>
                      <div className="font-headline-sm text-headline-sm font-semibold text-error tabular-nums">
                        &#8377;{Math.abs(item.amount).toLocaleString('en-IN')}
                      </div>
                    </div>
                    <div className="text-right pl-spacing-sm border-l border-outline-variant/30">
                      <div className="font-label-mono-xs text-label-mono-xs text-on-surface-variant uppercase font-semibold">Age</div>
                      <div className="font-label-mono-sm text-label-mono-sm text-on-surface tabular-nums">
                        {item.age_days ?? '?'}d open <span className="text-on-surface-variant">({item.record_date})</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-12 gap-spacing-md bg-surface-container-low/50 p-spacing-sm rounded border border-outline-variant/40">
                  <div className="xl:col-span-8 space-y-spacing-xs">
                    <div className="flex items-start gap-2 bg-surface-container-lowest p-2 rounded border border-outline-variant/80 text-xs">
                      <span className="material-symbols-outlined text-secondary text-base shrink-0 mt-0.5">info</span>
                      <div className="space-y-1 text-on-surface">
                        <div>
                          <strong className="text-on-surface font-semibold">Reason: </strong>
                          <span className="text-on-surface-variant">{item.reason_detail}</span>
                        </div>
                      </div>
                    </div>
                    {item.resolution && (
                      <div className="text-[11px] font-mono text-emerald-800 bg-emerald-50 p-2 rounded border border-emerald-200">
                        Resolved {new Date(item.resolution.resolved_at).toLocaleString()} by {item.resolution.resolved_by}
                        {item.resolution.note && ` -- "${item.resolution.note}"`}
                      </div>
                    )}
                  </div>

                  <div className="xl:col-span-4 flex flex-col justify-between border-t xl:border-t-0 xl:border-l border-outline-variant/40 pt-2 xl:pt-0 xl:pl-4 space-y-2">
                    <div className="flex flex-col gap-1.5">
                      {item.resolved ? (
                        <button
                          onClick={() => doUnresolve(item.record_id)}
                          className="w-full py-1.5 px-2.5 rounded text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-2xs active:scale-[0.98] bg-surface-container-lowest hover:bg-surface-container text-on-surface border border-outline-variant"
                          type="button"
                        >
                          <span className="material-symbols-outlined text-xs">undo</span>
                          <span>Reopen</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => doResolve(item.record_id)}
                          className="w-full py-1.5 px-2.5 rounded text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-2xs active:scale-[0.98] bg-neutral-900 hover:bg-neutral-800 text-white"
                          type="button"
                        >
                          <span className="material-symbols-outlined text-xs text-emerald-400">check</span>
                          <span>Mark Resolved</span>
                        </button>
                      )}
                      <button
                        disabled
                        title="No backend endpoint for escalation/assignment yet -- flagged as unimplemented rather than faked."
                        className="w-full py-1.5 px-2.5 rounded text-xs font-medium flex items-center justify-center gap-1.5 opacity-50 cursor-not-allowed bg-surface-container-lowest text-on-surface border border-outline-variant"
                        type="button"
                      >
                        <span className="material-symbols-outlined text-xs">flag</span>
                        <span>Escalate (not implemented)</span>
                      </button>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-on-surface-variant pt-2 border-t border-outline-variant/30">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                        <span>Unassigned (no assignee tracking yet)</span>
                      </span>
                      {onNavigateToAuditLog && (
                        <button onClick={onNavigateToAuditLog} className="text-secondary hover:underline font-medium flex items-center gap-0.5">
                          <span>Inspect Audit</span>
                          <span className="material-symbols-outlined text-[13px]">arrow_forward</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {filtered.length > 0 && (
        <div className="p-spacing-sm bg-surface-container-low border border-outline-variant rounded flex items-center justify-between flex-wrap gap-2">
          <div className="font-label-mono-xs text-label-mono-xs text-on-surface-variant">
            Showing <span className="font-semibold text-on-surface tabular-nums">{(page - 1) * PAGE_SIZE + 1} - {Math.min(page * PAGE_SIZE, filtered.length)}</span> of{' '}
            <span className="font-semibold text-on-surface tabular-nums">{filtered.length}</span> filtered exceptions
          </div>
          <div className="flex items-center gap-1">
            <button
              disabled={page === 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-2 py-1 rounded bg-surface-container-lowest border border-outline-variant/60 text-xs text-on-surface-variant disabled:opacity-50 disabled:cursor-not-allowed hover:bg-surface-container"
              type="button"
            >
              Previous
            </button>
            <span className="px-2 font-mono text-xs text-on-surface font-semibold tabular-nums">Page {page} of {pageCount}</span>
            <button
              disabled={page === pageCount}
              onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
              className="px-2 py-1 rounded bg-surface-container-lowest hover:bg-surface-container border border-outline-variant text-xs text-on-surface disabled:opacity-50 disabled:cursor-not-allowed"
              type="button"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
