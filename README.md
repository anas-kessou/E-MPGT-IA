# 🏗️ E-MPGT-IA — Système IA BTP

![Version](https://img.shields.io/badge/Version-2.0-success)
![Architecture](https://img.shields.io/badge/Architecture-3_Couches-blue)
![Stack](https://img.shields.io/badge/Stack-FastAPI_|_LangGraph_|_Qdrant_|_Neo4j-orange)
![Frontend](https://img.shields.io/badge/Frontend-React_|_Vite_|_Tailwind-purple)

> **Système IA BTP Production** — Base vectorielle · Intelligence métier · Automatisation des opérations.
> Transforme l'ensemble des données internes et externes du BTP en décisions opérationnelles.

---

## 🏛️ Architecture à 3 Couches

```
┌──────────────────────────────────────────────────────────────┐
│                  COUCHE 3 — EXÉCUTION                        │
│  React Dashboard · Chat IA · Gestion Docs · Knowledge Graph │
│  n8n Workflows · Webhooks · Human-in-the-Loop               │
├──────────────────────────────────────────────────────────────┤
│                  COUCHE 2 — INTELLIGENCE IA                  │
│  LangGraph Multi-Agents · RAG Avancé (Multi-Query)          │
│  Agent Conformité DTU · Agent Synthèse · Superviseur        │
├──────────────────────────────────────────────────────────────┤
│                  COUCHE 1 — DATA FOUNDATION                  │
│  Qdrant (Vecteurs) · Neo4j (Knowledge Graph)                │
│  PostgreSQL (Métadonnées) · MinIO (Documents S3)            │
│  Pipeline d'ingestion : OCR + Parsing + Enrichissement      │
└──────────────────────────────────────────────────────────────┘
```

## ✨ Fonctionnalités

- 🧠 **RAG Avancé** — Multi-query rewriting + compression contextuelle + GraphRAG
- 🤖 **Multi-Agents LangGraph** — Superviseur → RAG → Conformité → Synthèse
- ✅ **Vérification DTU/Normes** — LLM-as-a-Judge pour la conformité réglementaire
- 📊 **Dashboard Premium** — KPIs, activité, status des sources en temps réel
- 📁 **Gestion Documentaire** — Upload drag & drop, indexation auto, métadonnées enrichies
- 🕸️ **Knowledge Graph** — Exploration visuelle des relations projets/normes/documents
- 📎 **Citations Strictes** — Chaque réponse cite ses sources avec numéro de page
- 🔒 **Traçabilité Complète** — Audit logs de toutes les requêtes

## 🛠️ Stack Technique

| Composant | Technologie |
|:----------|:-----------|
| **API** | FastAPI (Python) |
| **Agents IA** | LangGraph (Supervisor + RAG + Conformité) |
| **LLM** | Gemini 2.0 Flash |
| **Embeddings** | Google text-embedding-004 |
| **Vector DB** | Qdrant (recherche sémantique + filtres) |
| **Knowledge Graph** | Neo4j (relations projets/normes) |
| **Métadonnées** | PostgreSQL + pgvector |
| **Stockage Docs** | MinIO (S3 compatible + versioning) |
| **Workflows** | n8n (automatisation) |
| **Frontend** | React + Vite + Tailwind CSS |

## 🚀 Lancement Rapide

### 1. Démarrer l'infrastructure

```bash
docker compose up -d
```

Services disponibles :
- Qdrant: http://localhost:6333/dashboard
- Neo4j: http://localhost:7474
- MinIO Console: http://localhost:9001
- n8n: http://localhost:5678

### 2. Lancer le Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Ajoutez votre GOOGLE_API_KEY
uvicorn app.main:app --reload --port 8000
```

API disponible sur : http://localhost:8000

### 3. Ingérer les documents existants

```bash
cd backend
python -m scripts.ingest_all
```

### 4. Lancer le Frontend

```bash
cd frontend
npm install
npm run dev
```

Interface disponible sur : http://localhost:3000

## 📂 Structure du Projet

```
E-MPGT-IA/
├── docker-compose.yml          # Infrastructure complète
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── config.py           # Configuration centralisée
│   │   ├── models/             # Pydantic schemas
│   │   ├── routers/            # API endpoints
│   │   ├── services/           # Business logic
│   │   ├── agents/             # LangGraph agents
│   │   └── database/           # Database clients
│   ├── scripts/                # Ingestion & migration
│   ├── resources/              # Documents BTP (PDFs)
│   └── Dockerfile
└── frontend/
    └── src/
        ├── App.tsx             # Multi-page application
        ├── api/client.ts       # API client
        ├── types/index.ts      # TypeScript types
        └── index.css           # Design system
```

## 📋 Endpoints API

| Méthode | Endpoint | Description |
|:--------|:---------|:-----------|
| POST | `/api/chat` | Chat IA avec RAG + conformité |
| GET | `/api/documents/` | Liste des documents indexés |
| POST | `/api/documents/upload` | Upload + ingestion d'un document |
| GET | `/api/knowledge/overview` | Stats du knowledge graph |
| GET | `/api/health` | Status de tous les services |
| GET | `/api/dashboard/stats` | KPIs agrégés |

---

**E-MPGT-IA v2.0 — Production-Ready BTP AI System**
