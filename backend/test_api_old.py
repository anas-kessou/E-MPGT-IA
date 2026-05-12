import requests
import json
import time

API_URL = "http://localhost:8000/api/chat"

def test_chat_api():
    print("====================================")
    print("🚀 Démarrage du test de l'API BTP 🚀")
    print("====================================\n")
    
    payload = {
        "message": "Quelles sont les règles de base pour un mur en maçonnerie selon les DTU ?"
    }
    
    print(f"Envoi de la question au backend : '{payload['message']}'...")
    
    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Réponse reçue avec succès en {round(end_time - start_time, 2)} secondes !\n")
            print("🤖 Réponse de l'IA :")
            print(f"--------------------------------------------------")
            print(data.get("reply", "Pas de réponse"))
            print(f"--------------------------------------------------\n")
            
            print("📚 Sources utilisées :")
            sources = data.get("sources", [])
            if sources:
                for source in sources:
                    print(f"  - {source}")
            else:
                print("  Aucune source spécifique (ou la base de données vectorielle est vide).")
        else:
            print(f"\n❌ Erreur API: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Échec de connexion à {API_URL}")
        print("Assurez-vous d'avoir lancé le backend avec : cd backend && uvicorn main:app --reload")

if __name__ == "__main__":
    test_chat_api()