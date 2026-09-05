import React, { useState, useEffect } from 'react';

interface ReconcileProgressModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
}

export const ReconcileProgressModal: React.FC<ReconcileProgressModalProps> = ({
  isOpen,
  onClose,
  onComplete
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isFinished, setIsFinished] = useState(false);

  const steps = [
    {
      title: 'Ingesting Telemetry Feeds',
      desc: 'Polling HDFC Bank Host-to-Host, Razorpay Webhook Nodal, and SAP RFC...',
      detail: '12,482 total records parsed'
    },
    {
      title: 'Tier 1: Bilateral UTR Exact Match',
      desc: 'Checking 1:1 string equality and deduplicating settlement rows...',
      detail: '10,784 records auto-settled (100% confidence)'
    },
    {
      title: 'Tier 2: Deterministic Rule & Fuzzy Jitter',
      desc: 'Applying ±180s timestamp jitter window and MDR gateway fee tolerance...',
      detail: '1,110 records auto-settled (≥75% confidence)'
    },
    {
      title: 'Tier 3: AI Inference & Subset-Sum Grouping',
      desc: 'Evaluating counterparty aliases, PAN matching, and split payment clusters...',
      detail: '550 records auto-settled (75%–94% confidence)'
    },
    {
      title: 'Tier 4 & 5: Exception Quarantine & HMAC-SHA256 Signing',
      desc: 'Routing 38 residual breaks to worklist queue and sealing ledger invariant block...',
      detail: 'Block #BLK-8492 cryptographically signed'
    }
  ];

  useEffect(() => {
    if (!isOpen) {
      setCurrentStep(0);
      setIsFinished(false);
      return;
    }

    let step = 0;
    const interval = setInterval(() => {
      step += 1;
      if (step < steps.length) {
        setCurrentStep(step);
      } else {
        clearInterval(interval);
        setIsFinished(true);
      }
    }, 600);

    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/60 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg bg-surface-container-lowest rounded-xl shadow-2xl border border-outline-variant overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-surface-container-low border-b border-outline-variant flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className={`material-symbols-outlined text-secondary text-xl ${!isFinished ? 'animate-spin' : ''}`}>
              {isFinished ? 'check_circle' : 'autorenew'}
            </span>
            <div>
              <h3 className="font-headline-sm text-sm font-semibold text-on-surface">
                {isFinished ? 'Reconciliation Complete' : 'Executing Batch #8492 Engine Pipeline'}
              </h3>
              <p className="text-[11px] font-mono text-on-surface-variant">
                Autonomous 5-Tier Reconciliation Engine · FIN-OPS v2.4
              </p>
            </div>
          </div>
          {isFinished && (
            <button onClick={onClose} className="p-1 rounded text-on-surface-variant hover:text-on-surface">
              <span className="material-symbols-outlined text-lg">close</span>
            </button>
          )}
        </div>

        {/* Pipeline Step Progress */}
        <div className="p-5 space-y-4">
          <div className="space-y-3">
            {steps.map((s, idx) => {
              const isCompleted = idx < currentStep || isFinished;
              const isCurrent = idx === currentStep && !isFinished;

              return (
                <div key={idx} className="flex items-start gap-3 text-xs">
                  <div className="mt-0.5 shrink-0">
                    {isCompleted ? (
                      <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs">
                        <span className="material-symbols-outlined text-sm">check</span>
                      </span>
                    ) : isCurrent ? (
                      <span className="w-5 h-5 rounded-full bg-secondary-fixed text-secondary flex items-center justify-center font-bold text-xs animate-pulse">
                        <span className="w-2 h-2 rounded-full bg-secondary"></span>
                      </span>
                    ) : (
                      <span className="w-5 h-5 rounded-full bg-surface-container text-outline-variant flex items-center justify-center text-[10px] font-mono">
                        {idx + 1}
                      </span>
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className={`font-semibold ${isCompleted ? 'text-on-surface' : isCurrent ? 'text-secondary' : 'text-outline'}`}>
                        {s.title}
                      </span>
                      {isCompleted && (
                        <span className="font-mono text-[10px] text-emerald-800 font-semibold bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
                          {s.detail}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-on-surface-variant mt-0.5">{s.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Final Summary Card when done */}
          {isFinished && (
            <div className="p-3 bg-surface-container-low rounded-lg border border-outline-variant space-y-2 animate-in fade-in">
              <div className="text-xs font-semibold text-on-surface flex items-center justify-between">
                <span>Batch #8492 Metric Verification:</span>
                <span className="text-emerald-700 font-mono">97.42% Match Rate</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="bg-surface-container-lowest p-2 rounded border border-outline-variant/60">
                  <div className="text-[10px] text-on-surface-variant uppercase font-mono">Auto-Settled</div>
                  <div className="font-semibold text-on-surface mt-0.5 font-mono">12,444 txns</div>
                </div>
                <div className="bg-surface-container-lowest p-2 rounded border border-outline-variant/60">
                  <div className="text-[10px] text-on-surface-variant uppercase font-mono">Reconciled ₹</div>
                  <div className="font-semibold text-secondary mt-0.5 font-mono">₹48.92 Cr</div>
                </div>
                <div className="bg-surface-container-lowest p-2 rounded border border-outline-variant/60">
                  <div className="text-[10px] text-on-surface-variant uppercase font-mono">Quarantined</div>
                  <div className="font-semibold text-error mt-0.5 font-mono">38 breaks</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-3 bg-surface-container-low border-t border-outline-variant flex items-center justify-between">
          <span className="text-[10px] font-mono text-on-surface-variant">
            {isFinished ? 'Execution time: 3.84s · SLA Passed' : 'Processing candidate pairs...'}
          </span>
          {isFinished ? (
            <button
              onClick={() => {
                onClose();
                onComplete();
              }}
              className="px-4 py-1.5 bg-primary text-white text-xs font-semibold rounded hover:bg-neutral-800 transition-colors shadow-xs"
            >
              Done &amp; View Results
            </button>
          ) : (
            <span className="text-xs text-secondary font-mono animate-pulse font-medium">Running...</span>
          )}
        </div>
      </div>
    </div>
  );
};
