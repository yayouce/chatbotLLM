# # indexer.py (adapté au nouveau parser)
# import os
# import shutil
# import time
# from langchain_community.vectorstores import Chroma
# from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain_core.documents import Document
# from parser import parse_log_line

# # Configuration
# LOG_FILE_PATH = "sample2.log" 
# DB_DIRECTORY = "log_db_advanced"
# t0 = time.time()
# def run_indexing():
#     print("indexation.......................")
#     embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2") 
#     doc_objects = []
#     print(f"Parsing du fichier de log '{LOG_FILE_PATH}'...")
#     with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
#         for i, line in enumerate(f):
#             parsed_log = parse_log_line(line)
#             if parsed_log:
#                 # Le contenu de la recherche est le log brut nettoyé, c'est le plus riche.
#                 doc = Document(
#                     page_content=parsed_log['raw_log'],
#                     metadata={k: str(v) for k, v in parsed_log.items() if v is not None}
#                 )
#                 doc_objects.append(doc)
#             else:
#                  print(f"Ligne non parsée {i+1}: {line.strip()}") 

#     if not doc_objects:
#         print("Aucun log n'a pu être parsé.")
#         return

#     print(f"Indexation de {len(doc_objects)} logs dans ChromaDB...")
#     db = Chroma.from_documents(
#         documents=doc_objects,
#         embedding=embedding_function,
#         persist_directory=DB_DIRECTORY
#     )
#     print(" Indexation terminée.")
#     tf=time.time()
#     tempecoule=tf-t0
#     print(tempecoule)

# if __name__ == "__main__":
#     run_indexing()












# indexer.py (version optimisée pour l'indexation ligne par ligne de gros volumes)
import os
import shutil
import time
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings # Import corrigé pour la nouvelle version
from langchain_core.documents import Document



from root_config import LOG_FILE_PATH, VECTOR_DB_PATH


from parser import parse_log_line

# Configuration de l'indexation
BATCH_SIZE = 1000  # Traiter les logs par lots 
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def run_indexing(force_recreate: bool = True):
    """
    Exécute une indexation complète d'un fichier de log, ligne par ligne.
    Affiche un benchmark de performance à la fin.
    
    :param force_recreate: Si True, supprime la base de données existante avant de commencer.
    """
    if not os.path.exists(LOG_FILE_PATH):
        print(f"❌ ERREUR: Le fichier de log '{LOG_FILE_PATH}' n'a pas été trouvé.")
        return

    if force_recreate and os.path.exists(VECTOR_DB_PATH):
        print(f"Suppression de la base de données existante à '{VECTOR_DB_PATH}'...")
        shutil.rmtree(VECTOR_DB_PATH)

    # --- Initialisation des composants lourds ---
    print(f"Chargement du modèle d'embedding: {EMBEDDING_MODEL}...")
    embedding_function = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    vectorstore = Chroma(
        persist_directory=VECTOR_DB_PATH,
        embedding_function=embedding_function
    )
    
    print(f"Démarrage du parsing de '{LOG_FILE_PATH}' et de l'indexation par lots de {BATCH_SIZE}...")
    
    # --- Début de la mesure du temps ---
    start_time = time.time()
    
    doc_batch = []
    total_parsed = 0
    total_indexed = 0
    lines_not_parsed = 0

    with open(LOG_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            parsed_log = parse_log_line(line)
            if parsed_log:
                total_parsed += 1
                doc = Document(
                    page_content=parsed_log.get('raw_log', ''),
                    # On convertit tout en string pour ChromaDB et on s'assure que les valeurs ne sont pas None
                    metadata={k: str(v) for k, v in parsed_log.items() if v is not None}
                )
                doc_batch.append(doc)
            else:
                lines_not_parsed += 1
            
            # Quand le lot est plein, on l'indexe
            if len(doc_batch) >= BATCH_SIZE:
                vectorstore.add_documents(doc_batch)
                total_indexed += len(doc_batch)
                print(f"  -> Lot de {len(doc_batch)} indexé. Total: {total_indexed} logs.")
                doc_batch = []

    # Ne pas oublier d'indexer le dernier lot s'il n'est pas plein
    print(doc_batch)
    if doc_batch:
        vectorstore.add_documents(doc_batch)
        total_indexed += len(doc_batch)
        print(f"  -> Dernier lot de {len(doc_batch)} indexé. Total: {total_indexed} logs.")

    # --- Fin de la mesure du temps ---
    end_time = time.time()
    duration = end_time - start_time
    
    # On évite la division par zéro
    docs_per_second = total_indexed / duration if duration > 0 else 0

    # --- Affichage des résultats ---
    print("\n" + "="*50)
    print("✅ INDEXATION TERMINÉE ✅")
    print(f"   Lignes parsées avec succès: {total_parsed}")
    print(f"   Lignes non parsées (ignorées): {lines_not_parsed}")
    print(f"   Documents effectivement indexés: {total_indexed}")
    print(f"   Durée totale: {duration:.2f} secondes (~{duration/60:.2f} minutes)")
    print(f"   Vitesse d'indexation: {docs_per_second:.2f} documents/seconde")
    print(f"   Base de données sauvegardée dans: '{VECTOR_DB_PATH}'")
    print("="*50)

if __name__ == "__main__":
    run_indexing()