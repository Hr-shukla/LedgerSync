import React, { useState } from 'react';
import { ExceptionItem } from '../../types/legacy';

interface JournalPreviewModalProps {
  isOpen: boolean;
  exception: ExceptionItem | null;
  onClose: () => void;
  onConfirm: () => void;
}

export const JournalPreviewModal: React.FC<JournalPreviewModalProps> = ({
  isOpen,
  exception,
  onClose,
  onConfirm
}) => {
  const [isPosting, setIsPosting] = useState(false);

  if (!isOpen || !exception) return null;

  const handlePost = () => {
    setIsPosting(true);
    setTimeout(() => {
      setIsPosting(false);
      onConfirm();
      onClose();
    }, 800);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/60 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg bg-surface-container-lowest rounded-xl shadow-2xl border border-outline-variant overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-surface-container-low border-b border-outline-variant flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-xl">edit_note</span>
            <div>
              <h3 className="font-headline-sm text-sm font-semibold text-on-surface">
                Post ERP Adjustment Journal Voucher
              </h3>
              <p className="text-[11px] font-mono text-on-surface-variant">
                Target: SAP General Ledger · Ref: {exception.reference}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded text-on-surface-variant hover:text-on-surface">
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        {/* Form / Journal Body */}
        <div className="p-4 space-y-4 text-xs">
          <div className="p-3 bg-surface-container-low rounded border border-outline-variant/60 leading-relaxed text-on-surface-variant">
            LedgerSync AI detected an unrecorded 18% GST fee component of <strong>₹4,850.00</strong> on platform gateway settlement. Generating balanced bilateral double-entry voucher:
          </div>

          {/* Double Entry Table */}
          <div className="border border-outline-variant rounded overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-low border-b border-outline-variant text-[10px] uppercase font-mono text-on-surface-variant">
                  <th className="p-2">Account # &amp; Description</th>
                  <th className="p-2 text-right">Debit (INR)</th>
                  <th className="p-2 text-right">Credit (INR)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/60 font-mono text-xs">
                <tr>
                  <td className="p-2 text-on-surface">
                    <div className="font-semibold">#2104 - Input Tax Credit (GST 18%)</div>
                    <div className="text-[10px] text-on-surface-variant">Tax Line: CGST 9% + SGST 9%</div>
                  </td>
                  <td className="p-2 text-right font-semibold text-on-surface">₹4,850.00</td>
                  <td className="p-2 text-right text-outline">-</td>
                </tr>
                <tr>
                  <td className="p-2 text-on-surface">
                    <div className="font-semibold">#1101 - Razorpay Gateway Clearing Nodal</div>
                    <div className="text-[10px] text-on-surface-variant">Variance Offset: RZP-BATCH-892418</div>
                  </td>
                  <td className="p-2 text-right text-outline">-</td>
                  <td className="p-2 text-right font-semibold text-on-surface">₹4,850.00</td>
                </tr>
                <tr className="bg-surface-container-low/60 font-bold border-t border-outline-variant">
                  <td className="p-2 text-on-surface font-sans">Total Balanced Entry</td>
                  <td className="p-2 text-right text-on-surface">₹4,850.00</td>
                  <td className="p-2 text-right text-on-surface">₹4,850.00</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="text-[11px] font-mono text-on-surface-variant flex items-center justify-between">
            <span>Fiscal Period: Oct 2024</span>
            <span className="text-emerald-700 font-semibold">Variance Delta: ₹0.00 (Balanced)</span>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-surface-container-low border-t border-outline-variant flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-3 py-1.5 border border-outline-variant rounded text-xs text-on-surface hover:bg-surface-container transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handlePost}
            disabled={isPosting}
            className="px-4 py-1.5 bg-primary text-white text-xs font-semibold rounded hover:bg-neutral-800 transition-colors shadow-xs flex items-center gap-1.5"
          >
            {isPosting ? (
              <>
                <span className="material-symbols-outlined text-xs animate-spin">refresh</span>
                <span>Posting to SAP RFC...</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-xs">send</span>
                <span>Post &amp; Auto-Reconcile</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
