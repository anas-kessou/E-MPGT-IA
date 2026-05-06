import os
import glob
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

os.environ["OPENAI_API_KEY"] = "sk-votre-cle-openai"

def ingest_pdf(file_path):
    print(f"Chargement de {file_path}...")
    loader = PyPDFLoader(file_path)
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    print("Création des vecteurs et sauvegarde dans Chroma...")
    Chroma.from_documents(
        documents=splits,
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        persist_directory="./chroma_db"
    )
    print("Terminé !")

if __name__ == "__main__":
    # Ingestion test pdf
    # ingest_pdf("../Fiche-Maitrise-Ouvrage-Professionnelle-Douches-Zero-Ressaut-Neufs-AQC.pdf")
    pass
