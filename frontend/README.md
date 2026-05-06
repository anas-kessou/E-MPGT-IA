# 🏗️ E-MPGT : Système IA BTP

![Status](https://img.shields.io/badge/Status-MVP_Hackathon-success)
![React](https://img.shields.io/badge/Frontend-React_Vite-blue)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)
![AI](https://img.shields.io/badge/IA-LangChain_%7C_OpenAI-orange)
![DB](https://img.shields.io/badge/Vector_DB-ChromaDB-purple)

> **Projet réalisé dans le cadre du Challenge E-MPGT (MVP développé en 24h).**  
> Ce système transforme l'ensemble des données internes et externes du BTP en décisions opérationnelles grâce à une mémoire intelligente, un moteur d'analyse métier et un système d'automatisation.

---

## 🎯 Objectif du Projet

Dans le secteur du BTP, l'information (DTU, normes NF, comptes rendus de chantier, fiches techniques) est dispersée et non structurée. 
**Notre solution** est un système d'Intelligence Artificielle à 3 couches capable de :
1. **Centraliser** toutes les données BTP.
2. **Intégrer** la connaissance métier stricte sans hallucination (RAG sourcé).
3. **Automatiser** les décisions et workflows (génération de rapports, alertes de conformité).

---

## 🏛️ Architecture à 3 Couches

L'architecture respecte strictement le cahier des charges E-MPGT, en passant d'une preuve de concept à un MVP fonctionnel.

```mermaid
graph TD
    subgraph Couche 3 : Exécution (Action)
        UI[Interface React / Chat]
        N8N[Moteur de Workflow - n8n]
    end

    subgraph Couche 2 : IA (Intelligence)
        API[API FastAPI]
        RAG[Moteur RAG - LangChain]
        LLM[GPT-4o-mini]
    end

    subgraph Couche 1 : Data (Fondation)
        VDB[(Base Vectorielle : ChromaDB)]
        PDF[PDFs : DTU, Fiches AQC, Plans]
        EMB[text-embedding-3-small]
    end

    UI <-->|Requêtes & Citations| API
    N8N -->|Emails/Alertes| API
    API <--> RAG
    RAG <-->|Contexte métier| LLM
    RAG <-->|Recherche Sémantique| VDB
    PDF -->|Ingestion & Split| EMB
    EMB -->|Stockage| VDB
```

---

## ✨ Fonctionnalités Clés (Killer Features)

- 🧠 **RAG (Retrieval-Augmented Generation) Expert** : L'IA ne devine pas, elle lit les documents stockés.
- 📎 **Citations Strictes** : Chaque réponse réglementaire fournie par l'IA indique la source exacte du document (ex: *DTU 20.1 - Maçonnerie*).
- ⚡ **Interface Temps Réel** : Une UI fluide en React/Tailwind simulant l'environnement de travail d'un ingénieur ou conducteur de travaux.
- ⚙️ **Automatisation (Couche 3)** : Connexion possible avec `n8n` pour écouter des requêtes entrantes (ex: un email de non-conformité sur chantier) et générer automatiquement une recommandation basée sur les DTU.

---

## 🛠️ Stack Technique

### Backend (Python)
* **Framework :** FastAPI (pour sa rapidité et son asynchronisme).
* **Orchestration IA :** LangChain.
* **Vector Store :** ChromaDB (choisi pour le MVP local car il ne nécessite pas d'infrastructure lourde contrairerement à pgvector, garantissant un déploiement en 24h).
* **Modèles (OpenAI) :** `text-embedding-3-small` (pour la vectorisation) et `gpt-4o-mini` (pour le raisonnement).

### Frontend (JavaScript)
* **Framework :** React.js propulsé par Vite.
* **Styling :** Tailwind CSS (UI calquée sur la charte graphique E-MPGT : Vert et Bleu marine).
* **Icônes & Markdown :** Lucide-React & React-Markdown.

---

## 🚀 Installation & Lancement en Local

### Prérequis
* Node.js (v18+)
* Python (3.10+)
* Une clé API OpenAI (`OPENAI_API_KEY`)

### 1. Cloner le projet
```bash
git clone https://github.com/votre-nom/e-mpgt-ai-btp.git
cd e-mpgt-ai-btp
```

### 2. Lancer le Backend (API & IA)
```bash
cd backend
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # (Sur Windows: venv\Scripts\activate)

# Installer les dépendances
pip install -r requirements.txt

# Configurer la clé API (Créer un fichier .env)
echo "OPENAI_API_KEY=sk-votre-cle-openai" > .env

# (Optionnel) Ingestion initiale des données pour remplir ChromaDB
python ingest.py

# Lancer le serveur
uvicorn main:app --reload --port 8000
```
*L'API sera disponible sur : `http://localhost:8000`*

### 3. Lancer le Frontend (UI)
Ouvrez un nouveau terminal :
```bash
cd frontend
# Installer les dépendances
npm install

# Lancer le serveur de développement
npm run dev
```
*L'interface sera disponible sur : `http://localhost:5173`*

---

## 📂 Structure des Données (Exemple MVP)

Pour ce MVP, la base vectorielle a été entraînée sur des documents métiers publics représentatifs :
* **Fiches AQC** (Agence Qualité Construction) : Prévention des pathologies et erreurs de chantier.
* **Extraits de DTU** (Document Technique Unifié) : Règles de l'art pour la construction traditionnelle.

---

## 🔭 Évolutions futures (V2 pour la Production)

Étant donné la contrainte de temps (MVP), des raccourcis techniques ont été pris. Pour un passage en production, nous prévoyons :
1. **Migration Base de Données :** Remplacement de ChromaDB par **PostgreSQL 15 + pgvector** avec SQLAlchemy/Alembic pour une robustesse et un filtrage strict par métadonnées (ID Projet, Auteur).
2. **Parsing Avancé :** Remplacement du loader PDF standard par **Docling** ou **LlamaParse** pour comprendre la structure complexe des tableaux dans les normes NF et devis.
3. **Agentic Workflows :** Implémentation de LangGraph pour créer des agents IA capables de déclencher des appels API vers des ERP/CRM (ex: Procore, Jira) de manière autonome.

---
**Développé avec ❤️ pour le Challenge E-MPGT.**