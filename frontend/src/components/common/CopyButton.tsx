import React, { useState } from 'react';

interface CopyButtonProps {
  text: string;
  label?: string;
  className?: string;
}

export const CopyButton: React.FC<CopyButtonProps> = ({ text, label, className = '' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      title={copied ? 'Copied to clipboard!' : `Copy ${label || text}`}
      className={`inline-flex items-center gap-1 text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors rounded px-1 py-0.5 text-[10px] font-mono ${className}`}
      type="button"
    >
      <span className="material-symbols-outlined text-[13px]">
        {copied ? 'check' : 'content_copy'}
      </span>
      {copied ? (
        <span className="text-emerald-700 font-semibold font-sans">Copied!</span>
      ) : label ? (
        <span>{label}</span>
      ) : null}
    </button>
  );
};
