import React, { useState, useEffect } from 'react';
import { Sidebar, NavPage } from './Sidebar';
import { TopBar } from './TopBar';
import { GlobalSearchModal } from '../common/GlobalSearchModal';
import { ComplianceModal } from '../common/ComplianceModal';
import { MerkleVerifyModal } from '../common/MerkleVerifyModal';
import { ReconcileProgressModal } from '../common/ReconcileProgressModal';
import { ShortcutsModal } from '../common/ShortcutsModal';
import { useToast } from '../common/ToastContext';

interface AppLayoutProps {
  currentPage: NavPage;
  onNavigate: (page: NavPage) => void;
  onSelectTransaction: (id: string) => void;
  openExceptionsCount: number;
  totalTransactionsCount?: number;
  children: (modals: {
    openComplianceModal: () => void;
    openMerkleModal: () => void;
  }) => React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  currentPage,
  onNavigate,
  onSelectTransaction,
  openExceptionsCount,
  totalTransactionsCount,
  children
}) => {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isComplianceOpen, setIsComplianceOpen] = useState(false);
  const [isMerkleOpen, setIsMerkleOpen] = useState(false);
  const [isProgressOpen, setIsProgressOpen] = useState(false);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const { addToast } = useToast();

  // Controller global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts if typing inside an input or textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') {
        return;
      }

      if (e.key === '1') {
        onNavigate('overview');
      } else if (e.key === '2') {
        onNavigate('transactions');
      } else if (e.key === '3') {
        onNavigate('exceptions');
      } else if (e.key === '4') {
        onNavigate('audit');
      } else if (e.key === '?' || (e.shiftKey && e.key === '/')) {
        setIsShortcutsOpen(true);
      } else if (e.key === 'r' || e.key === 'R') {
        if (!e.metaKey && !e.ctrlKey) {
          e.preventDefault();
          setIsProgressOpen(true);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onNavigate]);

  const handleReconciliationComplete = () => {
    addToast({
      type: 'success',
      title: 'Batch #8492 Reconciled',
      message: '12,482 transactions reconciled with 97.42% resolution rate.'
    });
  };

  return (
    <div className="min-h-screen bg-surface font-body-default text-body-default text-on-surface antialiased flex flex-col">
      {/* Fixed Left Sidebar */}
      <Sidebar
        currentPage={currentPage}
        onNavigate={onNavigate}
        openExceptionsCount={openExceptionsCount}
        totalTransactionsCount={totalTransactionsCount}
      />

      {/* Fixed Top Bar */}
      <TopBar
        onOpenSearch={() => setIsSearchOpen(true)}
        onRunReconcile={() => setIsProgressOpen(true)}
        onOpenHelp={() => setIsShortcutsOpen(true)}
        isRunningReconcile={isProgressOpen}
      />

      {/* Main Page Area */}
      <main className="pl-64 pt-14 min-h-screen bg-surface w-full flex-1">
        {children({
          openComplianceModal: () => setIsComplianceOpen(true),
          openMerkleModal: () => setIsMerkleOpen(true)
        })}
      </main>

      {/* Global Modals */}
      <GlobalSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelectTransaction={onSelectTransaction}
        onNavigate={onNavigate}
      />

      <ComplianceModal
        isOpen={isComplianceOpen}
        onClose={() => setIsComplianceOpen(false)}
      />

      <MerkleVerifyModal
        isOpen={isMerkleOpen}
        onClose={() => setIsMerkleOpen(false)}
      />

      <ReconcileProgressModal
        isOpen={isProgressOpen}
        onClose={() => setIsProgressOpen(false)}
        onComplete={handleReconciliationComplete}
      />

      <ShortcutsModal
        isOpen={isShortcutsOpen}
        onClose={() => setIsShortcutsOpen(false)}
      />
    </div>
  );
};
