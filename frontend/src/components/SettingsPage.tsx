import React, { useState, useEffect } from 'react';
import { Settings, CheckCircle2, RotateCcw, FileCheck, Database } from 'lucide-react';
import { getAllSettings, saveSetting } from '../api/client';
import { AppSettings } from '../types';

export function SettingsPage() {
  const [isSaving, setIsSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState<AppSettings>({
    llmModel: 'gemini-3.1-flash-lite',
    temperature: 0.2,
    embeddingModel: 'text-embedding-001',
    chunkSize: 1800,
    chunkOverlap: 350,
    topK: 10
  }); useEffect(() => {
    async function load() {
      try {
        const persisted = await getAllSettings();
        if (persisted && persisted.app_config) {
          setSettings(prev => ({ ...prev, ...persisted.app_config }));
        }
      } catch (err) {
        console.warn("Could not load settings from backend, using defaults", err);
      }
      setLoading(false);
    }
    load();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await saveSetting('app_config', settings);
      // Optional: show a toast
    } catch (err) {
      alert("Erreur lors de la sauvegarde des paramètres");
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <RotateCcw className="animate-spin text-btpGreen" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-8 fade-in">
      <div>
        <h2 className="text-2xl font-bold text-white">Paramètres Système</h2>
        <p className="text-slate-400 mt-1">Configuration des modèles IA et du pipeline RAG (Persisté en base)</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* LLM Config */}
        <div className="glass-card p-6 space-y-6">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <Settings size={16} className="text-btpGreen" />
            Intelligence Artificielle
          </h3>

          <div className="space-y-4">
            <div>
              <label className="text-xs text-slate-400 font-medium block mb-1.5">Modèle LLM Principal</label>
              <select
                className="input-dark w-full"
                value={settings.llmModel}
                onChange={e => setSettings(prev => ({ ...prev, llmModel: e.target.value }))}
              >
                <option value="gemini-3.1-flash-lite">gemini 3.1 flash lite (Recommandé)</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro (Haute Qualité)</option>
                <option value="gpt-4o">GPT-4o (Azure OpenAI)</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-slate-400 font-medium block mb-1.5">Température ({settings.temperature})</label>
              <input
                type="range" min="0" max="1" step="0.1"
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-btpGreen"
                value={settings.temperature}
                onChange={e => setSettings(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
              />
              <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                <span>Précis</span>
                <span>Créatif</span>
              </div>
            </div>
          </div>
        </div>

        {/* RAG Config */}
        <div className="glass-card p-6 space-y-6">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <Database size={16} className="text-btpCyan" />
            Paramètres RAG
          </h3>

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="text-xs text-slate-400 font-medium block mb-1.5">Modèle d'Embeddings</label>
              <select
                className="input-dark w-full"
                value={settings.embeddingModel}
                onChange={e => setSettings(prev => ({ ...prev, embeddingModel: e.target.value }))}
              >
                <option value="text-embedding-004">Google text-embedding-001</option>
                <option value="text-multilingual-embedding-002">Google multilingual-002</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 font-medium block mb-1.5">Taille des Chunks</label>
              <input
                type="number"
                className="input-dark w-full"
                value={settings.chunkSize}
                onChange={e => setSettings(prev => ({ ...prev, chunkSize: parseInt(e.target.value) }))}
              />
              <p className="text-xs text-slate-600 mt-1">Nombre de caractères par fragment</p>
            </div>
            <div>
              <label className="text-xs text-slate-400 font-medium block mb-1.5">Chevauchement (Overlap)</label>
              <input
                type="number"
                className="input-dark w-full"
                value={settings.chunkOverlap}
                onChange={e => setSettings(prev => ({ ...prev, chunkOverlap: parseInt(e.target.value) }))}
              />
              <p className="text-xs text-slate-600 mt-1">Chevauchement entre les chunks</p>
            </div>
            <div>
              <label className="text-xs text-slate-400 font-medium block mb-1.5">Top-K résultats</label>
              <input
                type="number"
                className="input-dark w-full"
                value={settings.topK}
                onChange={e => setSettings(prev => ({ ...prev, topK: parseInt(e.target.value) }))}
              />
              <p className="text-xs text-slate-600 mt-1">Nombre de chunks récupérés</p>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="lg:col-span-2 flex justify-end">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="btn-primary px-8 flex items-center gap-2"
          >
            {isSaving ? <RotateCcw className="animate-spin" size={16} /> : <FileCheck size={16} />}
            Enregistrer les modifications
          </button>
        </div>

        {/* Infrastructure Status */}
        <div className="glass-card p-6 lg:col-span-2">
          <h3 className="text-sm font-bold text-white mb-4">Infrastructure</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {[
              { name: 'Qdrant', desc: 'Vector DB', port: 6333 },
              { name: 'Neo4j', desc: 'Knowledge Graph', port: 7474 },
              { name: 'PostgreSQL', desc: 'Métadonnées', port: 5432 },
              { name: 'MinIO', desc: 'Documents S3', port: 9000 },
              { name: 'n8n', desc: 'Workflows', port: 5678 },
            ].map(svc => (
              <div key={svc.name} className="bg-slate-800/30 p-4 rounded-xl text-center">
                <div className="w-2 h-2 rounded-full bg-btpGreen pulse-dot mx-auto mb-2" />
                <p className="text-sm font-semibold text-white">{svc.name}</p>
                <p className="text-xs text-slate-500">{svc.desc}</p>
                <p className="text-[11px] text-slate-600 mt-1">:{svc.port}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
