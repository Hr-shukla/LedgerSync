import React from 'react';
import { SYSTEM_METRICS, CONNECTED_FEEDS } from '../../data/mockData';

interface ExecutiveSummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ExecutiveSummaryModal: React.FC<ExecutiveSummaryModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="w-full max-w-3xl bg-surface-container-lowest rounded-xl shadow-2xl border border-outline-variant overflow-hidden flex flex-col my-8">
        {/* Header */}
        <div className="p-4 bg-surface-container-low border-b border-outline-variant flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-xl">description</span>
            <div>
              <h3 className="font-headline-sm text-sm font-semibold text-on-surface">
                Executive Financial Reconciliation Summary
              </h3>
              <p className="text-[11px] font-mono text-on-surface-variant">
                Period: October 1–31, 2024 · Cycle 2024-M10 · Entity: Acme India Pvt Ltd
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="px-2.5 py-1 bg-surface-container-lowest border border-outline-variant rounded text-xs text-on-surface hover:bg-surface-container flex items-center gap-1 font-medium"
            >
              <span className="material-symbols-outlined text-[14px]">print</span>
              <span>Print</span>
            </button>
            <button onClick={onClose} className="p-1 rounded text-on-surface-variant hover:text-on-surface">
              <span className="material-symbols-outlined text-lg">close</span>
            </button>
          </div>
        </div>

        {/* Report Content */}
        <div className="p-6 space-y-5 text-xs text-on-surface max-h-[75vh] overflow-y-auto">
          {/* Executive Overview Box */}
          <div className="p-4 bg-surface-container-low rounded-lg border border-outline-variant space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sm text-on-surface">Financial Close Health: Invariant Verified</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                97.42% Match Rate
              </span>
            </div>
            <p className="text-on-surface-variant leading-relaxed text-xs">
              For the fiscal cycle ending October 31, 2024, LedgerSync successfully ingested and cross-matched three primary sources: HDFC Corporate Current Account (Host-to-Host direct API), Razorpay Payment Gateway Settlement Nodal Accounts, and the SAP ERP General Ledger. Total processed volume reached ₹50,21,80,000 across 12,482 transactions.
            </p>
          </div>

          {/* Key Metric Highlights */}
          <div className="grid grid-cols-4 gap-3">
            <div className="p-3 bg-surface-container-low/60 rounded border border-outline-variant/60">
              <div className="text-[10px] text-on-surface-variant uppercase font-mono">Gross Ingestion Volume</div>
              <div className="font-semibold text-sm text-on-surface mt-0.5 font-mono">₹50,21,80,000</div>
              <div className="text-[10px] text-on-surface-variant mt-1">12,482 records</div>
            </div>
            <div className="p-3 bg-surface-container-low/60 rounded border border-outline-variant/60">
              <div className="text-[10px] text-on-surface-variant uppercase font-mono">Reconciled Volume</div>
              <div className="font-semibold text-sm text-secondary mt-0.5 font-mono">₹48,92,40,150</div>
              <div className="text-[10px] text-emerald-700 font-semibold mt-1">97.42% auto-settled</div>
            </div>
            <div className="p-3 bg-surface-container-low/60 rounded border border-outline-variant/60">
              <div className="text-[10px] text-on-surface-variant uppercase font-mono">Value at Risk</div>
              <div className="font-semibold text-sm text-error mt-0.5 font-mono">₹1,29,39,850</div>
              <div className="text-[10px] text-error font-semibold mt-1">0.26% of gross</div>
            </div>
            <div className="p-3 bg-surface-container-low/60 rounded border border-outline-variant/60">
              <div className="text-[10px] text-on-surface-variant uppercase font-mono">Open Exceptions</div>
              <div className="font-semibold text-sm text-on-surface mt-0.5 font-mono">38 items</div>
              <div className="text-[10px] text-amber-700 font-semibold mt-1">Under controller review</div>
            </div>
          </div>

          {/* Tier Distribution Table */}
          <div className="space-y-2">
            <h4 className="font-semibold text-xs text-on-surface uppercase tracking-wider">
              Resolution Distribution by Tier
            </h4>
            <div className="border border-outline-variant rounded overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-low border-b border-outline-variant text-[10px] uppercase text-on-surface-variant font-mono">
                    <th className="p-2">Tier Level</th>
                    <th className="p-2 text-right">Transactions</th>
                    <th className="p-2 text-right">Amount (INR)</th>
                    <th className="p-2 text-center">Confidence</th>
                    <th className="p-2 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/60 font-mono text-xs">
                  {SYSTEM_METRICS.tiers.map(t => (
                    <tr key={t.id} className="hover:bg-surface-container-low/40">
                      <td className="p-2 font-sans font-medium text-on-surface">{t.name}</td>
                      <td className="p-2 text-right">{t.records.toLocaleString('en-IN')}</td>
                      <td className="p-2 text-right font-semibold">₹{t.settledAmountINR.toLocaleString('en-IN')}</td>
                      <td className="p-2 text-center">{t.confidenceLabel}</td>
                      <td className="p-2 text-right">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                          t.id === 'tier4_exceptions' ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'
                        }`}>
                          {t.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Ingestion Feed Health */}
          <div className="space-y-2">
            <h4 className="font-semibold text-xs text-on-surface uppercase tracking-wider">
              Connected Source Telemetry
            </h4>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {CONNECTED_FEEDS.map(f => (
                <div key={f.id} className="p-2.5 bg-surface-container-low rounded border border-outline-variant">
                  <div className="font-semibold text-on-surface">{f.name}</div>
                  <div className="text-[11px] text-on-surface-variant mt-0.5">{f.volumeLabel}</div>
                  <div className="text-[10px] text-emerald-700 font-mono mt-1">● Synced &amp; Healthy</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-surface-container-low border-t border-outline-variant flex items-center justify-between">
          <span className="text-[10px] font-mono text-on-surface-variant">
            Cryptographically certified under internal financial governance · LedgerSync v2.4
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-primary text-white text-xs font-semibold rounded hover:bg-neutral-800 transition-colors shadow-xs"
          >
            Close Report
          </button>
        </div>
      </div>
    </div>
  );
};
