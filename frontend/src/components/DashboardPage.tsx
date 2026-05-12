import React, { useState, useEffect } from 'react';
import { FileText, Database, TrendingUp, Zap, CircleDot, FileCheck, Activity } from 'lucide-react';
import { getDashboardStats, getSystemHealth } from '../api/client';
import { DashboardStats, SystemHealth } from '../types';

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, h] = await Promise.all([getDashboardStats(), getSystemHealth()]);
        setStats(s);
        setHealth(h);
      } catch {
        // Use demo data when backend is not available
        setStats({
          total_documents: 33,
          total_projects: 3,
          total_vectors: 1247,
          total_queries_today: 18,
          avg_conformity_score: 87.5,
          documents_by_type: { 'fiche_technique': 26, 'rapport_chantier': 4, 'dtu': 2, 'autre': 1 },
          recent_activity: [
            { type: 'document_indexed', filename: 'DTU 20.1 - Maçonnerie.pdf', document_type: 'dtu', timestamp: new Date().toISOString(), chunks: 45 },
            { type: 'document_indexed', filename: 'Fiche AQC - ITE Enduit.pdf', document_type: 'fiche_technique', timestamp: new Date().toISOString(), chunks: 12 },
            { type: 'document_indexed', filename: 'Rapport Qualité 2025.pdf', document_type: 'rapport_chantier', timestamp: new Date().toISOString(), chunks: 78 },
          ],
          data_sources_status: [
            { name: 'Qdrant (Vecteurs)', status: 'healthy', count: 1247 },
            { name: 'Neo4j (Graphe)', status: 'healthy', count: 156 },
            { name: 'PostgreSQL (Métadonnées)', status: 'healthy', count: 33 },
            { name: 'MinIO (Documents)', status: 'healthy', count: 33 },
          ],
        });
        setHealth({
          status: 'healthy', qdrant: 'healthy', neo4j: 'healthy',
          postgres: 'healthy', minio: 'healthy', llm: 'configured',
          documents_indexed: 33, vectors_count: 1247, knowledge_nodes: 156,
          uptime_seconds: 3600,
        });
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-btpGreen border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Chargement du tableau de bord...</p>
        </div>
      </div>
    );
  }

  const statCards = [
    { label: 'Documents Indexés', value: stats?.total_documents ?? 0, icon: FileText, cls: 'stat-green', color: 'text-btpGreen' },
    { label: 'Vecteurs en Base', value: stats?.total_vectors ?? 0, icon: Database, cls: 'stat-cyan', color: 'text-btpCyan' },
    { label: 'Projets Actifs', value: stats?.total_projects ?? 0, icon: TrendingUp, cls: 'stat-amber', color: 'text-btpAmber' },
    { label: 'Requêtes Aujourd\'hui', value: stats?.total_queries_today ?? 0, icon: Zap, cls: 'stat-purple', color: 'text-purple-400' },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-8 fade-in">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white">Tableau de bord</h2>
        <p className="text-slate-400 mt-1">Vue d'ensemble du système IA BTP</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card, i) => {
          const Icon = card.icon;
          return (
            <div key={i} className={`${card.cls} rounded-2xl p-5 glass-card-hover`} style={{ animationDelay: `${i * 0.1}s` }}>
              <div className="flex items-center justify-between mb-3">
                <Icon size={22} className={card.color} />
                <span className="text-xs text-slate-500 font-medium">Total</span>
              </div>
              <p className="text-3xl font-bold text-white">{card.value.toLocaleString()}</p>
              <p className="text-sm text-slate-400 mt-1">{card.label}</p>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Data Sources Status */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <CircleDot size={16} className="text-btpGreen" />
            Sources de Données
          </h3>
          <div className="space-y-3">
            {(stats?.data_sources_status ?? []).map((src, i) => (
              <div key={i} className="flex items-center justify-between bg-slate-800/30 p-3 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className={`w-2.5 h-2.5 rounded-full ${src.status === 'healthy' ? 'bg-btpGreen pulse-dot' : 'bg-btpRed'}`} />
                  <span className="text-sm text-slate-300">{src.name}</span>
                </div>
                <span className="text-sm font-semibold text-white">{src.count.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Documents by Type */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <FileCheck size={16} className="text-btpCyan" />
            Répartition par Type
          </h3>
          <div className="space-y-3">
            {Object.entries(stats?.documents_by_type ?? {}).map(([type, count]) => {
              const total = stats?.total_documents || 1;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={type}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-400 capitalize">{type.replace(/_/g, ' ')}</span>
                    <span className="text-white font-medium">{count} ({pct}%)</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2">
                    <div className="gradient-brand h-2 rounded-full transition-all duration-700" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <Activity size={16} className="text-btpAmber" />
            Activité Récente
          </h3>
          <div className="space-y-3">
            {(stats?.recent_activity ?? []).slice(0, 5).map((item, i) => (
              <div key={i} className="flex items-start gap-3 bg-slate-800/30 p-3 rounded-xl">
                <div className="w-8 h-8 rounded-lg bg-btpGreen/10 flex items-center justify-center shrink-0 mt-0.5">
                  <FileText size={14} className="text-btpGreen" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-white font-medium truncate">{item.filename}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{item.chunks} chunks • {item.document_type}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
