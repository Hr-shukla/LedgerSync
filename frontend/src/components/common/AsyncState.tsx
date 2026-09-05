import React from 'react';

export const LoadingState: React.FC<{ label?: string }> = ({ label = 'Loading...' }) => (
  <div className="flex flex-col items-center justify-center gap-3 py-24 text-on-surface-variant">
    <span className="material-symbols-outlined text-3xl animate-spin">progress_activity</span>
    <span className="font-body-sm text-body-sm">{label}</span>
  </div>
);

export const ErrorState: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div className="flex flex-col items-center justify-center gap-3 py-24 text-center px-6 max-w-lg mx-auto">
    <span className="material-symbols-outlined text-4xl text-error">cloud_off</span>
    <div className="font-semibold text-sm text-on-surface">Couldn't load data from the backend</div>
    <p className="font-body-xs text-body-xs text-on-surface-variant">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        type="button"
        className="px-3 py-1.5 bg-surface-container border border-outline-variant rounded text-xs font-medium text-on-surface hover:bg-surface-container-high transition-colors"
      >
        Retry
      </button>
    )}
  </div>
);

export const EmptyState: React.FC<{
  icon?: string;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}> = ({ icon = 'inbox', title, description, action }) => (
  <div className="p-12 text-center space-y-3">
    <span className="material-symbols-outlined text-4xl text-outline">{icon}</span>
    <div className="font-semibold text-sm text-on-surface">{title}</div>
    {description && <p className="text-xs text-on-surface-variant max-w-sm mx-auto">{description}</p>}
    {action && (
      <button
        onClick={action.onClick}
        type="button"
        className="px-3 py-1.5 bg-surface-container border border-outline-variant rounded text-xs font-medium text-on-surface hover:bg-surface-container-high"
      >
        {action.label}
      </button>
    )}
  </div>
);
