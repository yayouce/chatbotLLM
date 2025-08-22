# import os
# from langchain_core.tools import tool
# from langchain_groq import ChatGroq

# from langchain_community.vectorstores import Chroma
# from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain.retrievers.self_query.base import SelfQueryRetriever
# from langchain.chains.query_constructor.base import AttributeInfo



# #bd vectorielle
# VECTOR_DB_PATH = "log_db_advanced"

# # --- Initialisation ---
# # Cette partie est exécutée une seule fois quand le module est importé.
# print("INFO: Initialisation des composants RAG (recherche de logs)...")
# embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# if not os.path.exists(VECTOR_DB_PATH):
#     raise FileNotFoundError(f"Le dossier '{VECTOR_DB_PATH}' est introuvable à la racine du projet. Veuillez exécuter indexer.py.")

# vectorstore = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embedding_function)
# llm_for_retriever = ChatGroq(model_name="llama3-8b-8192", temperature=0)

# # Description des métadonnées
# metadata_field_info = [
#     AttributeInfo(name="context_id", description="L'identifiant unique (tel que momo_id, transaction_id, etc.) qui relie plusieurs logs concernant une même transaction.", type="string"),
#     AttributeInfo(name="log_type", description="Le type de log, comme 'sql_query', 'request_start', 'http_call_out', 'parameters'.", type="string"),
#     AttributeInfo(name="level", description="Le niveau de criticité du log: 'INFO', 'DEBUG', 'ERROR', etc.", type="string"),
# ]
# document_content_description = "Le contenu brut d'une ligne de log d'une application."

# # Création du retriever intelligent
# retriever = SelfQueryRetriever.from_llm(
#     llm_for_retriever, 
#     vectorstore, 
#     document_content_description, 
#     metadata_field_info, 
#     verbose=True
# )

# @tool
# def search_application_logs(query: str) -> str:
#     """
#     À utiliser pour rechercher des informations dans les logs de l'application afin de comprendre le déroulement d'une action ou de diagnostiquer un comportement inattendu.
#     Ne l'utilise PAS pour des informations financières précises ou des statuts de paiement, préfère les outils de base de données pour cela.
#     """
#     print(f"DEBUG: [RAG Tool] Recherche dans les logs pour: '{query}'")
#     docs = retriever.invoke(query)
#     if not docs:
#         return "Aucune information pertinente trouvée dans les logs pour cette requête."
    
#     return "\n\n---\n\n".join([f"Source Log: {doc.page_content}" for doc in docs])




# app_tools/rag_tools.py (Version enrichie pour les "histoires de transactions")

# import os
# from langchain_core.tools import tool
# from langchain_groq import ChatGroq
# from langchain_community.vectorstores import Chroma
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain.retrievers.self_query.base import SelfQueryRetriever
# from langchain.chains.query_constructor.base import AttributeInfo


# # --- 1. Import de la configuration ---

# VECTOR_DB_PATH = "../log_db_advanced"
# retriever = None

# # --- 3. Fonction d'Initialisation (pour être appelée par l'API) ---
# def initialize_rag_retriever():
#     """
#     Initialise tous les composants RAG pour l'interrogation des histoires de transactions.
#     """
#     global retriever
#     print("INFO: Initialisation des composants RAG (Histoires de Transactions)...")

#     if not os.path.exists(VECTOR_DB_PATH):
#         raise FileNotFoundError(f"Le dossier de la base de données RAG '{VECTOR_DB_PATH}' est introuvable. Veuillez exécuter le script d'indexation.")

#     embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
#     vectorstore = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embedding_function)
#     llm_for_retriever = ChatGroq(model_name="llama3-8b-8192", temperature=0)

#     # --- ENRICHISSEMENT DES MÉTRADONNÉES ---
#     # C'est la partie la plus importante. On décrit notre nouvelle structure de données.
#     metadata_field_info = [
#         AttributeInfo(
#             name="transaction_id", 
#             description="L'identifiant unique de la transaction complète. Souvent appelé 'context_id', 'momo_id', ou 'order_id'.", 
#             type="string"
#         ),
#         AttributeInfo(
#             name="final_status", 
#             description="Le statut final déduit de la transaction. Peut être 'SUCCESS', 'FAILURE', ou 'UNKNOWN'.", 
#             type="string"
#         ),
#         AttributeInfo(
#             name="start_time", 
#             description="Le timestamp du premier log associé à cette transaction.", 
#             type="string"
#         ),
#         AttributeInfo(
#             name="end_time", 
#             description="Le timestamp du dernier log associé à cette transaction.", 
#             type="string"
#         ),
#         AttributeInfo(
#             name="log_count", 
#             description="Le nombre total de lignes de log qui composent l'histoire de cette transaction.", 
#             type="integer"
#         ),
#     ]
#     # La description du contenu change également pour refléter la nouvelle structure.
#     document_content_description = "L'histoire complète d'une transaction, constituée de la concaténation de toutes les lignes de log associées, ordonnées chronologiquement."

#     # Création du retriever intelligent avec les nouvelles descriptions
#     retriever = SelfQueryRetriever.from_llm(
#         llm_for_retriever, 
#         vectorstore, 
#         document_content_description, 
#         metadata_field_info, 
#         verbose=True
#     )
#     print("✅ Composants RAG (Histoires de Transactions) initialisés.")


# # --- 4. Définition de l'Outil (mis à jour) ---
# @tool
# def search_application_logs(query: str) -> str:
#     """
#     À utiliser pour rechercher l'HISTOIRE COMPLÈTE d'une ou plusieurs transactions dans les logs.
#     Cet outil est idéal pour comprendre le déroulement chronologique d'une opération, diagnostiquer une erreur en ayant tout le contexte, ou répondre à des questions complexes sur le comportement d'une transaction.
#     Ne l'utilise PAS pour des statistiques globales (préfère les outils de base de données pour cela).
#     """
#     if retriever is None:
#         return "Erreur critique: Le moteur de recherche dans les logs (RAG) n'est pas initialisé."

#     print(f"DEBUG: [RAG Tool] Recherche d'histoires de transaction pour: '{query}'")
#     try:
#         docs = retriever.invoke(query)
#         if not docs:
#             return "Aucune histoire de transaction correspondante n'a été trouvée dans les logs pour cette requête."
        
#         # On peut retourner jusqu'à 3 histoires complètes pour donner un contexte riche au LLM
#         return "\n\n--- HISTOIRE DE TRANSACTION TROUVÉE ---\n\n".join(
#             [f"**Transaction ID:** {doc.metadata.get('transaction_id', 'N/A')}\n**Statut Final:** {doc.metadata.get('final_status', 'N/A')}\n\n**Logs complets:**\n{doc.page_content}" for doc in docs[:3]]
#         )
#     except Exception as e:
#         print(f"ERREUR dans le retriever RAG: {e}")
#         return "Une erreur est survenue lors de la recherche dans les logs."





# app_tools/rag_tools.py

import os
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains.query_constructor.base import AttributeInfo

# --- 1. Importation de la configuration centralisée ---
# Cette approche est plus robuste et évite les chemins en dur.
try:
    from root_config import VECTOR_DB_PATH
except ImportError:
    print("WARN: root_config.py non trouvé. Utilisation d'un chemin par défaut pour la DB RAG.")
    VECTOR_DB_PATH = "log_db_advanced"

# --- 2. Déclaration des variables globales ---
# On les déclare ici mais on ne les initialise PAS.
# Elles seront créées par la fonction d'initialisation.
retriever = None

# --- 3. Fonction d'Initialisation (le cœur de la solution) ---
def initialize_rag_components():
    """
    Initialise tous les composants lourds du RAG.
    Cette fonction est conçue pour être appelée UNE SEULE FOIS au démarrage de l'application.
    """
    global retriever
    print("INFO: Démarrage de l'initialisation des composants RAG...")

    # Vérification critique de l'existence de la base de données
    if not os.path.exists(VECTOR_DB_PATH):
        raise FileNotFoundError(
            f"Le dossier de la base de données RAG '{VECTOR_DB_PATH}' est introuvable. "
            f"Veuillez exécuter le script d'indexation (indexer.py) d'abord."
        )

    # Chargement des composants
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embedding_function)
    
  
    llm_for_retriever = ChatGroq(model_name="llama3-70b-8192", temperature=0)

    # --- DESCRIPTION ENRICHIE DES MÉTRADONNÉES ---
    # C'est le "guide" pour le LLM du retriever. Plus il est précis, meilleurs sont les résultats.
    metadata_field_info = [
        AttributeInfo(
            name="context_id", 
            description="L'identifiant de transaction unique qui relie tous les logs d'une même opération. L'utilisateur peut l'appeler 'transaction_id', 'order_id', 'token', ou simplement 'ID'. C'est le champ le plus important pour filtrer les logs d'une transaction spécifique.",
            type="string"
        ),
        AttributeInfo(
            name="log_type", 
            description="Le type de log, comme 'sql_query', 'request_start', 'parameters', 'request_completed', 'external_request', 'external_response'. Utile pour filtrer sur des types d'événements.",
            type="string"
        ),
        AttributeInfo(
            name="level", 
            description="Le niveau de criticité du log: 'INFO', 'DEBUG', 'ERROR'.", 
            type="string"
        ),
        AttributeInfo(
            name="semantic_status", 
            description="Un statut général déduit du contenu du log, peut être 'SUCCESS' ou 'FAILURE'. Utile pour trouver les transactions réussies ou échouées.", 
            type="string"
        ),
        # Ajoutez ici d'autres champs importants que votre parser extrait...
    ]
    document_content_description = "Le contenu brut d'une ligne de log d'une application de paiement. Chaque ligne représente un événement ponctuel dans le cycle de vie d'une transaction."

    # Création du retriever intelligent final
    retriever = SelfQueryRetriever.from_llm(
        llm=llm_for_retriever, 
        vectorstore=vectorstore, 
        document_contents=document_content_description, 
        metadata_field_info=metadata_field_info, 
        verbose=True # voir les requêtes généré
    )
    print("✅ Composants RAG initialisés avec succès.")


#Définition de l'Outil Exposé à l'Agent ---
@tool
def search_application_logs(query: str) -> str:
    """
    À utiliser pour rechercher des informations contextuelles et de diagnostic dans les logs bruts de l'application.
    Cet outil est le meilleur choix pour répondre aux questions sur le "pourquoi" et le "comment" : "Pourquoi cette transaction a échoué ?", "Quelles étapes ont été suivies pour l'ID X ?", "Montre-moi les erreurs liées au contrôleur Y".
    Ne l'utilise PAS pour des données financières agrégées (totaux, comptes) ; préfère les outils de base de données pour cela.
    """
    global retriever #si je veux changer la valeur d'une variable globale dans une fonction
    if retriever is None:
        return "Erreur critique: Le moteur de recherche dans les logs (RAG) n'a pas été initialisé. L'application a peut-être un problème de démarrage."

    print(f"DEBUG: [RAG Tool] Recherche dans les logs pour: '{query}'")
    try:
        # Le retriever va maintenant utiliser les métadonnées enrichies pour construire une requête très précise.
        docs = retriever.invoke(query)
        if not docs:
            return "Aucune information pertinente n'a été trouvée dans les logs pour cette requête spécifique."
        
        # On retourne jusqu'à 5 logs pertinents pour donner un contexte riche au LLM principal
        return "\n\n---\n\n".join(
            [f"Source Log (type: {doc.metadata.get('log_type', 'N/A')}):\n{doc.page_content}" for doc in docs[:5]]
        )
    except Exception as e:
        print(f"ERREUR dans le retriever RAG: {e}")
        return "Une erreur est survenue lors de la recherche dans les logs. Le format de la question est peut-être trop complexe ou la base de données est inaccessible."