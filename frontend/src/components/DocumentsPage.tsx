import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Upload, Search, Filter, FileText, Trash2, FolderOpen, Database, Play, Loader2, CheckCircle2, HardDrive, Plus } from 'lucide-react';
import { getDocuments, uploadDocument, deleteDocument, getResources, uploadResource, deleteResource, ingestAllResources, ingestSingleResource } from '../api/client';
import { DocumentItem, DocumentFilters, ResourceFile } from '../types';

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [resources, setResources] = useState<ResourceFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingResources, setLoadingResources] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadingResource, setUploadingResource] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [ingestingFile, setIngestingFile] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [filters, setFilters] = useState<DocumentFilters>({ query: '', type: 'tous' });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const resourceInputRef = useRef<HTMLInputElement>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // ── Load Resources ────────────────────────────────────────────────
  const loadResources = useCallback(async () => {
    setLoadingResources(true);
    try {
      const data = await getResources();
      setResources(data.resources || []);
    } catch {
      setResources([]);
    }
    setLoadingResources(false);
  }, []);

  // ── Load Documents ────────────────────────────────────────────────
  const loadDocs = useCallback(async () => {
    try {
      const data = await getDocuments();
      let docs = data.documents || [];
      
      if (filters.query || filters.type !== 'tous') {
        docs = docs.filter((d: any) => {
          const matchQuery = !filters.query || d.filename.toLowerCase().includes(filters.query.toLowerCase());
          const matchType = filters.type === 'tous' || d.document_type === filters.type;
          return matchQuery && matchType;
        });
      }
      
      setDocuments(docs);
    } catch {
      setDocuments([]);
    }
    setLoading(false);
  }, [filters]);

  useEffect(() => { loadDocs(); loadResources(); }, [loadDocs, loadResources]);

  // ── Document Handlers ─────────────────────────────────────────────
  const handleDelete = async (id: string) => {
    if (!window.confirm('Êtes-vous sûr de vouloir supprimer ce document ?')) return;
    try {
      await deleteDocument(id);
      showToast('Document supprimé');
      loadDocs();
    } catch {
      showToast('Erreur lors de la suppression', 'error');
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
    showToast(`${files.length} document(s) uploadé(s)`);
    loadDocs();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleUpload(e.dataTransfer.files);
  };

  // ── Resource Handlers ─────────────────────────────────────────────
  const handleResourceUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploadingResource(true);
    for (const file of Array.from(files)) {
      try {
        await uploadResource(file);
      } catch (err: any) {
        showToast(`Erreur: ${err.message}`, 'error');
      }
    }
    setUploadingResource(false);
    showToast(`Fichier(s) ajouté(s) aux ressources`);
    loadResources();
  };

  const handleResourceDelete = async (filename: string) => {
    if (!window.confirm(`Supprimer "${filename}" des ressources ?`)) return;
    try {
      await deleteResource(filename);
      showToast('Ressource supprimée');
      loadResources();
    } catch {
      showToast('Erreur lors de la suppression', 'error');
    }
  };

  const handleIngestAll = async () => {
    setIngesting(true);
    try {
      const result = await ingestAllResources();
      showToast(result.message || 'Ingestion terminée');
      loadResources();
      loadDocs();
    } catch (err: any) {
      showToast(`Erreur: ${err.message}`, 'error');
    }
    setIngesting(false);
  };

  const handleIngestSingle = async (filename: string) => {
    setIngestingFile(filename);
    try {
      const result = await ingestSingleResource(filename);
      showToast(result.message || `${filename} ingéré`);
      loadResources();
      loadDocs();
    } catch (err: any) {
      showToast(`Erreur: ${err.message}`, 'error');
    }
    setIngestingFile(null);
  };

  // ── Helpers ───────────────────────────────────────────────────────
  const criticiteBadge = (c: string) => {
    if (c === 'haute' || c === 'critique') return 'badge-red';
    if (c === 'moyenne') return 'badge-amber';
    return 'badge-green';
  };

  const typeLabel = (t: string) => t.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  const getFileIcon = (ext: string) => {
    if (ext === '.pdf') return '📄';
    if (ext === '.docx' || ext === '.doc') return '📝';
    if (ext === '.xlsx') return '📊';
    if (ext === '.txt') return '📃';
    return '📎';
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-6 fade-in">
      {/* Toast Notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-5 py-3 rounded-xl shadow-lg text-sm font-medium fade-in ${
          toast.type === 'success' 
            ? 'bg-btpGreen/20 text-btpGreen border border-btpGreen/30' 
            : 'bg-btpRed/20 text-btpRed border border-btpRed/30'
        }`}>
          {toast.message}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════
          SECTION 1: RAG RESOURCES (Knowledge Base Files)
         ════════════════════════════════════════════════════════════════ */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <HardDrive size={24} className="text-btpCyan" />
              Ressources RAG
            </h2>
            <p className="text-slate-400 mt-1">Fichiers sources de la base de connaissances — {resources.length} fichier{resources.length > 1 ? 's' : ''}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleIngestAll}
              disabled={ingesting || resources.length === 0}
              className="btn-secondary flex items-center gap-2 text-sm"
            >
              {ingesting ? <Loader2 size={14} className="animate-spin" /> : <Database size={14} />}
              {ingesting ? 'Ingestion...' : 'Ingérer Tout'}
            </button>
            <button
              onClick={() => resourceInputRef.current?.click()}
              disabled={uploadingResource}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Plus size={14} />
              Ajouter
            </button>
            <input
              ref={resourceInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.xlsx"
              className="hidden"
              onChange={e => handleResourceUpload(e.target.files)}
            />
          </div>
        </div>

        {/* Resources Grid */}
        {loadingResources ? (
          <div className="glass-card p-8 text-center">
            <div className="w-8 h-8 border-2 border-btpCyan border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-sm text-slate-500">Chargement des ressources...</p>
          </div>
        ) : resources.length === 0 ? (
          <div className="glass-card p-8 text-center">
            <HardDrive size={36} className="text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400">Aucune ressource trouvée</p>
            <p className="text-xs text-slate-600 mt-1">Ajoutez des fichiers PDF, DOCX, TXT ou XLSX</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {resources.map((res) => (
              <div
                key={res.filename}
                className="glass-card p-4 glass-card-hover group relative"
              >
                <div className="flex items-start gap-3">
                  <div className="text-2xl shrink-0 mt-0.5">{getFileIcon(res.extension)}</div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-white truncate" title={res.filename}>
                      {res.filename}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-slate-500">{res.size_display}</span>
                      <span className="text-xs text-slate-700">•</span>
                      <span className="text-xs text-slate-500 uppercase">{res.extension.replace('.', '')}</span>
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      {res.ingested ? (
                        <span className="badge badge-green text-[10px]">
                          <CheckCircle2 size={10} /> Ingéré
                        </span>
                      ) : (
                        <span className="badge badge-amber text-[10px]">
                          En attente
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Actions overlay */}
                <div className="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {!res.ingested && (
                    <button
                      onClick={() => handleIngestSingle(res.filename)}
                      disabled={ingestingFile === res.filename}
                      className="p-1.5 text-btpCyan hover:bg-btpCyan/10 rounded-lg transition-colors"
                      title="Ingérer ce fichier"
                    >
                      {ingestingFile === res.filename
                        ? <Loader2 size={14} className="animate-spin" />
                        : <Play size={14} />
                      }
                    </button>
                  )}
                  <button
                    onClick={() => handleResourceDelete(res.filename)}
                    className="p-1.5 text-slate-500 hover:text-btpRed hover:bg-btpRed/10 rounded-lg transition-colors"
                    title="Supprimer"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-slate-800" />

      {/* ════════════════════════════════════════════════════════════════
          SECTION 2: INDEXED DOCUMENTS
         ════════════════════════════════════════════════════════════════ */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Documents Indexés</h2>
          <p className="text-slate-400 mt-1">Documents traités et vectorisés dans le pipeline RAG</p>
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
            <p className="text-xs text-slate-600 mt-1">Uploadez un document ou ingérez les ressources ci-dessus</p>
          </div>
        )}
      </div>
    </div>
  );
}
