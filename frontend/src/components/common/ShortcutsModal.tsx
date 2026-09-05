import React from 'react';

interface ShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ShortcutsModal: React.FC<ShortcutsModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const shortcuts = [
    { key: '⌘ + K / Ctrl + K', action: 'Open Global Search Console' },
    { key: '1', action: 'Navigate to Reconciliation Overview' },
    { key: '2', action: 'Navigate to Transaction Matching' },
    { key: '3', action: 'Navigate to Exceptions Worklist Queue' },
    { key: '4', action: 'Navigate to Audit Trail & Run Log' },
    { key: 'R', action: 'Trigger Immediate Reconciliation Run' },
    { key: 'ESC', action: 'Close Drawer / Dismiss Modal' }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/60 backdrop-blur-xs p-4">
      <div className="w-full max-w-md bg-surface-container-lowest rounded-xl shadow-2xl border border-outline-variant overflow-hidden">
        <div className="p-4 bg-surface-container-low border-b border-outline-variant flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-xl">keyboard</span>
            <h3 className="font-headline-sm text-sm font-semibold text-on-surface">
              Finance Controller Keyboard Shortcuts
            </h3>
          </div>
          <button onClick={onClose} className="p-1 rounded text-on-surface-variant hover:text-on-surface">
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        <div className="p-4 space-y-2">
          {shortcuts.map(s => (
            <div key={s.key} className="flex items-center justify-between py-1.5 border-b border-outline-variant/40 text-xs">
              <span className="text-on-surface-variant">{s.action}</span>
              <kbd className="px-2 py-0.5 rounded bg-surface-container font-mono text-[11px] font-semibold text-on-surface border border-outline-variant">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="p-3 bg-surface-container-low border-t border-outline-variant flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-primary text-white text-xs font-semibold rounded hover:bg-neutral-800 transition-colors shadow-xs"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
};
