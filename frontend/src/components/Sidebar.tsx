import React from 'react';
import { HardHat, LayoutDashboard, MessageSquare, FolderOpen, Share2, Settings, Zap } from 'lucide-react';
import { PageName } from '../types';

interface SidebarProps {
  currentPage: PageName;
  onNavigate: (p: PageName) => void;
  onClose?: () => void;
}

export function Sidebar({ currentPage, onNavigate, onClose }: SidebarProps) {
  const handleNav = (p: PageName) => {
    onNavigate(p);
    if (onClose) onClose();
  };

  const navItems: { id: PageName; label: string; icon: React.ElementType }[] = [
    { id: 'dashboard', label: 'Tableau de bord', icon: LayoutDashboard },
    { id: 'chat', label: 'Assistant IA', icon: MessageSquare },
    { id: 'documents', label: 'Documents', icon: FolderOpen },
    { id: 'knowledge', label: 'Knowledge Graph', icon: Share2 },
    { id: 'settings', label: 'Paramètres', icon: Settings },
  ];

  return (
    <div className="w-[260px] h-full gradient-sidebar flex flex-col border-r border-slate-800">
      {/* Logo */}
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl gradient-brand flex items-center justify-center glow-green">
            <HardHat size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight">E-MPGT</h1>
            <p className="text-[11px] text-slate-500 font-medium uppercase tracking-widest">Système IA BTP</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(item => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handleNav(item.id)}
              className={`nav-item w-full ${isActive ? 'active' : ''}`}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* System Status */}
      <div className="p-4 border-t border-slate-800">
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-btpGreen pulse-dot" />
            <span className="text-xs font-semibold text-slate-300">Système Actif</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-500">RAG Pipeline</span>
              <span className="text-btpGreen font-medium">Online</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-500">Vector DB</span>
              <span className="text-btpGreen font-medium">Connected</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-500">Knowledge Graph</span>
              <span className="text-btpGreen font-medium">Ready</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
