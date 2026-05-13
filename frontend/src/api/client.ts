/// <reference types="vite/client" />
/**
 * API Client — Centralized fetch wrapper for all backend calls.
 */

import type { 
  ChatResponse, 
  DocumentListResponse, 
  DashboardStats, 
  SystemHealth, 
  GraphOverview,
  ResourceListResponse,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Chat ──────────────────────────────────────────────────────────

export async function sendChatMessage(message: string, projectId?: string): Promise<ChatResponse> {
  return request<ChatResponse>('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message, project_id: projectId }),
  });
}

// ── Documents ─────────────────────────────────────────────────────

export async function getDocuments(page = 1, pageSize = 20): Promise<DocumentListResponse> {
  return request<DocumentListResponse>(`/api/documents/?page=${page}&page_size=${pageSize}`);
}

export async function uploadDocument(file: File, projectId?: string) {
  const formData = new FormData();
  formData.append('file', file);
  if (projectId) formData.append('project_id', projectId);

  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteDocument(docId: string): Promise<{ message: string }> {
  return request<{ message: string }>(`/api/documents/${docId}`, { method: 'DELETE' });
}

// ── Resources (RAG Knowledge Base Files) ──────────────────────────

export async function getResources(): Promise<ResourceListResponse> {
  return request<ResourceListResponse>('/api/resources/');
}

export async function uploadResource(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/resources/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteResource(filename: string): Promise<{ message: string }> {
  return request<{ message: string }>(`/api/resources/${encodeURIComponent(filename)}`, { method: 'DELETE' });
}

export async function ingestAllResources(): Promise<any> {
  return request<any>('/api/resources/ingest', { method: 'POST' });
}

export async function ingestSingleResource(filename: string): Promise<any> {
  return request<any>(`/api/resources/ingest/${encodeURIComponent(filename)}`, { method: 'POST' });
}

// ── Dashboard ─────────────────────────────────────────────────────

export async function getDashboardStats(): Promise<DashboardStats> {
  return request<DashboardStats>('/api/dashboard/stats');
}

export async function getSystemHealth(): Promise<SystemHealth> {
  return request<SystemHealth>('/api/health');
}

// ── Knowledge Graph ───────────────────────────────────────────────

export async function getKnowledgeOverview(): Promise<GraphOverview> {
  return request<GraphOverview>('/api/knowledge/overview');
}

export async function getGraphData(nodeId: string, nodeType = 'Document', depth = 2): Promise<any> {
  return request<any>(`/api/knowledge/graph/${nodeId}?node_type=${nodeType}&depth=${depth}`);
}

export async function getLatestGraphData(limit = 50): Promise<any> {
  return request<any>(`/api/knowledge/graph/latest?limit=${limit}`);
}

// ── Settings ──────────────────────────────────────────────────────

export async function getAllSettings(): Promise<Record<string, any>> {
  return request<Record<string, any>>('/api/settings/');
}

export async function saveSetting(key: string, value: any): Promise<any> {
  return request<any>('/api/settings/', {
    method: 'POST',
    body: JSON.stringify({ key, value }),
  });
}

