import React, { useEffect, useState } from 'react';
import { AppLayout } from './components/layout/AppLayout';
import { NavPage } from './components/layout/Sidebar';
import { OverviewPage } from './pages/OverviewPage';
import { TransactionsPage } from './pages/TransactionsPage';
import { ExceptionsPage } from './pages/ExceptionsPage';
import { AuditLogPage } from './pages/AuditLogPage';
import { DataSourcesPage, ReconciliationRulesPage, SettingsPage } from './pages/PlatformPages';
import { ToastProvider } from './components/common/ToastContext';
import { getOverview, getTransactions } from './lib/api';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<NavPage>('overview');
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | undefined>(undefined);
  const [openExceptionsCount, setOpenExceptionsCount] = useState<number>(0);
  const [totalTransactionsCount, setTotalTransactionsCount] = useState<number>(0);

  // Sidebar badges reflect real backend counts. Best-effort: if the backend
  // is unreachable, badges just stay at 0 rather than showing a fabricated
  // number -- the individual pages surface the real connection error.
  useEffect(() => {
    getOverview()
      .then((o) => setOpenExceptionsCount(o.open_exceptions_count))
      .catch(() => {});
    getTransactions({ page_size: 1 })
      .then((t) => setTotalTransactionsCount(t.total))
      .catch(() => {});
  }, []);

  return (
    <ToastProvider>
      <AppLayout
        currentPage={currentPage}
        onNavigate={setCurrentPage}
        onSelectTransaction={(id) => {
          setSelectedTransactionId(id);
          setCurrentPage('transactions');
        }}
        openExceptionsCount={openExceptionsCount}
        totalTransactionsCount={totalTransactionsCount}
      >
        {() => {
          switch (currentPage) {
            case 'overview':
              return <OverviewPage onNavigate={setCurrentPage} />;
            case 'transactions':
              return (
                <TransactionsPage
                  selectedTransactionId={selectedTransactionId}
                  onSelectTransactionId={setSelectedTransactionId}
                />
              );
            case 'exceptions':
              return (
                <ExceptionsPage
                  onNavigateToAuditLog={() => setCurrentPage('audit')}
                  onUpdateOpenCount={setOpenExceptionsCount}
                />
              );
            case 'audit':
              return <AuditLogPage />;
            case 'datasources':
              return <DataSourcesPage />;
            case 'rules':
              return <ReconciliationRulesPage />;
            case 'settings':
              return <SettingsPage />;
            default:
              return <OverviewPage onNavigate={setCurrentPage} />;
          }
        }}
      </AppLayout>
    </ToastProvider>
  );
};

export default App;
