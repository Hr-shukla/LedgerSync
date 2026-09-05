import React, { useState } from 'react';
import { useToast } from '../common/ToastContext';

export type NavPage = 'overview' | 'transactions' | 'exceptions' | 'audit' | 'datasources' | 'rules' | 'settings';

interface SidebarProps {
  currentPage: NavPage;
  onNavigate: (page: NavPage) => void;
  openExceptionsCount?: number;
  totalTransactionsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onNavigate,
  openExceptionsCount = 0,
  totalTransactionsCount
}) => {
  const [isEntityMenuOpen, setIsEntityMenuOpen] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState({
    name: 'Acme India Pvt Ltd',
    meta: 'INR ₹ · 27AABCA1234F1Z5',
    region: 'India Hub'
  });
  const { addToast } = useToast();

  const entities = [
    { name: 'Acme India Pvt Ltd', meta: 'INR ₹ · 27AABCA1234F1Z5', region: 'Primary Merchant' },
    { name: 'Acme Global Singapore Pte', meta: 'USD $ · 201934982K', region: 'APAC Treasury' },
    { name: 'Acme US Inc (Delaware)', meta: 'USD $ · EIN 84-2918239', region: 'North America' }
  ];

  const handleEntityChange = (e: typeof entities[0]) => {
    setSelectedEntity(e);
    setIsEntityMenuOpen(false);
    addToast({
      type: 'info',
      title: `Switched Entity: ${e.name}`,
      message: `Loaded active ledger feeds for ${e.meta}`
    });
  };

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-surface-container-lowest border-r border-outline-variant z-50 flex flex-col justify-between select-none shadow-xs">
      <div className="flex flex-col">
        {/* Brand Header */}
        <div className="p-spacing-base border-b border-outline-variant">
          <div className="flex items-center justify-between mb-spacing-md">
            <div className="flex items-center gap-2.5">
              <svg className="w-7 h-7 rounded-md shrink-0 shadow-xs" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="32" height="32" rx="6" fill="#0F172A"/>
                <path d="M7 11H25M7 16H19M7 21H23" stroke="#F8FAFC" strokeWidth="2.5" strokeLinecap="round"/>
                <circle cx="23" cy="16" r="2.5" fill="#10B981"/>
              </svg>
              <div className="flex items-baseline gap-1.5">
                <span className="font-headline-sm text-headline-sm text-on-surface tracking-tight font-bold">
                  LedgerSync
                </span>
              </div>
            </div>
            <span className="font-label-mono-xs text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200 font-semibold tracking-wide uppercase">
              FIN-OPS v2.4
            </span>
          </div>

          {/* Company / Entity Switcher */}
          <div className="relative">
            <button
              onClick={() => setIsEntityMenuOpen(!isEntityMenuOpen)}
              className="w-full text-left flex items-center justify-between p-2.5 bg-slate-50 border border-slate-200 rounded-md cursor-pointer hover:bg-slate-100 hover:border-slate-300 transition-all shadow-2xs group"
              type="button"
              title="Switch Legal Entity &amp; Currency"
            >
              <div className="flex flex-col truncate pr-1">
                <div className="flex items-center gap-1.5 truncate">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  <span className="font-semibold text-xs text-slate-900 truncate">
                    {selectedEntity.name}
                  </span>
                </div>
                <span className="font-mono text-[10px] text-slate-500 uppercase mt-0.5 pl-3.5 truncate">
                  {selectedEntity.meta}
                </span>
              </div>
              <span className="material-symbols-outlined text-slate-400 group-hover:text-slate-700 text-[18px] transition-colors">
                unfold_more
              </span>
            </button>

            {isEntityMenuOpen && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-xl z-50 py-1 divide-y divide-slate-100 animate-in fade-in slide-in-from-top-1">
                <div className="px-3 py-1.5 text-[10px] font-mono text-slate-400 uppercase font-semibold">
                  Select Legal Entity
                </div>
                {entities.map((e) => (
                  <button
                    key={e.name}
                    className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-50 transition-colors flex items-center justify-between ${
                      selectedEntity.name === e.name ? 'bg-sky-50/60 font-semibold text-sky-900' : 'text-slate-700'
                    }`}
                    onClick={() => handleEntityChange(e)}
                  >
                    <div>
                      <div className="font-semibold">{e.name}</div>
                      <div className="text-[10px] font-mono text-slate-500">{e.meta}</div>
                    </div>
                    {selectedEntity.name === e.name && (
                      <span className="material-symbols-outlined text-sky-600 text-sm">check</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Section: Reconciliation Engine */}
        <div className="px-3 pt-3 pb-1">
          <span className="font-label-mono-xs text-[10px] text-slate-400 uppercase font-semibold tracking-wider px-2">
            Reconciliation Engine
          </span>
        </div>
        <nav className="px-2 space-y-0.5">
          {/* Overview */}
          <button
            onClick={() => onNavigate('overview')}
            className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md transition-all text-xs ${
              currentPage === 'overview'
                ? 'bg-slate-100 text-slate-900 font-semibold border border-slate-200 shadow-2xs'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <span className={`material-symbols-outlined text-[18px] ${currentPage === 'overview' ? 'text-slate-900' : 'text-slate-400'}`}>
                dashboard
              </span>
              <span>Overview</span>
            </div>
            <kbd className="font-mono text-[10px] px-1 py-0.2 rounded bg-white text-slate-400 border border-slate-200 shadow-2xs">
              1
            </kbd>
          </button>

          {/* Transactions */}
          <button
            onClick={() => onNavigate('transactions')}
            className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md transition-all text-xs ${
              currentPage === 'transactions'
                ? 'bg-slate-100 text-slate-900 font-semibold border border-slate-200 shadow-2xs'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <span className={`material-symbols-outlined text-[18px] ${currentPage === 'transactions' ? 'text-slate-900' : 'text-slate-400'}`}>
                swap_horiz
              </span>
              <span>Transactions</span>
            </div>
            <div className="flex items-center gap-1.5">
              {totalTransactionsCount !== undefined && (
                <span className="font-mono text-[11px] px-1.5 py-0.2 rounded bg-slate-200/70 text-slate-700 tabular-nums font-semibold">
                  {totalTransactionsCount.toLocaleString('en-IN')}
                </span>
              )}
              <kbd className="font-mono text-[10px] px-1 py-0.2 rounded bg-white text-slate-400 border border-slate-200 shadow-2xs">
                2
              </kbd>
            </div>
          </button>

          {/* Exceptions Queue */}
          <button
            onClick={() => onNavigate('exceptions')}
            className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md transition-all text-xs ${
              currentPage === 'exceptions'
                ? 'bg-red-50/70 text-red-950 font-semibold border border-red-200 shadow-2xs'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <span className={`material-symbols-outlined text-[18px] ${currentPage === 'exceptions' ? 'text-red-700' : 'text-slate-400'}`}>
                error
              </span>
              <span>Exceptions Queue</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[11px] px-1.5 py-0.2 rounded bg-red-100 text-red-800 tabular-nums font-bold border border-red-200">
                {openExceptionsCount}
              </span>
              <kbd className="font-mono text-[10px] px-1 py-0.2 rounded bg-white text-slate-400 border border-slate-200 shadow-2xs">
                3
              </kbd>
            </div>
          </button>

          {/* Audit Log */}
          <button
            onClick={() => onNavigate('audit')}
            className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md transition-all text-xs ${
              currentPage === 'audit'
                ? 'bg-slate-100 text-slate-900 font-semibold border border-slate-200 shadow-2xs'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <span className={`material-symbols-outlined text-[18px] ${currentPage === 'audit' ? 'text-slate-900' : 'text-slate-400'}`}>
                history_edu
              </span>
              <span>Audit Log</span>
            </div>
            <kbd className="font-mono text-[10px] px-1 py-0.2 rounded bg-white text-slate-400 border border-slate-200 shadow-2xs">
              4
            </kbd>
          </button>
        </nav>

        {/* Section: Platform */}
        <div className="px-3 pt-4 pb-1">
          <span className="font-label-mono-xs text-[10px] text-slate-400 uppercase font-semibold tracking-wider px-2">
            Platform
          </span>
        </div>
        <nav className="px-2 space-y-0.5">
          <button
            onClick={() => onNavigate('datasources')}
            className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-md transition-all text-xs ${
              currentPage === 'datasources'
                ? 'bg-slate-100 text-slate-900 font-semibold border border-slate-200'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium'
            }`}
          >
            <span className="material-symbols-outlined text-[18px] text-slate-400">account_balance</span>
            <span>Data Sources</span>
          </button>
          <button
            onClick={() => onNavigate('rules')}
            className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-md transition-all text-xs ${
              currentPage === 'rules'
                ? 'bg-slate-100 text-slate-900 font-semibold border border-slate-200'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium'
            }`}
          >
            <span className="material-symbols-outlined text-[18px] text-slate-400">rule</span>
            <span>Reconciliation Rules</span>
          </button>
          <button
            onClick={() => onNavigate('settings')}
            className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-md transition-all text-xs ${
              currentPage === 'settings'
                ? 'bg-slate-100 text-slate-900 font-semibold border border-slate-200'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium'
            }`}
          >
            <span className="material-symbols-outlined text-[18px] text-slate-400">settings</span>
            <span>Settings</span>
          </button>
        </nav>
      </div>

      {/* Pinned Bottom Status & Profile */}
      <div className="border-t border-slate-200">
        {/* Engine Operational Indicator */}
        <div className="p-2.5 mx-2.5 my-2.5 bg-slate-50 rounded-md border border-slate-200 shadow-2xs">
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="font-mono text-[10px] font-bold text-slate-800 uppercase tracking-wider">
              Engine Operational
            </span>
          </div>
          <div className="font-mono text-[10px] text-slate-500 mt-1 flex items-center justify-between">
            <span>Last run: 4 mins ago</span>
            <span className="text-emerald-700 font-semibold">PASS</span>
          </div>
        </div>

        {/* User Profile */}
        <div className="p-3 border-t border-slate-200 flex items-center justify-between bg-white">
          <div className="flex items-center gap-2.5 truncate">
            <div className="w-7 h-7 rounded-full bg-slate-900 flex items-center justify-center flex-shrink-0 text-white font-bold text-[11px] shadow-xs">
              PS
            </div>
            <div className="flex flex-col truncate">
              <span className="font-semibold text-xs text-slate-900 truncate">Priya Sharma</span>
              <span className="text-[10px] text-slate-500 truncate">Lead Finance Controller</span>
            </div>
          </div>
          <button 
            onClick={() => addToast({ type: 'info', title: 'Signed Out', message: 'Controller session ended safely.' })}
            title="Sign out"
            className="text-slate-400 hover:text-slate-700 p-1 rounded hover:bg-slate-100 transition-colors"
          >
            <span className="material-symbols-outlined text-[17px]">logout</span>
          </button>
        </div>
      </div>
    </aside>
  );
};
