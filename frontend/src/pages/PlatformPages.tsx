import React from 'react';
import { CONNECTED_FEEDS, SYSTEM_METRICS } from '../data/mockData';

export const DataSourcesPage: React.FC = () => {
  return (
    <div className="p-spacing-xl space-y-spacing-lg max-w-[1680px] mx-auto w-full">
      <div className="bg-surface-container-lowest rounded-lg p-spacing-lg border border-outline-variant shadow-xs">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-headline-lg text-headline-lg font-semibold text-on-surface">Connected Data Ingestion Feeds</h1>
            <p className="text-body-sm text-on-surface-variant mt-1">Manage core banking API connections, payment gateways, and ERP general ledger adapters.</p>
          </div>
          <button className="h-8 px-4 bg-primary text-white text-xs font-semibold rounded hover:bg-neutral-800 transition-colors flex items-center gap-1.5">
            <span className="material-symbols-outlined text-sm">add</span>
            <span>Connect Ingestion Source</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {CONNECTED_FEEDS.map(f => (
          <div key={f.id} className="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 space-y-3 shadow-xs">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded bg-surface-container-low border border-outline-variant flex items-center justify-center text-secondary">
                <span className="material-symbols-outlined text-xl">{f.icon}</span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Active
              </span>
            </div>
            <div>
              <h3 className="font-semibold text-sm text-on-surface">{f.name}</h3>
              <p className="text-xs text-on-surface-variant mt-0.5">{f.type}</p>
            </div>
            <div className="pt-2 border-t border-outline-variant/60 font-mono text-[11px] text-on-surface-variant space-y-1">
              <div>Sync Status: <span className="text-on-surface font-semibold">{f.lastSync}</span></div>
              <div>Batch Payload: <span className="text-on-surface">{f.batchInfo}</span></div>
              <div>Current Volume: <span className="text-secondary font-semibold">{f.volumeLabel}</span></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export const ReconciliationRulesPage: React.FC = () => {
  const rules = [
    {
      id: 'RULE-EXACT-HASH-01',
      tier: 'Tier 1',
      name: 'Bilateral UTR Exact Match',
      formula: 'Bank.UTR == Gateway.Settlement_UTR && Delta(Amount) == 0.00',
      action: 'Auto-Settled',
      confidence: '1.00 (100%)',
      status: 'Active'
    },
    {
      id: 'RULE-FUZZY-JITTER-02',
      tier: 'Tier 2',
      name: 'Timestamp Jitter Window (±180s) + Gateway MDR Fee Offset',
      formula: 'DateDiff <= 180s && Abs(Bank.Amount - (Gateway.Gross - Fee)) <= 1.00',
      action: 'Auto-Settled',
      confidence: '>= 0.75 (75%)',
      status: 'Active'
    },
    {
      id: 'RULE-AI-SUBSET-SUM-03',
      tier: 'Tier 3',
      name: 'AI Alias Resolution & Multi-Invoice Split Aggregation',
      formula: 'SemanticVendorMatch(GSTIN, EntityName) >= 0.75 && SubsetSum == Bank.Credit',
      action: 'Auto-Settled',
      confidence: '0.75 - 0.94',
      status: 'Active'
    },
    {
      id: 'RULE-EXCEPTION-ROUTE-04',
      tier: 'Tier 4',
      name: 'Unmatched Break Quarantine',
      formula: 'MatchScore < 0.75 || UnresolvedVariance > 0.00',
      action: 'Route to Exceptions Queue',
      confidence: 'Review Req.',
      status: 'Active'
    }
  ];

  return (
    <div className="p-spacing-xl space-y-spacing-lg max-w-[1680px] mx-auto w-full">
      <div className="bg-surface-container-lowest rounded-lg p-spacing-lg border border-outline-variant shadow-xs">
        <h1 className="font-headline-lg text-headline-lg font-semibold text-on-surface">Reconciliation Rules &amp; Tier Policy Cascade</h1>
        <p className="text-body-sm text-on-surface-variant mt-1">
          Deterministic 5-tier matching heuristics configured with single confidence cut-off at {SYSTEM_METRICS.confidenceThreshold * 100}%.
        </p>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden shadow-xs">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="h-8 bg-surface-container-low border-b border-outline-variant uppercase text-on-surface-variant font-semibold text-[11px]">
              <th className="px-3 py-1">Rule ID</th>
              <th className="px-3 py-1">Tier</th>
              <th className="px-3 py-1">Rule Name</th>
              <th className="px-3 py-1">Evaluation Invariant Formula</th>
              <th className="px-3 py-1">Resolution Action</th>
              <th className="px-3 py-1 text-center">Confidence</th>
              <th className="px-3 py-1 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/60">
            {rules.map(r => (
              <tr key={r.id} className="h-11 hover:bg-surface-container-low/60 transition-colors">
                <td className="px-3 py-2 font-mono font-semibold text-secondary">{r.id}</td>
                <td className="px-3 py-2 font-semibold text-on-surface">{r.tier}</td>
                <td className="px-3 py-2 font-medium text-on-surface">{r.name}</td>
                <td className="px-3 py-2 font-mono text-[11px] text-on-surface-variant">{r.formula}</td>
                <td className="px-3 py-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                    r.action.includes('Auto') ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-red-50 text-red-800 border border-red-200'
                  }`}>
                    {r.action}
                  </span>
                </td>
                <td className="px-3 py-2 text-center font-mono font-semibold text-on-surface">{r.confidence}</td>
                <td className="px-3 py-2 text-right">
                  <span className="text-emerald-700 font-semibold text-xs flex items-center justify-end gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Active
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export const SettingsPage: React.FC = () => {
  return (
    <div className="p-spacing-xl space-y-spacing-lg max-w-4xl mx-auto w-full">
      <div className="bg-surface-container-lowest rounded-lg p-spacing-lg border border-outline-variant shadow-xs">
        <h1 className="font-headline-lg text-headline-lg font-semibold text-on-surface">Platform Settings &amp; Governance</h1>
        <p className="text-body-sm text-on-surface-variant mt-1">Configure global reconciliation thresholds, fiscal calendar periods, and cryptographic audit parameters.</p>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 space-y-4 shadow-xs text-xs">
        <div className="space-y-1">
          <label className="font-semibold text-on-surface block">AI Discretion Confidence Threshold</label>
          <div className="flex items-center gap-3">
            <input type="range" min="50" max="95" defaultValue="75" className="w-64 accent-secondary" />
            <span className="font-mono font-semibold text-secondary text-sm">75% (0.75)</span>
          </div>
          <p className="text-[11px] text-on-surface-variant">Matches scored below 0.75 are automatically quarantined to the Exceptions Queue.</p>
        </div>

        <div className="pt-3 border-t border-outline-variant space-y-1">
          <label className="font-semibold text-on-surface block">Cryptographic Log Signing Key (HMAC-SHA256)</label>
          <div className="flex items-center gap-2">
            <code className="bg-surface-container-low px-2 py-1 rounded border border-outline-variant font-mono text-[11px] text-on-surface flex-1">
              hsm_sec_2024_acme_ledger_finops_master_key_sig
            </code>
            <button className="px-3 py-1 bg-surface-container border border-outline-variant rounded hover:bg-surface-container-high font-medium">
              Rotate Key
            </button>
          </div>
        </div>

        <div className="pt-3 border-t border-outline-variant space-y-1">
          <label className="font-semibold text-on-surface block">Default Fiscal Period Close Window</label>
          <select className="h-8 pl-2 pr-8 rounded bg-surface-container-low border border-outline-variant font-mono text-xs">
            <option>Monthly Close (Calendar Month End)</option>
            <option>Bi-weekly Rolling Close</option>
            <option>Continuous T+1 Reconciliation</option>
          </select>
        </div>
      </div>
    </div>
  );
};
