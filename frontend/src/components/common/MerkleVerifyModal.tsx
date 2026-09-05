import React, { useState } from 'react';

interface MerkleVerifyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MerkleVerifyModal: React.FC<MerkleVerifyModalProps> = ({ isOpen, onClose }) => {
  const [isVerifying, setIsVerifying] = useState(false);
  const [hasVerified, setHasVerified] = useState(false);

  if (!isOpen) return null;

  const handleVerify = () => {
    setIsVerifying(true);
    setTimeout(() => {
      setIsVerifying(false);
      setHasVerified(true);
    }, 900);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/50 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg bg-surface-container-lowest rounded-xl shadow-2xl border border-outline-variant overflow-hidden">
        <div className="p-4 border-b border-outline-variant flex items-center justify-between bg-surface-container-low">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-xl">shield</span>
            <div>
              <h3 className="font-headline-sm text-sm font-semibold text-on-surface">
                Cryptographic Merkle Root Verification
              </h3>
              <span className="text-[11px] font-mono text-secondary">
                HMAC-SHA256 Append-Only Chain
              </span>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface p-1 rounded"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        <div className="p-4 space-y-3 text-xs">
          <p className="text-on-surface-variant leading-relaxed">
            Every reconciliation batch and manual controller intervention is hashed into an immutable chronological block. Verify the current ledger root against the cryptographic seal.
          </p>

          <div className="p-3 bg-surface-container-low rounded border border-outline-variant/60 font-mono space-y-2">
            <div className="flex justify-between text-[11px]">
              <span className="text-on-surface-variant">Total Blocks Signed:</span>
              <span className="text-on-surface font-semibold">186 Runs (Oct 2024)</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-on-surface-variant">Current Block Sequence:</span>
              <span className="text-on-surface font-semibold">#BLK-8492-20241031</span>
            </div>
            <div>
              <div className="text-on-surface-variant text-[10px] mb-0.5">Calculated Merkle Root:</div>
              <code className="text-[10px] bg-surface-container-lowest p-1.5 rounded border border-outline-variant/60 block break-all text-on-surface">
                0x8f28b49e612cb3501a4e59178cc0209f87c53641b9a2c3d4e5f6a7b8c9d0e1f2
              </code>
            </div>
          </div>

          {hasVerified && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded flex items-center gap-2.5 text-emerald-900">
              <span className="material-symbols-outlined text-emerald-600 text-lg">check_circle</span>
              <div>
                <div className="font-semibold text-xs">100% Chain Integrity Confirmed</div>
                <div className="text-[11px] text-emerald-700">
                  All 186 batch invariants and transaction trees verified without tamper.
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="p-3 border-t border-outline-variant bg-surface-container-low flex items-center justify-between">
          <span className="text-[10px] font-mono text-on-surface-variant">
            Last check: 4 mins ago · PASS
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 border border-outline-variant rounded text-xs text-on-surface hover:bg-surface-container transition-colors"
            >
              Close
            </button>
            <button
              onClick={handleVerify}
              disabled={isVerifying}
              className="px-4 py-1.5 bg-primary text-on-primary rounded text-xs font-semibold hover:bg-neutral-800 transition-colors flex items-center gap-1.5 shadow-xs"
            >
              {isVerifying ? (
                <>
                  <span className="material-symbols-outlined text-xs animate-spin">refresh</span>
                  <span>Hashing Blocks...</span>
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-xs">verified</span>
                  <span>Verify Merkle Root Now</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
