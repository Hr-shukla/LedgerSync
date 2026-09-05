import React from 'react';

interface ComplianceModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ComplianceModal: React.FC<ComplianceModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const checklistItems = [
    {
      title: 'Bilateral Invariant Enforcement',
      desc: 'All bank credits and settlement reports validated with 0.00 rupee discrepancy threshold.',
      status: 'VERIFIED',
      date: '2024-10-31 23:59:58 IST'
    },
    {
      title: 'Cryptographic Chain of Custody (HMAC-SHA256)',
      desc: 'Immutable audit log blocks hashed and signed in sequence with hardware tamper protection.',
      status: 'VERIFIED',
      date: 'Continuous Telemetry'
    },
    {
      title: 'Threshold-Enforced AI Discretion Boundary',
      desc: 'No autonomous ledger modification permitted under the 75% (0.75) confidence cut-off.',
      status: 'VERIFIED',
      date: 'Policy Config Active'
    },
    {
      title: 'General Ledger Segregation of Duties',
      desc: 'Controller approvals for exception overrides cryptographically logged with user identity.',
      status: 'VERIFIED',
      date: 'October Close Active'
    },
    {
      title: 'Archival & Record Retention Invariant',
      desc: 'Full historical transaction logs preserved in immutable append-only storage.',
      status: 'VERIFIED',
      date: 'Policy Compliant'
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/50 backdrop-blur-xs p-4">
      <div className="w-full max-w-xl bg-surface-container-lowest rounded-xl shadow-2xl border border-outline-variant overflow-hidden">
        <div className="p-4 border-b border-outline-variant flex items-center justify-between bg-surface-container-low">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-xl">verified_user</span>
            <div>
              <h3 className="font-headline-sm text-sm font-semibold text-on-surface">
                Internal Audit &amp; Compliance Checklist
              </h3>
              <p className="text-[11px] text-on-surface-variant">
                Internal Governance &amp; Immutable Financial Controls Attestation
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface p-1 rounded"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        <div className="p-4 space-y-3">
          <div className="text-xs text-on-surface-variant leading-relaxed">
            All system runs, decision heuristics, and exception resolutions are cryptographically tracked under internal audit rules.
          </div>

          <div className="space-y-2">
            {checklistItems.map((item, idx) => (
              <div key={idx} className="p-2.5 rounded border border-outline-variant/60 bg-surface-container-low/40 flex items-start justify-between gap-3">
                <div className="space-y-0.5">
                  <div className="font-medium text-xs text-on-surface flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
                    <span>{item.title}</span>
                  </div>
                  <div className="text-[11px] text-on-surface-variant">{item.desc}</div>
                  <div className="text-[10px] font-mono text-outline">{item.date}</div>
                </div>
                <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="p-3 border-t border-outline-variant bg-surface-container-low flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-primary text-on-primary rounded text-xs font-medium hover:bg-neutral-800 transition-colors shadow-xs"
          >
            Acknowledge Checklist
          </button>
        </div>
      </div>
    </div>
  );
};
