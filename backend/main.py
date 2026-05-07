import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Configuration (Mettez votre clé dans un .env en réalité)
os.environ["GOOGLE_API_KEY"] = "AIzaSyAI6bj411QOU-wAU7a7wOxkjbfbI8hoMUM"

app = FastAPI(title="MVP IA BTP")

# Indispensable si le Frontend est en React (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En prod, mettre "http://localhost:3000" ou http://localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Initialisation IA avec GEMINI
embeddings = GoogleGenerativeAIEmbeddings(model="text-embedding-001")

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash", 
    temperature=0,
    # # Optionnel: baisser les filtres de sécurité pour le BTP
    # safety_settings={
    #     "HARASSMENT": "BLOCK_NONE",
    #     "HATE_SPEECH": "BLOCK_NONE",
    #     "SEXUALLY_EXPLICIT": "BLOCK_NONE",
    #     "DANGEROUS_CONTENT": "BLOCK_NONE",
    # }
)

# Connecter Chroma (assurez-vous d'avoir ingéré des données avant dans "./chroma_db")
vector_store = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
retriever = vector_store.as_retriever(search_kwargs={"k": 3})

# Prompt métier BTP
system_prompt = (
    "Tu es un assistant expert en BTP et réglementations (DTU). "
    "Utilise uniquement les documents fournis pour répondre. "
    "Si tu ne sais pas, dis-le. Cite toujours tes sources à la fin.\n\n"
    "Contexte: {context}"
)
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

# 2. Modèle de donnée API
class ChatRequest(BaseModel):
    message: str

# 3. Route API
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        response = rag_chain.invoke({"input": request.message})
        # Formatage de la réponse pour extraire les sources
        sources = [doc.metadata.get('source', 'Inconnue') for doc in response["context"]]
        
        return {
            "reply": response["answer"],
            "sources": list(set(sources)) # Suppression des doublons
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
