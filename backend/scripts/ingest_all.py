"""
Bulk ingestion script — Ingest all documents from the resources directory.
Run: python -m scripts.ingest_all
"""

import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.services.ingestion import ingest_directory


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Ingest resources PDFs
    resources_dir = os.path.join(base_dir, "resources")
    if os.path.exists(resources_dir):
        print(f"\n📁 Ingesting resources from: {resources_dir}")
        results = ingest_directory(resources_dir, project_id="demo", project_name="Démo BTP")
        print(f"✅ {len(results)} documents ingested from resources/")

    # Ingest Placo descriptifs
    placo_dir = os.path.join(base_dir, "Descriptifs_Types_Placo")
    if os.path.exists(placo_dir):
        print(f"\n📁 Ingesting Placo descriptifs from: {placo_dir}")
        results = ingest_directory(placo_dir, project_id="placo-2025", project_name="Descriptifs Placo 2025")
        print(f"✅ {len(results)} documents ingested from Descriptifs_Types_Placo/")

    print("\n🎉 Bulk ingestion complete!")


if __name__ == "__main__":
    main()
