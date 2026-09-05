import React, { useState } from 'react';

interface TopBarProps {
  onOpenSearch: () => void;
  onRunReconcile: () => void;
  onOpenHelp: () => void;
  isRunningReconcile?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  onOpenSearch,
  onRunReconcile,
  onOpenHelp,
  isRunningReconcile = false
}) => {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showDateDropdown, setShowDateDropdown] = useState(false);
  const [selectedCycle, setSelectedCycle] = useState('Oct 1, 2024 - Oct 31, 2024');

  const cycles = [
    { label: 'Oct 1, 2024 - Oct 31, 2024', tag: 'Monthly Close (Current)' },
    { label: 'Sep 1, 2024 - Sep 30, 2024', tag: 'Archived Close' },
    { label: 'Q3 FY24-25 (Oct-Dec)', tag: 'Quarterly Audit' }
  ];

  return (
    <header className="fixed top-0 left-64 right-0 h-14 bg-surface-container-lowest border-b border-outline-variant z-40 flex items-center justify-between px-spacing-xl shadow-xs">
      {/* Search Bar with ⌘K */}
      <div className="flex items-center gap-spacing-md w-96">
        <div 
          onClick={onOpenSearch}
          className="relative w-full flex items-center cursor-pointer group"
          title="Press ⌘K or Ctrl+K to search"
        >
          <span className="material-symbols-outlined absolute left- spacing-sm text-on-surface-variant text-[18px] ml-2 group-hover:text-secondary transition-colors">
            search
          </span>
          <input
            readOnly
            className="w-full h-8 pl-8 pr-12 text-body-sm font-body-sm bg-surface-container-low border border-outline-variant rounded group-hover:border-secondary transition-colors text-on-surface placeholder:text-outline cursor-pointer"
            placeholder="Search transaction ID, UTR, invoice #, amount..."
            type="text"
          />
          <span className="absolute right-2 font-label-mono-xs text-label-mono-xs text-on-surface-variant border border-outline-variant rounded px-spacing-2xs bg-surface-container-lowest font-medium">
            ⌘K
          </span>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-spacing-md">
        {/* Date-range picker with fiscal period label */}
        <div className="relative">
          <button
            onClick={() => setShowDateDropdown(!showDateDropdown)}
            className="flex items-center gap-spacing-xs px-spacing-sm py-1 bg-surface-container-low border border-outline-variant rounded text-on-surface cursor-pointer hover:bg-surface-container transition-colors"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px] text-on-surface-variant">calendar_today</span>
            <span className="font-label-mono-xs text-label-mono-xs tabular-nums font-medium">{selectedCycle}</span>
            <span className="font-body-xs text-body-xs text-on-surface-variant">· Monthly Close</span>
            <span className="material-symbols-outlined text-[14px] text-on-surface-variant">expand_more</span>
          </button>

          {showDateDropdown && (
            <div className="absolute top-full right-0 mt-1 w-64 bg-surface-container-lowest border border-outline-variant rounded shadow-lg z-50 py-1 divide-y divide-outline-variant/40">
              <div className="px-3 py-1.5 text-[10px] font-mono text-on-surface-variant uppercase font-semibold">
                Fiscal Closing Periods
              </div>
              {cycles.map(c => (
                <button
                  key={c.label}
                  onClick={() => {
                    setSelectedCycle(c.label);
                    setShowDateDropdown(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-xs hover:bg-surface-container transition-colors ${
                    selectedCycle === c.label ? 'bg-surface-container font-medium' : ''
                  }`}
                >
                  <div className="font-mono text-on-surface font-semibold">{c.label}</div>
                  <div className="text-[10px] text-on-surface-variant">{c.tag}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Environment Badge */}
        <span className="font-label-mono-xs text-label-mono-xs px-spacing-sm py-1 rounded bg-secondary-fixed text-on-secondary-fixed font-semibold uppercase border border-secondary-fixed-dim tracking-wide">
          Production
        </span>

        {/* Primary Action Button: "Run Now" (sized appropriately without wrapping) */}
        <button
          onClick={onRunReconcile}
          disabled={isRunningReconcile}
          title="Run Reconciliation Now (Batch #8492) - Hotkey: R"
          className="h-8 px-spacing-md border border-outline-variant rounded text-on-surface bg-surface-container-lowest hover:bg-surface-container-low font-body-medium text-body-medium flex items-center gap-spacing-xs transition-colors whitespace-nowrap flex-shrink-0 shadow-xs active:scale-[0.98]"
          type="button"
        >
          <span className={`material-symbols-outlined text-[16px] text-secondary ${isRunningReconcile ? 'animate-spin' : ''}`}>
            autorenew
          </span>
          <span className="font-semibold text-xs">
            {isRunningReconcile ? 'Syncing...' : 'Run Now'}
          </span>
        </button>

        <div className="h-4 w-px bg-outline-variant"></div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-spacing-xs rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low transition-colors"
            title="Notifications"
            type="button"
          >
            <span className="material-symbols-outlined text-[20px]">notifications</span>
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-error ring-2 ring-surface-container-lowest"></span>
          </button>

          {showNotifications && (
            <div className="absolute top-full right-0 mt-2 w-80 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-xl z-50 p-3 space-y-2">
              <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
                <span className="font-headline-sm text-xs font-semibold">System Notifications</span>
                <span className="font-label-mono-xs text-[10px] text-secondary font-semibold">3 new</span>
              </div>
              <div className="space-y-1.5 text-xs">
                <div className="p-2 bg-surface-container-low rounded border border-outline-variant/60">
                  <div className="font-medium text-on-surface flex items-center justify-between">
                    <span>Hourly Ingestion Completed</span>
                    <span className="text-[10px] font-mono text-on-surface-variant">4m ago</span>
                  </div>
                  <div className="text-on-surface-variant text-[11px] mt-0.5">480 txns matched with 99.17% resolution.</div>
                </div>
                <div className="p-2 bg-error-container/30 border border-error-container rounded">
                  <div className="font-medium text-on-error-container flex items-center justify-between">
                    <span>New Break Flagged (#EXP-402)</span>
                    <span className="text-[10px] font-mono text-on-surface-variant">12m ago</span>
                  </div>
                  <div className="text-on-surface-variant text-[11px] mt-0.5">Bank debit ₹18,40,000 without ERP counterpart.</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Help / Shortcuts Icon */}
        <button
          onClick={onOpenHelp}
          className="p-spacing-xs rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low transition-colors"
          title="Keyboard Shortcuts &amp; Help (Press ?)"
          type="button"
        >
          <span className="material-symbols-outlined text-[20px]">help</span>
        </button>

        {/* User Profile Avatar */}
        <div 
          className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary text-xs font-semibold cursor-pointer"
          title="Priya Sharma (Lead Finance Controller)"
        >
          PS
        </div>
      </div>
    </header>
  );
};
