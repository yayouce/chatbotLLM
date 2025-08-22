# api_server.py
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import uuid
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

# --- 1. Importations des Composants du Projet ---
# On importe les configurations et les prompts
import root_config
from prompts import SYSTEM_PROMPT_TEXT

# On importe les outils de manière séparée
from app_tools.database_tools import (
    get_transaction_details, find_transactions_by_criteria, get_transaction_summary,
    get_wallet_notification_stats, get_pending_transactions_count,
    get_top_active_phone_numbers, find_transaction_by_any_reference
)
# On importe la FONCTION d'initialisation et l'OUTIL du module RAG
from app_tools.rag_tools import search_application_logs
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
# On importe les composants de l'agent depuis le fichier principal
# Assurez-vous que le nom du fichier est correct (ex: `main` ou `agentcombine`)
from main import GatewaySupportAgent, AgentState

# On importe le LLM
from langchain_groq import ChatGroq
agent_executor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gère l'initialisation des ressources lourdes au démarrage de l'application.
    """
    global agent_executor 

    print("--- DÉMARRAGE DE L'API ---")
    
    # 1. Initialiser les composants RAG (qui sont lourds)
    print("1. Initialisation des composants RAG (ChromaDB, Embeddings)...")
    # 2. Initialiser le LLM
    print("2. Initialisation du LLM (ChatGroq)...")
    llm = ChatGroq(
        groq_api_key=root_config.GROQ_API_KEY,
        model_name=root_config.MODEL_NAME_GROQ,
        temperature=0.0
    )
    
    # 3. Assembler la liste complète des outils
    print("3. Assemblage de la boîte à outils de l'agent...")
    database_tools = [
        get_transaction_details, find_transactions_by_criteria, get_transaction_summary,
        get_wallet_notification_stats, get_pending_transactions_count,
        get_top_active_phone_numbers, find_transaction_by_any_reference
    ]
    rag_tool_list = [search_application_logs]
    all_tools = database_tools + rag_tool_list

    # 4. Créer et compiler l'agent
    print("4. Création et compilation de l'agent LangGraph...")
    agent = GatewaySupportAgent(llm, all_tools, system_prompt=SYSTEM_PROMPT_TEXT)
    agent_executor = agent.graph
    
    print("✅ Initialisation terminée. L'agent est prêt.")
    
    # Le 'yield' signale à FastAPI que le démarrage est terminé.
    yield
    
    # --- Actions à l'Arrêt (optionnel) ---
    print("--- ARRÊT DE L'API ---")
    # Ici, on pourrait ajouter du code pour fermer proprement des connexions si nécessaire.


# --- 4. Création de l'Application FastAPI ---
app = FastAPI(
    title="NGBOT Assist API",
    description="API pour interagir avec l'agent conversationnel hybride (SQL + RAG).",
    version="1.1.0",
    lifespan=lifespan  # On lie notre gestionnaire de cycle de vie à l'application
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], # Autorise toutes les méthodes (GET, POST, etc.)
    allow_headers=["*"], # Autorise tous les headers
)

# --- 5. Définition des Modèles de Données (Contrats d'API) ---
class ChatRequest(BaseModel):
    user_input: str
    conversation_id: str | None = None

class ChatResponse(BaseModel):
    ai_response: str
    conversation_id: str

# --- 6. Création du Endpoint API ---
@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Reçoit une question de l'utilisateur et un ID de conversation (optionnel).
    Invoque l'agent de manière asynchrone et retourne sa réponse.
    """
    if agent_executor is None:
        raise HTTPException(status_code=503, detail="L'agent n'est pas encore initialisé. Veuillez patienter.")

    # Si aucun ID de conversation n'est fourni, on en génère un nouveau.
    conversation_id = request.conversation_id or f"api-session-{uuid.uuid4()}"
    print(f"INFO: Requête reçue pour la conversation '{conversation_id}'")
    
    conversation_config = {"configurable": {"thread_id": conversation_id}}
    
    try:
     
        user_message = HumanMessage(content=request.user_input)
        final_state = await agent_executor.ainvoke(
            {"messages": [user_message]},
            config=conversation_config
        )


        # La réponse finale est toujours le dernier message dans l'état du graphe.
        ai_response_content = final_state['messages'][-1].content
        
        print(f"INFO: Réponse générée pour la conversation '{conversation_id}'")
        
        return ChatResponse(
            ai_response=ai_response_content,
            conversation_id=conversation_id
        )
    except Exception as e:
        print(f" ERREUR lors du traitement de la requête pour l'ID {conversation_id}: {e}")
        import traceback
        traceback.print_exc() # Affiche la trace complète de l'erreur dans la console du serveur
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur lors du traitement de votre demande.")


if __name__ == "__main__":
    # Cette commande permet de lancer le serveur facilement avec `python api_server.py`
    # L'option --reload est très pratique car elle redémarre le serveur à chaque modification du code.
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)