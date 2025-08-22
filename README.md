## NGBOT Assist : Agent Conversationnel Hybride pour l'Analyse de Logs
Ce projet présente un assistant IA avancé conçu pour transformer l'analyse de logs applicatifs et le support technique. Au lieu de recherches manuelles fastidieuses, cet agent permet aux équipes d'exploitation de dialoguer en langage naturel pour diagnostiquer des incidents, retracer des transactions et comprendre le comportement de l'application en temps réel.
Ce projet a été réalisé dans le cadre de mon stage de fin de cycle de MASTER chez NGSER
[lien youtube vers la demo](https://youtu.be/RZADO153XmI )
Lien vers une courte vidéo de démonstration de l'interface et des capacités de l'agent.
## Le Problème : Du Chaos des Logs à l'Intelligence Actionnable
Les applications modernes génèrent des volumes massifs de logs hétérogènes. Pour les équipes de support, trouver l'information pertinente pour diagnostiquer un incident client est souvent comme chercher une aiguille dans une botte de foin avec des outils comme grep. Ce processus est lent, sujet à erreur et nécessite une expertise technique approfondie.
NGBOT Assist a été conçu pour résoudre ce problème en offrant une interface de dialogue unifiée et intelligente qui comprend l'intention de l'utilisateur et fournit des réponses synthétiques basées sur les données.
## Fonctionnalités Clés
**Dialogue en Langage Naturel** : Posez des questions complexes comme "Pourquoi la transaction X a-t-elle échoué ?" ou "Montre-moi les requêtes SQL lentes pour l'ID de commande Y".
Agent Hybride : L'agent peut raisonner et puiser des informations depuis deux sources de vérité distinctes :
**Les Logs Applicatifs (RAG)** : Pour comprendre le contexte, le déroulement des opérations et les erreurs d'exécution.
**La Base de Données Transactionnelle (SQL)** : Pour obtenir des données factuelles et structurées (statuts, montants, etc.).
Recherche Sémantique et Structurée : Grâce à un pipeline RAG avancé, l'agent peut filtrer les logs sur des métadonnées précises (timestamp, context_id, statut, IP, etc.) et comprendre le sens des requêtes.
Exposition via API : Le système est entièrement encapsulé dans une API REST performante, prête à être intégrée dans n'importe quel outil ou frontend.
Interface de Démonstration : Un POC frontend en React a été développé pour illustrer les capacités de l'agent.
🏛️ Architecture Technique
Ce projet met en œuvre une architecture RAG Agentique moderne, orchestrée par LangGraph.


<img width="948" height="454" alt="image" src="https://github.com/user-attachments/assets/51f84009-b236-4bf1-9a3b-2dabd4b33dc9" />



Pipeline d'Ingestion de Données (Offline) :
**Parsing** : Un parser Python sur mesure analyse et structure les logs bruts, en extrayant plus de 15 types de métadonnées (ID de contexte, type de log, statut, durées, etc.).
**Indexation** : Les logs sont indexés dans une base de données vectorielle ChromaDB. Chaque ligne de log est transformée en un "embedding" sémantique avec Sentence-Transformers.
Agent Conversationnel (Temps Réel) :
**Orchestration** : **LangGraph** est utilisé pour modéliser le flux de pensée de l'agent, lui permettant d'enchaîner plusieurs outils pour résoudre des problèmes complexes.
**Cerveau** : Le raisonnement est assuré par des LLMs performants via ChatGroq (llama3-70b-8192).
Boîte à Outils : L'agent dispose d'outils spécialisés pour :
**Interroger la DB SQL** (via des fonctions Python sécurisées appelé **TOOLS**).
Interroger la DB Vectorielle (RAG) via un SelfQueryingRetriever qui traduit le langage naturel en requêtes de filtrage précises.

Exposition : L'agent est servi via une API asynchrone construite avec FastAPI.
## Stack Technologique
**Backend & IA** : **Python, LangChain, LangGraph, FastAPI, ChromaDB, Sentence-Transformers**
**LLM** : ChatGroq (Llama 3)
**Base de Données** : PostgreSQL (pour l'application), ChromaDB (pour le RAG)
**Infrastructure & CI/CD** :  *Docker*, *Git*
