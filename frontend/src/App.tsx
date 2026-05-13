import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { DashboardPage } from './components/DashboardPage';
import { ChatPage } from './components/ChatPage';
import { DocumentsPage } from './components/DocumentsPage';
import { KnowledgePage } from './components/KnowledgePage';
import { SettingsPage } from './components/SettingsPage';
import type { PageName } from './types';

export default function App() {
  const [currentPage, setCurrentPage] = useState<PageName>('chat');

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage />;
      case 'chat':
        return <ChatPage />;
      case 'documents':
        return <DocumentsPage />;
      case 'knowledge':
        return <KnowledgePage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <ChatPage />;
    }
  };

  return (
    <div className="flex h-screen bg-slate-900 text-slate-200 overflow-hidden font-sans">
      <Sidebar currentPage={currentPage} onNavigate={setCurrentPage} />
      
      <main className="flex-1 flex flex-col relative overflow-hidden bg-slate-950">
        <header className="h-16 flex items-center justify-between px-6 border-b border-slate-800 bg-slate-900/50 backdrop-blur top-0 z-10 w-full">
          <h2 className="text-lg font-semibold text-slate-100 capitalize">
            {currentPage === 'dashboard' && 'Tableau de bord'}
            {currentPage === 'chat' && 'Assistant IA BTP'}
            {currentPage === 'documents' && 'Gestion Documentaire RAG'}
            {currentPage === 'knowledge' && 'Knowledge Graph BTP'}
            {currentPage === 'settings' && 'Configuration Système'}
          </h2>
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium px-2.5 py-1 rounded bg-green-500/10 text-green-400 border border-green-500/20">
              Système En Ligne
            </span>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto w-full relative">
          {renderPage()}
        </div>
      </main>
    </div>
  );
}
