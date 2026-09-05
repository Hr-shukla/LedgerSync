import React, { useState } from 'react';
import { getAuditLog } from '../lib/api';
import { useApiData } from '../hooks/useApiData';
import { RunHistoryEntry } from '../types';
import { CopyButton } from '../components/common/CopyButton';
import { LoadingState, ErrorState, EmptyState } from '../components/common/AsyncState';
import { useToast } from '../components/common/ToastContext';

export const AuditLogPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRun, setSelectedRun] = useState<RunHistoryEntry | null>(null);
  const { addToast } = useToast();

  const { data, loading, error, reload } = useApiData(() => getAuditLog(100), []);
  const runs = data?.runs ?? [];

  const filteredRuns = runs.filter((r) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    return String(r.seed).includes(q) || (r.ai_provider ?? '').toLowerCase().includes(q) || r.run_at.toLowerCase().includes(q);
  });

  const activeRun = selectedRun ?? filteredRuns[0] ?? null;

  const handleDownloadJson = () => {
    const blob = new Blob([JSON.stringify(runs, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'audit_run_history.json';
    a.click();
    URL.revokeObjectURL(url);
    addToast({ type: 'success', title: `Downloaded ${runs.length} run(s) as JSON` });
  };

  if (loading) return <LoadingState label="Loading run history..." />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div className="flex flex-col w-full min-h-[calc(100vh-56px)] bg-surface pb-12">
      {/* Top Context Header & Actions Strip */}
      <div className="px-spacing-xl pt-spacing-lg pb-spacing-base bg-surface-container-lowest border-b border-outline-variant">
        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-spacing-md">
          <div>
            <h1 className="font-headline-lg text-headline-lg text-on-surface font-semibold tracking-tight">
              Reconciliation Run Log &amp; Audit Trail
            </h1>
            <p className="font-body-default text-body-default text-on-surface-variant mt-0.5">
              One entry per `run_reconciliation.py` invocation, read from output/run_history.jsonl
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-spacing-xs">
            <button
              onClick={handleDownloadJson}
              className="h-8 px-spacing-md bg-primary hover:bg-neutral-800 text-on-primary rounded font-body-medium text-body-medium flex items-center gap-spacing-xs transition-colors shadow-xs text-xs font-semibold active:scale-[0.98]"
              type="button"
            >
              <span className="material-symbols-outlined text-[16px]">data_object</span>
              <span>Download Run History (JSON)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Summary Metrics Strip */}
      <div className="px-spacing-xl py-spacing-md bg-slate-50/80 border-b border-outline-variant/60">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-spacing-base">
          <div className="bg-surface-container-lowest p-spacing-base rounded-lg border border-slate-200/80 shadow-xs">
            <div className="font-body-sm text-body-sm text-slate-600 font-medium">Total Runs Logged</div>
            <div className="mt-spacing-sm font-metric-display text-metric-display text-on-surface tabular-nums font-bold">{runs.length}</div>
          </div>
          <div className="bg-surface-container-lowest p-spacing-base rounded-lg border border-slate-200/80 shadow-xs">
            <div className="font-body-sm text-body-sm text-slate-600 font-medium">Latest Match Rate</div>
            <div className="mt-spacing-sm font-metric-display text-metric-display text-on-surface tabular-nums font-bold">
              {runs[0]?.match_rate_pct ?? '--'}%
            </div>
          </div>
          <div className="bg-surface-container-lowest p-spacing-base rounded-lg border border-slate-200/80 shadow-xs">
            <div className="font-body-sm text-body-sm text-slate-600 font-medium">Latest Precision / Recall</div>
            <div className="mt-spacing-sm font-metric-display text-metric-display text-on-surface tabular-nums font-bold">
              {runs[0] ? `${runs[0].precision_pct}% / ${runs[0].recall_pct}%` : '--'}
            </div>
          </div>
          <div className="bg-surface-container-lowest p-spacing-base rounded-lg border border-slate-200/80 shadow-xs">
            <div className="font-body-sm text-body-sm text-slate-600 font-medium">Latest Open Exceptions</div>
            <div className="mt-spacing-sm font-metric-display text-metric-display text-error tabular-nums font-bold">
              {runs[0]?.exceptions_count ?? '--'}
            </div>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="px-spacing-xl py-spacing-sm bg-surface-container-lowest border-b border-outline-variant">
        <div className="relative max-w-xl">
          <span className="material-symbols-outlined absolute left-spacing-sm text-slate-400 text-[18px] ml-2.5">search</span>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-8 pl-9 pr-10 text-body-sm font-body-sm bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-secondary text-slate-900 placeholder:text-slate-400 shadow-2xs"
            placeholder="Search by seed, AI provider..."
            type="text"
          />
        </div>
      </div>

      {/* Main Table */}
      <div className="px-spacing-xl py-spacing-md">
        {filteredRuns.length === 0 ? (
          <EmptyState icon="history" title="No runs match your search" />
        ) : (
          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="h-8 bg-slate-50 border-b border-outline-variant font-body-xs text-body-xs text-slate-500 uppercase font-semibold">
                    <th className="px-3 py-1">Run</th>
                    <th className="px-3 py-1">Timestamp</th>
                    <th className="px-3 py-1 text-right">Match Rate</th>
                    <th className="px-3 py-1 text-right">Precision</th>
                    <th className="px-3 py-1 text-right">Recall</th>
                    <th className="px-3 py-1 text-right">False-Match</th>
                    <th className="px-3 py-1 text-right">Exceptions</th>
                    <th className="px-3 py-1 text-right">Tier 4</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/60 font-body-sm text-body-sm">
                  {filteredRuns.map((run, i) => {
                    const isSelected = activeRun?.run_at === run.run_at;
                    return (
                      <tr
                        key={run.run_at}
                        onClick={() => setSelectedRun(run)}
                        className={`h-11 transition-colors cursor-pointer ${isSelected ? 'bg-sky-50/50 border-l-[3px] border-l-secondary' : 'hover:bg-slate-50/70'}`}
                      >
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-secondary"></span>
                            <span className="font-mono text-xs font-bold text-secondary">Run #{filteredRuns.length - i}</span>
                            <CopyButton text={run.run_at} />
                          </div>
                          <div className="text-[11px] text-slate-500 ml-3.5">seed {run.seed}</div>
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-slate-500 tabular-nums">{new Date(run.run_at).toLocaleString()}</td>
                        <td className="px-3 py-2 text-right font-mono text-xs font-bold tabular-nums text-slate-900">{run.match_rate_pct}%</td>
                        <td className="px-3 py-2 text-right font-mono text-xs tabular-nums text-slate-700">{run.precision_pct}%</td>
                        <td className="px-3 py-2 text-right font-mono text-xs tabular-nums text-slate-700">{run.recall_pct}%</td>
                        <td className="px-3 py-2 text-right font-mono text-xs tabular-nums text-slate-700">{run.false_match_rate_pct}%</td>
                        <td className="px-3 py-2 text-right font-mono text-xs tabular-nums text-error font-semibold">{run.exceptions_count}</td>
                        <td className="px-3 py-2 text-right">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            {run.ai_available ? run.ai_provider : 'disabled'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="px-spacing-md py-2 bg-slate-50 flex items-center justify-between border-t border-outline-variant">
              <span className="font-body-xs text-body-xs text-slate-500">
                Showing <strong className="text-slate-900 font-semibold tabular-nums">{filteredRuns.length}</strong> of{' '}
                <strong className="text-slate-900 font-semibold tabular-nums">{runs.length}</strong> logged runs
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Selected Run Detail */}
      {activeRun && (
        <div className="px-spacing-xl pb-spacing-md">
          <div className="bg-surface-container-lowest rounded-lg border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs font-bold text-secondary">{new Date(activeRun.run_at).toLocaleString()}</span>
                <span className="font-semibold text-xs text-slate-900">seed {activeRun.seed} run detail</span>
              </div>
              <CopyButton text={JSON.stringify(activeRun, null, 2)} label="Copy JSON" />
            </div>
            <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
                <div className="text-slate-500 text-[11px] font-semibold uppercase font-mono">Reconciled Value</div>
                <div className="font-mono font-bold text-slate-900 text-sm mt-0.5">
                  &#8377;{activeRun.reconciled_value_rupees.toLocaleString('en-IN')}
                </div>
                <div className="text-slate-600 text-[11px] mt-1 font-mono">
                  of &#8377;{activeRun.total_value_rupees.toLocaleString('en-IN')} total
                </div>
              </div>
              <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
                <div className="text-slate-500 text-[11px] font-semibold uppercase font-mono">Grading vs Ground Truth</div>
                <div className="font-mono font-bold text-slate-900 text-sm mt-0.5">
                  P {activeRun.precision_pct}% / R {activeRun.recall_pct}%
                </div>
                <div className="text-emerald-700 text-[11px] mt-1 font-mono font-semibold">
                  False-match rate: {activeRun.false_match_rate_pct}%
                </div>
              </div>
              <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
                <div className="text-slate-500 text-[11px] font-semibold uppercase font-mono">Tier 4 (AI-Assisted Resolution)</div>
                <div className="font-mono font-bold text-slate-900 text-sm mt-0.5">
                  {activeRun.ai_available ? activeRun.ai_provider : 'Not configured'}
                </div>
                <div className="text-slate-600 text-[11px] mt-1 font-mono">
                  {activeRun.ai_available ? 'Live LLM calls enabled for this run' : 'Deterministic tiers only'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
