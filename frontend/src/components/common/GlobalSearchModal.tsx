import React, { useState, useEffect } from 'react';
import { INITIAL_TRANSACTIONS, INITIAL_EXCEPTIONS, INITIAL_AUDIT_LOGS } from '../../data/mockData';
import { NavPage } from '../layout/Sidebar';

interface GlobalSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTransaction: (id: string) => void;
  onNavigate: (page: NavPage) => void;
}

export const GlobalSearchModal: React.FC<GlobalSearchModalProps> = ({
  isOpen,
  onClose,
  onSelectTransaction,
  onNavigate
}) => {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else onClose(); // parent handles toggle
      }
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filteredTxns = INITIAL_TRANSACTIONS.filter(t => 
    t.id.toLowerCase().includes(query.toLowerCase()) ||
    t.bank.entity.toLowerCase().includes(query.toLowerCase()) ||
    t.bank.utr.toLowerCase().includes(query.toLowerCase()) ||
    t.ledger.invoiceRef.toLowerCase().includes(query.toLowerCase())
  );

  const filteredExceptions = INITIAL_EXCEPTIONS.filter(e =>
    e.id.toLowerCase().includes(query.toLowerCase()) ||
    e.reference.toLowerCase().includes(query.toLowerCase()) ||
    e.title.toLowerCase().includes(query.toLowerCase())
  );

  const filteredRuns = INITIAL_AUDIT_LOGS.filter(r =>
    r.runId.toLowerCase().includes(query.toLowerCase()) ||
    r.runType.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-neutral-900/50 backdrop-blur-xs p-4">
      <div 
        className="w-full max-w-2xl bg-surface-container-lowest rounded-xl shadow-2xl border border-outline-variant overflow-hidden flex flex-col max-h-[80vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Search Header */}
        <div className="p-4 border-b border-outline-variant flex items-center gap-3">
          <span className="material-symbols-outlined text-secondary text-2xl">search</span>
          <input
            autoFocus
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search transaction ID, UTR, invoice #, amount, or exception..."
            className="flex-1 bg-transparent text-sm focus:outline-none placeholder:text-outline text-on-surface"
          />
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container-low text-on-surface-variant border border-outline-variant">
            ESC to close
          </span>
          <button 
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface p-1 rounded"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Results List */}
        <div className="overflow-y-auto p-3 space-y-4 text-xs">
          {/* Transactions */}
          <div>
            <div className="text-[10px] uppercase font-mono text-on-surface-variant font-semibold px-2 mb-1 flex items-center justify-between">
              <span>Transactions & Matches</span>
              <span className="text-secondary">{filteredTxns.length} found</span>
            </div>
            {filteredTxns.length === 0 ? (
              <div className="px-2 py-1 text-on-surface-variant italic">No matching transactions</div>
            ) : (
              filteredTxns.map(t => (
                <div
                  key={t.id}
                  onClick={() => {
                    onNavigate('transactions');
                    onSelectTransaction(t.id);
                    onClose();
                  }}
                  className="p-2 rounded hover:bg-surface-container-low cursor-pointer flex items-center justify-between transition-colors border border-transparent hover:border-outline-variant/60"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-secondary">{t.id}</span>
                    <span className="text-on-surface font-medium">{t.bank.entity}</span>
                    <span className="text-[10px] font-mono text-on-surface-variant">UTR: {t.bank.utr}</span>
                  </div>
                  <div className="flex items-center gap-2 font-mono">
                    <span className="font-semibold text-on-surface">₹{t.bank.amount.toLocaleString('en-IN')}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                      t.tier === 'tier1_exact' ? 'bg-emerald-50 text-emerald-800' :
                      t.tier === 'tier2_fuzzy' ? 'bg-blue-50 text-blue-800' :
                      t.tier === 'tier3_ai' ? 'bg-sky-50 text-sky-800' : 'bg-red-50 text-red-800'
                    }`}>
                      {t.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Exceptions */}
          <div className="pt-2 border-t border-outline-variant">
            <div className="text-[10px] uppercase font-mono text-on-surface-variant font-semibold px-2 mb-1 flex items-center justify-between">
              <span>Exceptions Queue</span>
              <span className="text-error">{filteredExceptions.length} found</span>
            </div>
            {filteredExceptions.map(e => (
              <div
                key={e.id}
                onClick={() => {
                  onNavigate('exceptions');
                  onClose();
                }}
                className="p-2 rounded hover:bg-surface-container-low cursor-pointer flex items-center justify-between transition-colors border border-transparent hover:border-outline-variant/60"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold text-error">{e.id}</span>
                  <span className="text-on-surface truncate max-w-md">{e.title}</span>
                </div>
                <div className="font-mono font-semibold text-error">
                  ₹{e.valueAtRisk.toLocaleString('en-IN')}
                </div>
              </div>
            ))}
          </div>

          {/* Audit Runs */}
          <div className="pt-2 border-t border-outline-variant">
            <div className="text-[10px] uppercase font-mono text-on-surface-variant font-semibold px-2 mb-1 flex items-center justify-between">
              <span>Reconciliation Engine Runs</span>
              <span className="text-on-surface">{filteredRuns.length} found</span>
            </div>
            {filteredRuns.map(r => (
              <div
                key={r.runId}
                onClick={() => {
                  onNavigate('audit');
                  onClose();
                }}
                className="p-2 rounded hover:bg-surface-container-low cursor-pointer flex items-center justify-between transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold text-on-surface">{r.runId}</span>
                  <span className="text-on-surface font-medium">{r.runType}</span>
                  <span className="text-[10px] font-mono text-on-surface-variant">{r.timestamp}</span>
                </div>
                <span className="font-mono text-secondary font-medium">Match: {r.matchRate}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
