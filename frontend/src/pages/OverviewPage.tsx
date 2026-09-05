import React, { useState } from 'react';
import { getOverview, getAuditLog, runReconcile, ApiError } from '../lib/api';
import { useApiData } from '../hooks/useApiData';
import { NavPage } from '../components/layout/Sidebar';
import { CopyButton } from '../components/common/CopyButton';
import { LoadingState, ErrorState } from '../components/common/AsyncState';
import { useToast } from '../components/common/ToastContext';
import { OverviewData, RunHistoryEntry } from '../types';

interface OverviewPageProps {
  onNavigate: (page: NavPage) => void;
}

const TIER_LABELS: Record<string, { name: string; description: string; color: string }> = {
  tier1_exact: { name: 'Tier 1: Exact Reference Match', description: 'Bank UTR == settlement UTR, string equality', color: '#0F172A' },
  tier1_exact_grouped: { name: 'Tier 1: Exact Match (Grouped)', description: 'Exact UTR match spanning multiple bank/settlement rows', color: '#0F172A' },
  tier2_fuzzy: { name: 'Tier 2: Deterministic Fuzzy Match', description: 'Fuzzy reference + amount/date tolerance', color: '#006398' },
  tier3_grouping: { name: 'Tier 3: Subset-Sum Grouping', description: 'Aggregated/split settlements, partial payments', color: '#5bb8fe' },
  tier4_ai: { name: 'Tier 4: AI-Assisted Resolution', description: 'LLM-resolved ambiguous candidate', color: '#7c3aed' },
};

function formatINR(n: number): string {
  return `₹${Math.round(n).toLocaleString('en-IN')}`;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ onNavigate }) => {
  const [hoveredTier, setHoveredTier] = useState<string | null>(null);
  const [isReconciling, setIsReconciling] = useState(false);
  const { addToast } = useToast();
  const { data: overview, loading: overviewLoading, error: overviewError, reload: reloadOverview } =
    useApiData<OverviewData>(getOverview, []);
  const { data: auditLog, loading: runsLoading, error: runsError, reload: reloadAuditLog } =
    useApiData(() => getAuditLog(4), []);

  const handleRunReconcile = async () => {
    setIsReconciling(true);
    try {
      await runReconcile();
      addToast({ type: 'success', title: 'Reconciliation complete', message: 'Pipeline re-ran against the current dataset.' });
      reloadOverview();
      reloadAuditLog();
    } catch (e) {
      addToast({
        type: 'error',
        title: 'Reconciliation run failed',
        message: e instanceof ApiError ? e.message : 'Unknown error',
      });
    } finally {
      setIsReconciling(false);
    }
  };

  if (overviewLoading) return <LoadingState label="Loading reconciliation overview..." />;
  if (overviewError || !overview) return <ErrorState message={overviewError || 'No data returned'} onRetry={reloadOverview} />;

  const tierEntries = Object.entries(overview.tier_breakdown);
  const matchedGroupTotal = tierEntries.reduce((sum, [, count]) => sum + count, 0);
  const recentRuns: RunHistoryEntry[] = auditLog?.runs ?? [];
  const valueAtRiskPct = overview.total_value_rupees > 0
    ? (overview.value_at_risk_rupees / overview.total_value_rupees) * 100
    : 0;

  return (
    <div className="p-spacing-xl space-y-spacing-xl max-w-[1680px] mx-auto w-full">
      {/* Top Section: Header & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-spacing-md bg-surface-container-lowest p-spacing-lg rounded-lg border border-outline-variant shadow-xs">
        <div className="flex flex-col">
          <h1 className="font-headline-lg text-headline-lg text-on-surface tracking-tight font-semibold">
            Reconciliation Overview
          </h1>
          <p className="font-body-default text-body-default text-on-surface-variant mt-spacing-2xs flex items-center gap-spacing-xs flex-wrap">
            <span className="inline-flex items-center gap-1.5 text-secondary font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
              {overview.ai_available ? `Tier 4 AI enabled (${overview.ai_provider})` : 'Tier 4 AI not configured -- deterministic tiers only'}
            </span>
          </p>
        </div>

        <div className="flex items-center gap-spacing-sm flex-wrap">
          <button
            disabled
            title="Not wired to a backend endpoint -- there is no live report generator behind this button yet, so it stays disabled rather than showing fabricated figures."
            className="h-8 px-spacing-md border border-outline-variant rounded text-on-surface-variant bg-surface-container-low font-body-medium text-body-medium flex items-center gap-spacing-xs opacity-60 cursor-not-allowed"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px]">description</span>
            <span>Export Executive Summary</span>
          </button>
          <button
            onClick={handleRunReconcile}
            disabled={isReconciling}
            title="Re-runs the real pipeline against the current dataset (~15s) -- a live Tier 4 call included, not a simulated progress bar."
            className="h-8 px-spacing-md rounded text-on-primary bg-primary hover:bg-neutral-800 font-body-medium text-body-medium flex items-center gap-spacing-xs transition-colors shadow-sm disabled:opacity-75 active:scale-[0.98]"
            type="button"
          >
            <span className={`material-symbols-outlined text-[16px] ${isReconciling ? 'animate-spin' : ''}`}>
              {isReconciling ? 'autorenew' : 'play_arrow'}
            </span>
            <span>{isReconciling ? 'Running reconciliation...' : 'Run Reconcile'}</span>
          </button>
        </div>
      </div>

      {/* Metric / KPI Cards (Row of 4) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-spacing-md">
        <div
          onClick={() => onNavigate('transactions')}
          className="bg-surface-container-lowest border border-outline-variant rounded-lg p-spacing-base flex flex-col justify-between shadow-xs hover:border-secondary transition-all cursor-pointer group"
          title="Click to view all matching transactions"
        >
          <span className="font-body-sm text-body-sm text-on-surface-variant font-medium group-hover:text-secondary transition-colors">
            Total Match Rate
          </span>
          <div className="my-spacing-sm">
            <div className="font-metric-display text-metric-display text-on-surface font-semibold tracking-tight tabular-nums">
              {overview.match_rate_pct}%
            </div>
          </div>
          <div className="flex items-center gap-spacing-xs font-label-mono-xs text-label-mono-xs text-on-surface-variant">
            Precision {overview.precision_pct}% &middot; Recall {overview.recall_pct}%
          </div>
        </div>

        <div
          onClick={() => onNavigate('transactions')}
          className="bg-surface-container-lowest border border-outline-variant rounded-lg p-spacing-base flex flex-col justify-between shadow-xs hover:border-secondary transition-all cursor-pointer group"
          title="Click to inspect reconciled transactions"
        >
          <div className="flex items-center justify-between">
            <span className="font-body-sm text-body-sm text-on-surface-variant font-medium group-hover:text-secondary transition-colors">
              Reconciled vs Total Volume
            </span>
            <span className="font-label-mono-xs text-label-mono-xs text-secondary font-semibold tabular-nums">
              {overview.reconciled_value_pct}%
            </span>
          </div>
          <div className="my-spacing-sm">
            <span className="font-metric-display text-metric-display text-on-surface font-semibold tracking-tight tabular-nums">
              {formatINR(overview.reconciled_value_rupees)}
            </span>
            <div className="font-label-mono-xs text-label-mono-xs text-on-surface-variant tabular-nums mt-0.5">
              of {formatINR(overview.total_value_rupees)} processed
            </div>
          </div>
          <div className="w-full h-1.5 bg-surface-container rounded-full overflow-hidden">
            <div className="h-full bg-secondary rounded-full transition-all duration-500" style={{ width: `${overview.reconciled_value_pct}%` }}></div>
          </div>
        </div>

        <div
          onClick={() => onNavigate('exceptions')}
          className="bg-surface-container-lowest border border-outline-variant rounded-lg p-spacing-base flex flex-col justify-between shadow-xs hover:border-error transition-all cursor-pointer group"
          title="Click to review open exceptions queue"
        >
          <span className="font-body-sm text-body-sm text-on-surface-variant font-medium group-hover:text-error transition-colors">
            Open Exceptions
          </span>
          <div className="my-spacing-sm">
            <div className="font-metric-display text-metric-display text-on-surface font-semibold tracking-tight tabular-nums">
              {overview.open_exceptions_count} <span className="font-headline-sm text-headline-sm font-normal text-on-surface-variant">records</span>
            </div>
          </div>
          <div className="font-body-xs text-body-xs text-on-surface-variant flex items-center justify-between">
            <span>Across bank, settlement &amp; ledger</span>
            <span className="text-secondary font-body-medium group-hover:underline inline-flex items-center gap-0.5 font-semibold">
              <span>Review Queue</span>
              <span className="material-symbols-outlined text-[13px]">arrow_forward</span>
            </span>
          </div>
        </div>

        <div
          onClick={() => onNavigate('exceptions')}
          className="bg-surface-container-lowest border border-outline-variant rounded-lg p-spacing-base flex flex-col justify-between shadow-xs hover:border-error transition-all cursor-pointer group"
          title="Click to resolve value at risk"
        >
          <span className="font-body-sm text-body-sm text-on-surface-variant font-medium group-hover:text-error transition-colors">
            Value at Risk
          </span>
          <div className="my-spacing-sm">
            <div className="font-metric-display text-metric-display text-error font-semibold tracking-tight tabular-nums">
              {formatINR(overview.value_at_risk_rupees)}
            </div>
          </div>
          <div className="font-body-xs text-body-xs text-on-surface-variant">
            <span className="font-label-mono-xs text-label-mono-xs font-semibold text-on-surface tabular-nums">
              {valueAtRiskPct.toFixed(2)}%
            </span>{' '}
            of gross volume
          </div>
        </div>
      </div>

      {/* Middle Section: Tier Breakdown + Real Per-Source Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-spacing-md items-start">
        <div className="lg:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-lg p-spacing-base shadow-xs space-y-spacing-base">
          <div className="border-b border-outline-variant pb-spacing-sm">
            <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold">Resolution Breakdown by Tier</h2>
            <p className="font-body-xs text-body-xs text-on-surface-variant">
              Share of matched groups resolved by each tier ({matchedGroupTotal} matched groups this run)
            </p>
          </div>

          <div className="space-y-spacing-xs">
            <div className="w-full h-3 bg-surface-container rounded-xs flex overflow-hidden">
              {tierEntries.map(([tier, count]) => {
                const pct = matchedGroupTotal > 0 ? (count / matchedGroupTotal) * 100 : 0;
                const meta = TIER_LABELS[tier] || { name: tier, description: '', color: '#94A3B8' };
                return (
                  <div
                    key={tier}
                    className={`h-full transition-opacity duration-200 ${hoveredTier && hoveredTier !== tier ? 'opacity-30' : 'opacity-100'}`}
                    style={{ width: `${pct}%`, backgroundColor: meta.color }}
                    title={`${meta.name}: ${pct.toFixed(1)}% (${count} groups)`}
                  ></div>
                );
              })}
            </div>
          </div>

          <div className="overflow-x-auto border border-outline-variant rounded">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="h-8 bg-surface-container-low border-b border-outline-variant font-body-xs text-body-xs text-on-surface-variant uppercase font-medium">
                  <th className="px-3 py-1 font-semibold">Reconciliation Tier</th>
                  <th className="px-3 py-1 font-semibold text-right">Groups</th>
                  <th className="px-3 py-1 font-semibold text-center">Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/60 font-body-sm text-body-sm">
                {tierEntries.length === 0 && (
                  <tr><td colSpan={3} className="px-3 py-4 text-center text-on-surface-variant font-body-xs text-body-xs">No matched groups yet</td></tr>
                )}
                {tierEntries.map(([tier, count]) => {
                  const meta = TIER_LABELS[tier] || { name: tier, description: '', color: '#94A3B8' };
                  const pct = matchedGroupTotal > 0 ? (count / matchedGroupTotal) * 100 : 0;
                  return (
                    <tr
                      key={tier}
                      onMouseEnter={() => setHoveredTier(tier)}
                      onMouseLeave={() => setHoveredTier(null)}
                      className={`h-10 transition-colors ${hoveredTier === tier ? 'bg-secondary-fixed/30' : 'hover:bg-surface-container-low/60'}`}
                    >
                      <td className="px-3 py-1.5">
                        <div className="flex flex-col">
                          <span className="font-body-medium font-semibold text-on-surface">{meta.name}</span>
                          <span className="font-body-xs text-body-xs text-on-surface-variant">{meta.description}</span>
                        </div>
                      </td>
                      <td className="px-3 py-1.5 text-right font-label-mono-xs text-label-mono-xs tabular-nums font-semibold text-on-surface">
                        {count.toLocaleString('en-IN')}
                      </td>
                      <td className="px-3 py-1.5 text-center font-label-mono-xs text-label-mono-xs text-on-surface-variant tabular-nums">
                        {pct.toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Real per-source breakdown, replacing the mocked "Connected Feeds" panel */}
        <div className="lg:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-lg p-spacing-base shadow-xs space-y-spacing-base">
          <div className="border-b border-outline-variant pb-spacing-sm">
            <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold">Match Rate by Source</h2>
            <p className="font-body-xs text-body-xs text-on-surface-variant">Bank statement, Razorpay settlements, internal ledger</p>
          </div>

          <div className="space-y-spacing-sm">
            {(['bank', 'settlement', 'ledger'] as const).map((source) => {
              const stats = overview.per_source[source];
              const icon = source === 'bank' ? 'account_balance' : source === 'settlement' ? 'payments' : 'menu_book';
              const label = source === 'bank' ? 'Bank Statement' : source === 'settlement' ? 'Razorpay Settlements' : 'Internal Ledger';
              return (
                <div
                  key={source}
                  className="p-spacing-sm border border-outline-variant rounded bg-surface-container-low flex items-center justify-between"
                >
                  <div className="flex items-center gap-spacing-sm">
                    <div className="w-8 h-8 rounded bg-surface-container-lowest border border-outline-variant flex items-center justify-center flex-shrink-0">
                      <span className="material-symbols-outlined text-secondary text-[18px]">{icon}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="font-body-medium text-body-medium text-on-surface font-semibold">{label}</span>
                      <span className="font-label-mono-xs text-label-mono-xs text-on-surface-variant">
                        {stats.matched_records} / {stats.total_records} matched
                      </span>
                    </div>
                  </div>
                  <span className="font-label-mono-xs text-label-mono-xs px-2 py-0.5 rounded bg-surface-container-high border border-outline-variant text-on-surface tabular-nums font-semibold">
                    {stats.match_rate_pct}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Section: Recent Engine Runs */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-spacing-base shadow-xs space-y-spacing-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-spacing-xs border-b border-outline-variant pb-spacing-sm">
          <div>
            <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold">Recent Engine Runs</h2>
            <p className="font-body-xs text-body-xs text-on-surface-variant">From output/run_history.jsonl, one entry per pipeline run</p>
          </div>
          <button
            onClick={() => onNavigate('audit')}
            className="font-body-xs text-body-xs text-secondary hover:underline flex items-center gap-0.5 font-semibold"
          >
            <span>View Complete Audit Log</span>
            <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
          </button>
        </div>

        {runsLoading ? (
          <LoadingState label="Loading run history..." />
        ) : runsError ? (
          <ErrorState message={runsError} />
        ) : recentRuns.length === 0 ? (
          <div className="py-8 text-center text-body-xs text-on-surface-variant">No runs logged yet.</div>
        ) : (
          <div className="overflow-x-auto border border-outline-variant rounded">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="h-8 bg-surface-container-low border-b border-outline-variant font-body-xs text-body-xs text-on-surface-variant uppercase font-medium">
                  <th className="px-3 py-1 font-semibold">Run</th>
                  <th className="px-3 py-1 font-semibold">Timestamp</th>
                  <th className="px-3 py-1 font-semibold text-right">Match Rate</th>
                  <th className="px-3 py-1 font-semibold text-right">Precision / Recall</th>
                  <th className="px-3 py-1 font-semibold text-right">Exceptions</th>
                  <th className="px-3 py-1 font-semibold text-right">Tier 4</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/60 font-body-sm text-body-sm">
                {recentRuns.map((run, i) => (
                  <tr
                    key={run.run_at}
                    onClick={() => onNavigate('audit')}
                    className="h-11 hover:bg-surface-container-low/60 transition-colors cursor-pointer"
                  >
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-secondary"></span>
                        <span className="font-label-mono-xs text-label-mono-xs font-semibold text-on-surface">
                          Run #{recentRuns.length - i} (seed {run.seed})
                        </span>
                        <CopyButton text={run.run_at} />
                      </div>
                    </td>
                    <td className="px-3 py-2 font-label-mono-xs text-label-mono-xs text-on-surface-variant tabular-nums">
                      {new Date(run.run_at).toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right font-label-mono-xs text-label-mono-xs tabular-nums text-on-surface font-semibold">
                      {run.match_rate_pct}%
                    </td>
                    <td className="px-3 py-2 text-right font-label-mono-xs text-label-mono-xs tabular-nums text-on-surface-variant">
                      {run.precision_pct}% / {run.recall_pct}%
                    </td>
                    <td className="px-3 py-2 text-right font-label-mono-xs text-label-mono-xs tabular-nums text-error font-semibold">
                      {run.exceptions_count}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-surface-container-high border border-outline-variant text-on-surface-variant">
                        {run.ai_available ? run.ai_provider : 'disabled'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
