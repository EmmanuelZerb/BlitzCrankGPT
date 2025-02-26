from typing import Annotated, Dict, List, Optional
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import json
import os
import re


# Définition de la classe d'état avec mémoire
class State(TypedDict):
    messages: Annotated[list, add_messages]
    memory: Dict


# Fonction pour charger la mémoire depuis un fichier
def load_memory() -> Dict:
    memory_file = "blitzcrank_memory.json"
    if os.path.exists(memory_file):
        try:
            with open(memory_file, "r") as f:
                return json.load(f)
        except:
            return {"user_info": {"name": "Emmanuel"}, "lol_preferences": {}}
    else:
        # Mémoire par défaut avec votre prénom
        return {"user_info": {"name": "Emmanuel"}, "lol_preferences": {}}


# Fonction pour sauvegarder la mémoire
def save_memory(memory: Dict):
    with open("blitzcrank_memory.json", "w") as f:
        json.dump(memory, f)


# Fonction pour initialiser le graphe avec mémoire
def create_memory_chatbot():
    graph_builder = StateGraph(State)

    # Initialiser l'agent avec votre clé API
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,  # Plus de créativité pour les recommandations de builds
        api_key="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"
    )

    # Fonction pour gérer la mémoire et les réponses du chatbot
    def memory_chatbot(state: State):
        memory = state.get("memory", {})
        user_name = memory.get("user_info", {}).get("name", "")

        # Créer un message système pour Blitzcrank GPT
        system_message = SystemMessage(
            content=f"""Tu es Blitzcrank GPT, un assistant spécialisé sur League of Legends. 
Ta mission est de fournir les meilleurs builds, conseils et stratégies pour League of Legends.
Tu parles à {user_name}. Utilise son prénom dans tes réponses quand c'est approprié.
Tu as un style amical, énergique et passionné comme le champion Blitzcrank.
Tu connais parfaitement la méta actuelle, les objets, les runes, et les stratégies optimales pour chaque champion.
Commence toujours tes messages par "BLITZCRANK GPT:" pour montrer ton identité unique.
Si on te pose une question qui n'est pas liée à League of Legends, réponds quand même mais ramène rapidement la conversation vers le jeu."""
        )

        # Ajouter le message système aux messages existants
        messages_with_memory = [system_message] + state["messages"]

        # Obtenir la réponse du modèle
        response = llm.invoke(messages_with_memory)

        # Mettre à jour et renvoyer l'état
        return {"messages": [response], "memory": memory}

    # Ajouter le nœud de chatbot au graphe
    graph_builder.add_node("memory_chatbot", memory_chatbot)
    graph_builder.set_entry_point("memory_chatbot")
    graph_builder.set_finish_point("memory_chatbot")

    # Compiler le graphe
    return graph_builder.compile()


# Fonction interactive pour le chat
def chat_loop():
    # Charger la mémoire existante
    memory = load_memory()

    # État initial avec la mémoire chargée
    state = {"messages": [], "memory": memory}

    # Créer le graphe
    graph = create_memory_chatbot()

    print(f"BLITZCRANK GPT démarré! (Tapez 'exit' pour quitter)")
    print(f"Mémoire chargée: Blitzcrank GPT connaît votre prénom, {memory['user_info']['name']}")
    print("Prêt à répondre à toutes vos questions sur League of Legends!")

    while True:
        # Obtenir l'entrée de l'utilisateur
        user_input = input("\nVous: ")

        # Vérifier si l'utilisateur veut quitter
        if user_input.lower() in ["exit", "quit", "q"]:
            print("Au revoir!")
            break

        # Ajouter le message de l'utilisateur à l'état
        state["messages"].append(HumanMessage(content=user_input))

        # Exécuter le graphe avec l'état mis à jour
        new_state = graph.invoke(state)

        # Mettre à jour l'état
        state = new_state

        # Afficher la réponse de Blitzcrank GPT
        ai_message = state["messages"][-1]
        # Assurer que la réponse commence par "BLITZCRANK GPT:" si ce n'est pas déjà le cas
        response_content = ai_message.content
        if not response_content.startswith("BLITZCRANK GPT:"):
            response_content = f"BLITZCRANK GPT: {response_content}"
        print(f"\n{response_content}")

        # Mettre à jour la mémoire avec les préférences League of Legends détectées
        response_content = ai_message.content
        user_input_lower = user_input.lower()
        memory = state["memory"]

        # Détecter si l'utilisateur mentionne un champion préféré
        champion_pattern = r"j'(?:aime|préfère|main|joue|utilise) (\w+)"
        champion_match = re.search(champion_pattern, user_input_lower)
        if champion_match:
            possible_champion = champion_match.group(1).capitalize()
            if "lol_preferences" not in memory:
                memory["lol_preferences"] = {}
            memory["lol_preferences"]["favorite_champion"] = possible_champion

        # Détecter si l'utilisateur mentionne un rôle préféré
        role_keywords = {
            "top": ["top", "toplaner", "toplane"],
            "jungle": ["jungle", "jungler", "jgl"],
            "mid": ["mid", "middle", "milieu"],
            "adc": ["adc", "bot", "botlane", "carry"],
            "support": ["support", "supp", "soutien"]
        }

        for role, keywords in role_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                if "lol_preferences" not in memory:
                    memory["lol_preferences"] = {}
                memory["lol_preferences"]["preferred_role"] = role
                break

        # Mettre à jour et sauvegarder la mémoire après chaque interaction
        state["memory"] = memory
        save_memory(state["memory"])


# Lancer la boucle de chat si exécuté directement
if __name__ == "__main__":
    chat_loop()