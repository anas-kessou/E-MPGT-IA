import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Upload, Search, Filter, FileText, Trash2, FolderOpen } from 'lucide-react';
import { getDocuments, uploadDocument, deleteDocument } from '../api/client';
import { DocumentItem, DocumentFilters } from '../types';

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [filters, setFilters] = useState<DocumentFilters>({ query: '', type: 'tous' });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocs = useCallback(async () => {
    try {
      const data = await getDocuments();
      let docs = data.documents || [];
      
      // Local filtering for MVP (ideally backend)
      if (filters.query || filters.type !== 'tous') {
        docs = docs.filter((d: any) => {
          const matchQuery = !filters.query || d.filename.toLowerCase().includes(filters.query.toLowerCase());
          const matchType = filters.type === 'tous' || d.document_type === filters.type;
          return matchQuery && matchType;
        });
      }
      
      setDocuments(docs);
    } catch {
      // Demo data
      setDocuments([
        { id: '1', filename: 'DTU 20.1 - Maçonnerie.pdf', document_type: 'dtu', project_name: 'Résidence Vert', lot: 'Gros Œuvre', status: 'indexed', date_indexed: new Date().toISOString(), num_chunks: 45, criticite: 'haute' },
        { id: '2', filename: 'Fiche AQC - ITE Enduit.pdf', document_type: 'fiche_technique', project_name: null, lot: 'Façade', status: 'indexed', date_indexed: new Date().toISOString(), num_chunks: 12, criticite: 'moyenne' },
        { id: '3', filename: 'Rapport Qualité 2025.pdf', document_type: 'rapport_chantier', project_name: 'Tour Bleue', lot: null, status: 'indexed', date_indexed: new Date().toISOString(), num_chunks: 78, criticite: 'haute' },
        { id: '4', filename: 'Cloison Placostil.pdf', document_type: 'fiche_technique', project_name: null, lot: 'Plâtrerie', status: 'indexed', date_indexed: new Date().toISOString(), num_chunks: 8, criticite: 'basse' },
        { id: '5', filename: 'CCTP Lot Plomberie.pdf', document_type: 'cctp', project_name: 'Résidence Vert', lot: 'Plomberie', status: 'indexed', date_indexed: new Date().toISOString(), num_chunks: 34, criticite: 'haute' },
      ]);
    }
    setLoading(false);
  }, [filters]);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  const handleDelete = async (id: string) => {
    if (!window.confirm('Êtes-vous sûr de vouloir supprimer ce document ?')) return;
    try {
      await deleteDocument(id);
      loadDocs();
    } catch (err) {
      alert('Erreur lors de la suppression');
    }
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    for (const file of Array.from(files)) {
      try {
        await uploadDocument(file);
      } catch { /* skip */ }
    }
    setUploading(false);
    loadDocs();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleUpload(e.dataTransfer.files);
  };

  const criticiteBadge = (c: string) => {
    if (c === 'haute' || c === 'critique') return 'badge-red';
    if (c === 'moyenne') return 'badge-amber';
    return 'badge-green';
  };

  const typeLabel = (t: string) => t.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-6 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Gestion Documentaire</h2>
          <p className="text-slate-400 mt-1">Upload, indexation et recherche de documents BTP</p>
        </div>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="btn-primary flex items-center gap-2"
          disabled={uploading}
        >
          <Upload size={16} /> Uploader
        </button>
        <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.txt,.xlsx" className="hidden" onChange={e => handleUpload(e.target.files)} />
      </div>

      {/* Search and Filter */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="relative col-span-2">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
          <input 
            type="text" 
            placeholder="Rechercher par nom de fichier..." 
            className="input-dark w-full pl-10"
            value={filters.query}
            onChange={e => setFilters(prev => ({ ...prev, query: e.target.value }))}
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
          <select 
            className="input-dark w-full pl-10 appearance-none capitalize"
            value={filters.type}
            onChange={e => setFilters(prev => ({ ...prev, type: e.target.value }))}
          >
            <option value="tous">Tous les types</option>
            <option value="dtu">DTU</option>
            <option value="norme_nf">Norme NF</option>
            <option value="fiche_technique">Fiche Technique</option>
            <option value="rapport_chantier">Rapport Chantier</option>
            <option value="cctp">CCTP</option>
          </select>
        </div>
      </div>

      {/* Drop Zone */}
      <div
        className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer ${
          dragOver ? 'border-btpGreen bg-btpGreen/5' : 'border-slate-700 hover:border-slate-500'
        }`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload size={32} className={`mx-auto mb-3 ${dragOver ? 'text-btpGreen' : 'text-slate-500'}`} />
        <p className="text-sm text-slate-400">
          {uploading ? 'Indexation en cours...' : 'Glissez-déposez vos fichiers BTP ou cliquez pour parcourir'}
        </p>
        <p className="text-xs text-slate-600 mt-1">PDF, DOCX, XLSX, TXT — Parsing automatique + enrichissement métadonnées</p>
      </div>

      {/* Documents Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider p-4">Document</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider p-4">Type</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider p-4">Lot</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider p-4">Chunks</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider p-4">Criticité</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider p-4">Status</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider p-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-btpCyan/10 flex items-center justify-center shrink-0">
                        <FileText size={16} className="text-btpCyan" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white truncate max-w-[240px]">{doc.filename}</p>
                        {doc.project_name && <p className="text-xs text-slate-500">{doc.project_name}</p>}
                      </div>
                    </div>
                  </td>
                  <td className="p-4"><span className="badge badge-cyan text-[11px]">{typeLabel(doc.document_type)}</span></td>
                  <td className="p-4 text-sm text-slate-400">{doc.lot || '—'}</td>
                  <td className="p-4 text-sm text-white font-medium">{doc.num_chunks}</td>
                  <td className="p-4"><span className={`badge ${criticiteBadge(doc.criticite)} text-[11px]`}>{doc.criticite}</span></td>
                  <td className="p-4"><span className="badge badge-green text-[11px]">{doc.status}</span></td>
                  <td className="p-4 text-right">
                    <button 
                      onClick={() => handleDelete(doc.id)}
                      className="p-2 text-slate-500 hover:text-btpRed hover:bg-btpRed/10 rounded-lg transition-colors"
                      title="Supprimer"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {loading && (
          <div className="p-8 text-center">
            <div className="w-8 h-8 border-2 border-btpGreen border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-sm text-slate-500">Chargement...</p>
          </div>
        )}
        {!loading && documents.length === 0 && (
          <div className="p-12 text-center">
            <FolderOpen size={40} className="text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400">Aucun document indexé</p>
            <p className="text-xs text-slate-600 mt-1">Uploadez votre premier document pour commencer</p>
          </div>
        )}
      </div>
    </div>
  );
}
