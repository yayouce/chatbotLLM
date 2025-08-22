# # main.py (Version Complète et Corrigée)

# import os
# import operator
# import re
# import json
# import uuid
# from typing import TypedDict, Annotated, List

# # --- 1. Importations ---
# import root_config
# from langchain_groq import ChatGroq
# from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import MemorySaver
# from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

# from app_tools.database_tools import (
#     get_transaction_details, find_transactions_by_criteria, get_transaction_summary,
#     get_wallet_notification_stats, get_pending_transactions_count,
#     get_top_active_phone_numbers, find_transaction_by_any_reference
# )
# from app_tools.rag_tools import search_application_logs
# from prompts import SYSTEM_PROMPT_TEXT

# # --- 2. Configuration (la vôtre, conservée) ---
# if root_config.LANGCHAIN_TRACING_V2 == "true":
#     pass

# if root_config.TAVILY_API_KEY:
#     pass

# # --- Définition de l'État
# class AgentState(TypedDict):
#     messages: Annotated[List[HumanMessage | AIMessage | ToolMessage | SystemMessage], operator.add]

# # --- 4. Classe de l'Agent (Modifiée pour être plus robuste) ---
# class GatewaySupportAgent:
#     def __init__(self, model, tools, system_prompt=""):
#         self.system_prompt_content = system_prompt
#         self.tools_map = {t.name: t for t in tools}
#         self.model = model.bind_tools(tools)
        
#         # Construction du graphe
#         graph_builder = StateGraph(AgentState)
#         graph_builder.add_node("agent", self.call_agent)
#         graph_builder.add_node("tools", self.take_action)
#         graph_builder.add_conditional_edges(
#             "agent", self.should_continue, {"continue": "tools", "end": END}
#         )
#         graph_builder.add_edge("tools", "agent")
#         graph_builder.set_entry_point("agent")
        
#         self.memory = MemorySaver()
#         self.graph = graph_builder.compile(checkpointer=self.memory)

#     def _get_messages_with_system_prompt(self, current_messages):
#         if self.system_prompt_content:
#             if not current_messages or not isinstance(current_messages[0], SystemMessage):
#                 return [SystemMessage(content=self.system_prompt_content)] + current_messages
#         return current_messages

#     def _parse_and_correct_llm_output(self, ai_message: AIMessage) -> AIMessage:
#         """
#         Vérifie et corrige la sortie du LLM si elle est mal formatée.
#         Ceci est crucial pour les modèles qui ne respectent pas toujours le format tool_calls.
#         """
#         # Si le format est déjà correct, on ne touche à rien.
#         if isinstance(ai_message.tool_calls, list) and len(ai_message.tool_calls) > 0:
#             return ai_message

#         # Si le format est du texte brut qui ressemble à un appel de fonction
#         content = ai_message.content
#         if isinstance(content, str) and content.strip().startswith("<function="):
#             print("DEBUG: Sortie LLM mal formatée détectée. Tentative de correction...")
            
#             # Regex pour extraire le nom de la fonction et les arguments
#             match = re.search(r"<function=([\w_]+)>(.*?)</function>", content, re.DOTALL)
#             if match:
#                 tool_name = match.group(1).strip()
#                 args_str = match.group(2).strip()
#                 try:
#                     args_dict = json.loads(args_str)
#                     print(f"DEBUG: Correction réussie. Outil: {tool_name}, Args: {args_dict}")
#                     # On reconstruit un AIMessage avec un tool_calls VALIDE
#                     ai_message.tool_calls = [{
#                         "name": tool_name,
#                         "args": args_dict,
#                         "id": f"manual-call-{uuid.uuid4()}"
#                     }]
#                     ai_message.content = "" 
#                     return ai_message
#                 except json.JSONDecodeError:
#                     print(f"WARN: Impossible de parser les arguments JSON de la fonction corrigée: {args_str}")
        
        
#         return ai_message

#     def call_agent(self, state: AgentState):
#         """Appelle le LLM pour qu'il prenne une décision, puis nettoie sa sortie."""
#         messages_for_llm = self._get_messages_with_system_prompt(state['messages'])
#         print(f"DEBUG: LLM Input -> {[m.type for m in messages_for_llm]}")
        
#         raw_ai_response = self.model.invoke(messages_for_llm)
        
#         # On passe la réponse brute au nettoyeur avant de continuer
#         cleaned_ai_response = self._parse_and_correct_llm_output(raw_ai_response)
        
#         print(f"DEBUG: LLM Output (nettoyé) -> Content: '{cleaned_ai_response.content[:100]}', Tool Calls: {cleaned_ai_response.tool_calls}")
#         return {'messages': [cleaned_ai_response]}

#     def should_continue(self, state: AgentState):
#         """Décide s'il faut continuer avec un outil ou terminer."""
#         last_message = state['messages'][-1]
        
#         # Grâce au nettoyage, cette condition est maintenant fiable.
#         if not last_message.tool_calls:
#             return "end" # Le LLM a produit une réponse textuelle, on termine.
#         else:
#             return "continue" # Le LLM a demandé un outil, on continue.

#     def take_action(self, state: AgentState):
#         """Exécute les appels d'outils."""
#         # Votre fonction take_action est déjà très bien, on la conserve.
#         tool_calls = state['messages'][-1].tool_calls
#         tool_results_messages = []
#         if not tool_calls:
#             return {'messages': []}

#         for tc in tool_calls:
#             tool_name = tc.get('name')
#             print(f"DEBUG: Appel de l'outil '{tool_name}' avec les arguments {tc.get('args')}")
#             tool_to_call = self.tools_map[tool_name]
#             try:
#                 result = tool_to_call.invoke(tc.get('args', {}))
#                 result_content = str(result)
#             except Exception as e:
#                 result_content = f"Error executing tool {tool_name}: {str(e)}"
            
#             tool_results_messages.append(ToolMessage(tool_call_id=tc['id'], name=tool_name, content=result_content))
#         return {'messages': tool_results_messages}


# llm = ChatGroq(
#     groq_api_key=root_config.GROQ_API_KEY,
#     model_name=root_config.MODEL_NAME_GROQ,
#     temperature=0.0
# )

# database_tools = [
#    get_transaction_details, find_transactions_by_criteria, get_transaction_summary,
#    get_wallet_notification_stats, get_pending_transactions_count,
#    get_top_active_phone_numbers, find_transaction_by_any_reference
# ]
# rag_tool_list = [search_application_logs]
# all_tools = database_tools + rag_tool_list

# agent_executor = GatewaySupportAgent(llm, all_tools, system_prompt=SYSTEM_PROMPT_TEXT).graph

# # --- 6. Boucle Principale (la vôtre, conservée) ---
# if __name__ == "__main__":
#     print("NGBOT Assist démarré. Tapez 'exit' ou 'quitter' pour quitter.")
#     print("Bonjour ! Je suis NGBOT Assist. Comment puis-je vous aider ?")
    
#     conversation_id = "user_conversation_main_thread_1"
#     conversation_config = {"configurable": {"thread_id": conversation_id}}

#     try:
#         while True:
#             user_input = input("👤 Vous: ")

#             if user_input.lower() in ["exit", "quitter"]:
#                 print("🤖 Assistant: Au revoir!")
#                 break
            
#             if not user_input.strip():
#                 continue

#             print("🤖 Assistant réfléchit...")

#             current_state_input = {"messages": [HumanMessage(content=user_input)]}
#             final_ai_message_content = None

#             # Votre boucle de streaming est conservée car elle gère l'affichage
#             for event_value_map in agent_executor.stream(current_state_input, config=conversation_config, stream_mode="values"):
#                 messages = event_value_map.get('messages', [])
#                 if messages:
#                     last_message = messages[-1]
#                     if isinstance(last_message, AIMessage):
#                         if not last_message.tool_calls and last_message.content:
#                             final_ai_message_content = last_message.content

#             if final_ai_message_content:
#                 print(f"🤖 Assistant: {final_ai_message_content}")
#             else:
#                 # Logique de fallback si le stream ne capture pas la réponse finale
#                 print("🤖 Assistant: Je n'ai pas pu formuler de réponse directe, veuillez vérifier les logs de l'agent.")

#     except KeyboardInterrupt:
#         print("\n🛑 Session interrompue par l'utilisateur.")
#     except Exception as e:
#         print(f"💥 ERREUR INATTENDUE: {e}")
#         import traceback
#         traceback.print_exc()
#     finally:
#         print("🏁 Arrêt de NGBOT Assist.")

























# main.py (Version Corrigée avec Initialisation Explicite)

import os
import operator
import re
import json
import uuid
from typing import TypedDict, Annotated, List

# --- 1. Importations ---
import root_config
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from app_tools.database_tools import (
    get_transaction_details, find_transactions_by_criteria, get_transaction_summary,
    get_wallet_notification_stats, get_pending_transactions_count,
    get_top_active_phone_numbers, find_transaction_by_any_reference
)
# On importe la FONCTION D'INITIALISATION et l'outil
from app_tools.rag_tools import search_application_logs, initialize_rag_components
from prompts import SYSTEM_PROMPT_TEXT
if root_config.LANGCHAIN_TRACING_V2 == "true":
     pass


# ... (votre code de configuration, AgentState, et la classe GatewaySupportAgent restent identiques) ...
class AgentState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage | ToolMessage | SystemMessage], operator.add]

class GatewaySupportAgent:
    def __init__(self, model, tools, system_prompt=""):
        self.system_prompt_content = system_prompt
        self.tools_map = {t.name: t for t in tools}
        self.model = model.bind_tools(tools)
        
        # Construction du graphe
        graph_builder = StateGraph(AgentState)
        graph_builder.add_node("agent", self.call_agent)
        graph_builder.add_node("tools", self.take_action)
        graph_builder.add_conditional_edges(
            "agent", self.should_continue, {"continue": "tools", "end": END}
        )
        graph_builder.add_edge("tools", "agent")
        graph_builder.set_entry_point("agent")
        
        self.memory = MemorySaver()
        self.graph = graph_builder.compile(checkpointer=self.memory)

    def _get_messages_with_system_prompt(self, current_messages):
        if self.system_prompt_content:
            if not current_messages or not isinstance(current_messages[0], SystemMessage):
                return [SystemMessage(content=self.system_prompt_content)] + current_messages
        return current_messages

    def _parse_and_correct_llm_output(self, ai_message: AIMessage) -> AIMessage:
        """
        Vérifie et corrige la sortie du LLM si elle est mal formatée.
        Ceci est crucial pour les modèles qui ne respectent pas toujours le format tool_calls.
        """
        # Si le format est déjà correct, on ne touche à rien.
        if isinstance(ai_message.tool_calls, list) and len(ai_message.tool_calls) > 0:
            return ai_message

        # Si le format est du texte brut qui ressemble à un appel de fonction
        content = ai_message.content
        if isinstance(content, str) and content.strip().startswith("<function="):
            print("DEBUG: Sortie LLM mal formatée détectée. Tentative de correction...")
            
            # Regex pour extraire le nom de la fonction et les arguments
            match = re.search(r"<function=([\w_]+)>(.*?)</function>", content, re.DOTALL)
            if match:
                tool_name = match.group(1).strip()
                args_str = match.group(2).strip()
                try:
                    args_dict = json.loads(args_str)
                    print(f"DEBUG: Correction réussie. Outil: {tool_name}, Args: {args_dict}")
                    # On reconstruit un AIMessage avec un tool_calls VALIDE
                    ai_message.tool_calls = [{
                        "name": tool_name,
                        "args": args_dict,
                        "id": f"manual-call-{uuid.uuid4()}"
                    }]
                    ai_message.content = "" 
                    return ai_message
                except json.JSONDecodeError:
                    print(f"WARN: Impossible de parser les arguments JSON de la fonction corrigée: {args_str}")
        
        
        return ai_message

    def call_agent(self, state: AgentState):
        """Appelle le LLM pour qu'il prenne une décision, puis nettoie sa sortie."""
        messages_for_llm = self._get_messages_with_system_prompt(state['messages'])
        print(f"DEBUG: LLM Input -> {[m.type for m in messages_for_llm]}")
        
        raw_ai_response = self.model.invoke(messages_for_llm)
        
        # On passe la réponse brute au nettoyeur avant de continuer
        cleaned_ai_response = self._parse_and_correct_llm_output(raw_ai_response)
        
        print(f"DEBUG: LLM Output (nettoyé) -> Content: '{cleaned_ai_response.content[:100]}', Tool Calls: {cleaned_ai_response.tool_calls}")
        return {'messages': [cleaned_ai_response]}

    def should_continue(self, state: AgentState):
        """Décide s'il faut continuer avec un outil ou terminer."""
        last_message = state['messages'][-1]
        
        # Grâce au nettoyage, cette condition est maintenant fiable.
        if not last_message.tool_calls:
            return "end" # Le LLM a produit une réponse textuelle, on termine.
        else:
            return "continue" # Le LLM a demandé un outil, on continue.

    def take_action(self, state: AgentState):
        """Exécute les appels d'outils."""
        tool_calls = state['messages'][-1].tool_calls
        tool_results_messages = []
        if not tool_calls:
            return {'messages': []}

        for tc in tool_calls:
            tool_name = tc.get('name')
            print(f"DEBUG: Appel de l'outil '{tool_name}' avec les arguments {tc.get('args')}")
            tool_to_call = self.tools_map[tool_name]
            try:
                result = tool_to_call.invoke(tc.get('args', {}))
                result_content = str(result)
            except Exception as e:
                result_content = f"Error executing tool {tool_name}: {str(e)}"
            
            tool_results_messages.append(ToolMessage(tool_call_id=tc['id'], name=tool_name, content=result_content))
        return {'messages': tool_results_messages}

try:
    print("--- DÉMARRAGE DE L'INITIALISATION DE L'APPLICATION ---")

    #  initialiser le retriever RAG.
    print("Étape 1: Initialisation des composants RAG...")
    initialize_rag_components()
    print("   -> Succès.")

    print("Étape 2: Initialisation du LLM principal...")
    llm = ChatGroq(
        groq_api_key=root_config.GROQ_API_KEY,
        model_name=root_config.MODEL_NAME_GROQ,
        temperature=0.0
    )
    print("   -> Succès.")

    print("Étape 3: Assemblage de la boîte à outils...")
    database_tools = [
       get_transaction_details, find_transactions_by_criteria, get_transaction_summary,
       get_wallet_notification_stats, get_pending_transactions_count,
       get_top_active_phone_numbers, find_transaction_by_any_reference
    ]
    rag_tool_list = [search_application_logs]
    all_tools = database_tools + rag_tool_list
    print("   -> Succès.")

    print("Étape 4: Création de l'instance de l'agent...")
    agent_executor = GatewaySupportAgent(llm, all_tools, system_prompt=SYSTEM_PROMPT_TEXT).graph
    print("   -> Succès.")
    
    print("\n✅✅✅ INITIALISATION COMPLÈTE RÉUSSIE ✅✅✅\n")

except Exception as e:
    print("\n" + "💥" * 20)
    print("💥💥💥 ERREUR FATALE LORS DE L'INITIALISATION DE L'AGENT 💥💥💥")
    print(f"L'erreur est: {e}")
    import traceback
    traceback.print_exc()
    print("💥" * 20 + "\n")
    agent_executor = None # On s'assure que l'agent n'est pas utilisable

# --- 6. Boucle Principale ---
if __name__ == "__main__":
    
    if agent_executor:
        print("NGBOT Assist démarré. Tapez 'exit' ou 'quitter' pour quitter.")
        # ... (le reste de votre boucle `while True` reste identique)
    else:
        print("L'agent n'a pas pu démarrer en raison d'une erreur d'initialisation. Veuillez vérifier les logs ci-dessus.")
    
    print("NGBOT Assist démarré. Tapez 'exit' ou 'quitter' pour quitter.")

    
    print("Bonjour ! Je suis NGBOT Assist. Comment puis-je vous aider ?")
    
    conversation_id = "user_conversation_main_thread_1"
    conversation_config = {"configurable": {"thread_id": conversation_id}}
    try:
        while True:
            user_input = input("👤 Vous: ")

            if user_input.lower() in ["exit", "quitter"]:
                print("🤖 Assistant: Au revoir!")
                break
            
            if not user_input.strip():
                continue

            print("🤖 Assistant réfléchit...")

            current_state_input = {"messages": [HumanMessage(content=user_input)]}
            final_ai_message_content = None

            # Votre boucle de streaming est conservée car elle gère l'affichage
            for event_value_map in agent_executor.stream(current_state_input, config=conversation_config, stream_mode="values"):
                messages = event_value_map.get('messages', [])
                if messages:
                    last_message = messages[-1]
                    if isinstance(last_message, AIMessage):
                        if not last_message.tool_calls and last_message.content:
                            final_ai_message_content = last_message.content

            if final_ai_message_content:
                print(f"🤖 Assistant: {final_ai_message_content}")
            else:
                # Logique de fallback si le stream ne capture pas la réponse finale
                print("🤖 Assistant: Je n'ai pas pu formuler de réponse directe, veuillez vérifier les logs de l'agent.")

    except KeyboardInterrupt:
        print("\n🛑 Session interrompue par l'utilisateur.")
    except Exception as e:
        print(f"💥 ERREUR INATTENDUE: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🏁 Arrêt de NGBOT Assist.")