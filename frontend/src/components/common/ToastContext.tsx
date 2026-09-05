import React, { createContext, useContext, useState, useCallback } from 'react';

export interface ToastItem {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  title: string;
  message?: string;
}

interface ToastContextType {
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, 'id'>) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addToast = useCallback((toast: Omit<ToastItem, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev.slice(-3), { ...toast, id }]); // keep max 4
    setTimeout(() => {
      removeToast(id);
    }, 4000);
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      {/* Toast Container */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm pointer-events-none">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-3 p-3 rounded-lg shadow-xl border text-xs transition-all animate-in fade-in slide-in-from-bottom-2 ${
              t.type === 'success'
                ? 'bg-neutral-900 text-white border-neutral-700'
                : t.type === 'error'
                ? 'bg-red-950 text-white border-red-800'
                : t.type === 'warning'
                ? 'bg-amber-950 text-white border-amber-800'
                : 'bg-neutral-900 text-white border-neutral-700'
            }`}
          >
            <span className="material-symbols-outlined text-base mt-0.5 shrink-0 text-emerald-400">
              {t.type === 'success' ? 'check_circle' : t.type === 'error' ? 'error' : t.type === 'warning' ? 'warning' : 'info'}
            </span>
            <div className="flex-1">
              <div className="font-semibold text-xs">{t.title}</div>
              {t.message && <div className="text-[11px] text-neutral-300 mt-0.5">{t.message}</div>}
            </div>
            <button
              onClick={() => removeToast(t.id)}
              className="text-neutral-400 hover:text-white p-0.5"
            >
              <span className="material-symbols-outlined text-sm">close</span>
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
