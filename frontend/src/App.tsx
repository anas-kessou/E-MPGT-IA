/**
 * E-MPGT-IA — Système IA BTP
 * Premium Dashboard + Chat + Document Management
 * Refactored Version 2.1
 */

import React, { useState } from 'react';
import { Menu, HardHat } from 'lucide-react';

import { AnimatePresence, motion } from 'motion/react';

// Components
import { Sidebar } from './components/Sidebar';
import { DashboardPage } from './components/DashboardPage';
import { ChatPage } from './components/ChatPage';
import { DocumentsPage } from './components/DocumentsPage';
import { KnowledgePage } from './components/KnowledgePage';
import { SettingsPage } from './components/SettingsPage';

// Types
import { PageName } from './types';

export default function App() {
  const [currentPage, setCurrentPage] = useState<PageName>('dashboard');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const renderPage = () => {
    return (
      <AnimatePresence mode="wait">
        <motion.div
          key={currentPage}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className="flex-1 flex flex-col min-w-0 h-full"
        >
          {(() => {
            switch (currentPage) {
              case 'dashboard': return <DashboardPage />;
              case 'chat': return <ChatPage />;
              case 'documents': return <DocumentsPage />;
              case 'knowledge': return <KnowledgePage />;
              case 'settings': return <SettingsPage />;
              default: return <DashboardPage />;
            }
          })()}
        </motion.div>
      </AnimatePresence>
    );
  };

  return (
    <div className="flex h-screen bg-surface-primary overflow-hidden relative">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden animate-in fade-in duration-300"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar (Desktop Hidden on Mobile by CSS) */}
      <div className={`
        fixed inset-y-0 left-0 z-50 transform md:relative md:translate-x-0 transition-transform duration-300 ease-in-out
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        md:flex
      `}>
        <Sidebar 
          currentPage={currentPage} 
          onNavigate={setCurrentPage} 
          onClose={() => setIsSidebarOpen(false)} 
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile Header */}
        <div className="md:hidden flex items-center justify-between p-4 border-b border-slate-800 bg-surface-secondary/50">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg gradient-brand flex items-center justify-center">
              <HardHat size={16} className="text-white" />
            </div>
            <span className="font-bold text-white">E-MPGT IA</span>
          </div>
          <button 
            onClick={() => setIsSidebarOpen(true)}
            className="p-2 text-slate-400 hover:text-white"
          >
            <Menu size={24} />
          </button>
        </div>
        
        {renderPage()}
      </div>
    </div>
  );
}
