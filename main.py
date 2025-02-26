import discord
from discord.ext import commands
from typing import Dict
import json
import os
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Configuration du bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Fonction pour charger la mémoire depuis un fichier
def load_memory() -> Dict:
    memory_file = "blitzcrank_memory.json"
    if os.path.exists(memory_file):
        try:
            with open(memory_file, "r") as f:
                return json.load(f)
        except:
            return {"user_info": {}, "lol_preferences": {}}
    else:
        # Mémoire par défaut
        return {"user_info": {}, "lol_preferences": {}}

# Fonction pour sauvegarder la mémoire
def save_memory(memory: Dict):
    with open("blitzcrank_memory.json", "w") as f:
        json.dump(memory, f)

# Initialiser le LLM avec votre clé API
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    api_key="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"
)

# Dictionnaire pour stocker les historiques de conversation par utilisateur
user_conversations = {}

# Événement déclenchée quand le bot est prêt
@bot.event
async def on_ready():
    print(f'{bot.user.name} est en ligne!')

# Événement pour écouter les messages
@bot.event
async def on_message(message):
    # Ignorer les messages du bot lui-même
    if message.author == bot.user:
        return

    # Traiter les commandes d'abord
    await bot.process_commands(message)

    # Vérifier si le message est une commande (commence par !)
    if message.content.startswith('!'):
        return

    # Répondre uniquement aux messages dans les canaux (pas en DM)
    if isinstance(message.channel, discord.TextChannel):
        # Vérifier si le message mentionne le bot ou contient "blitzcrank"
        if bot.user.mentioned_in(message) or "blitzcrank" in message.content.lower():
            # Indiquer que le bot est en train d'écrire
            async with message.channel.typing():
                # Charger la mémoire
                memory = load_memory()

                # Obtenir ou créer l'historique de conversation pour cet utilisateur
                user_id = str(message.author.id)
                if user_id not in user_conversations:
                    user_conversations[user_id] = []

                # Enregistrer le prénom de l'utilisateur dans la mémoire s'il n'est pas déjà présent
                if user_id not in memory["user_info"]:
                    memory["user_info"][user_id] = {"name": message.author.display_name}

                # Créer le message système pour Blitzcrank GPT
                user_name = memory["user_info"][user_id]["name"]
                system_message = SystemMessage(
                    content=f"""Tu es Blitzcrank GPT, un assistant spécialisé sur League of Legends. 
Ta mission est de fournir les meilleurs builds, conseils et stratégies pour League of Legends.
Tu parles à {user_name}. Utilise son prénom dans tes réponses quand c'est approprié.
Tu as un style amical, énergique et passionné comme le champion Blitzcrank.
Tu connais parfaitement la méta actuelle, les objets, les runes, et les stratégies optimales pour chaque champion.
Commence toujours tes messages par "BLITZCRANK GPT:" pour montrer ton identité unique.
Si on te pose une question qui n'est pas liée à League of Legends, réponds quand même mais ramène rapidement la conversation vers le jeu.
Tes réponses doivent être concises pour être adaptées au format Discord (environ 200-300 mots maximum)."""
                )

                # Ajouter le message de l'utilisateur à son historique
                user_message = HumanMessage(content=message.content)
                user_conversations[user_id].append(user_message)

                # Limiter l'historique à 10 messages pour éviter de dépasser les limites de tokens
                if len(user_conversations[user_id]) > 10:
                    user_conversations[user_id] = user_conversations[user_id][-10:]

                # Préparer les messages pour l'appel API
                messages = [system_message] + user_conversations[user_id]

                # Obtenir la réponse du modèle
                response = llm.invoke(messages)

                # Ajouter la réponse à l'historique
                user_conversations[user_id].append(response)

                # Mettre en forme la réponse
                response_content = response.content
                if not response_content.startswith("BLITZCRANK GPT:"):
                    response_content = f"BLITZCRANK GPT: {response_content}"

                # Détecter si l'utilisateur mentionne un champion préféré
                user_input_lower = message.content.lower()
                champion_pattern = r"j'(?:aime|préfère|main|joue|utilise) (\w+)"
                champion_match = re.search(champion_pattern, user_input_lower)
                if champion_match:
                    possible_champion = champion_match.group(1).capitalize()
                    if "lol_preferences" not in memory:
                        memory["lol_preferences"] = {}
                    if user_id not in memory["lol_preferences"]:
                        memory["lol_preferences"][user_id] = {}
                    memory["lol_preferences"][user_id]["favorite_champion"] = possible_champion

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
                        if user_id not in memory["lol_preferences"]:
                            memory["lol_preferences"][user_id] = {}
                        memory["lol_preferences"][user_id]["preferred_role"] = role
                        break

                # Sauvegarder la mémoire mise à jour
                save_memory(memory)

                # Envoyer la réponse
                await message.reply(response_content)

# Commande pour obtenir de l'aide sur le bot
@bot.command(name="aide")
async def aide(ctx):
    embed = discord.Embed(
        title="Aide Blitzcrank GPT",
        description="Je suis Blitzcrank GPT, votre assistant League of Legends!",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Comment m'utiliser",
        value="- Mentionnez-moi ou utilisez le mot 'blitzcrank' dans votre message\n"
              "- Posez-moi des questions sur les champions, builds, stratégies, etc.",
        inline=False
    )
    embed.add_field(
        name="Commandes disponibles",
        value="- `!aide` : Affiche ce message d'aide\n"
              "- `!profile` : Affiche vos préférences LoL enregistrées\n"
              "- `!meta` : Affiche les champions meta actuels\n"
              "- `!build [champion]` : Affiche le build recommandé pour un champion",
        inline=False
    )
    embed.set_footer(text="Développé avec passion pour League of Legends")
    await ctx.send(embed=embed)

# Commande pour afficher le profil d'un utilisateur
@bot.command(name="profile")
async def profile(ctx):
    # Charger la mémoire
    memory = load_memory()
    user_id = str(ctx.author.id)

    embed = discord.Embed(
        title=f"Profil LoL de {ctx.author.display_name}",
        color=discord.Color.gold()
    )

    # Vérifier si l'utilisateur a des préférences enregistrées
    if user_id in memory.get("lol_preferences", {}) and memory["lol_preferences"].get(user_id):
        user_prefs = memory["lol_preferences"][user_id]

        if "favorite_champion" in user_prefs:
            embed.add_field(
                name="Champion favori",
                value=user_prefs["favorite_champion"],
                inline=True
            )

        if "preferred_role" in user_prefs:
            roles = {
                "top": "Top Lane 🛡️",
                "jungle": "Jungle 🌲",
                "mid": "Mid Lane ⚔️",
                "adc": "ADC 🏹",
                "support": "Support 💫"
            }
            embed.add_field(
                name="Rôle préféré",
                value=roles.get(user_prefs["preferred_role"], user_prefs["preferred_role"]),
                inline=True
            )

        embed.set_footer(text="Dites-moi vos préférences LoL pour mettre à jour votre profil")
    else:
        embed.description = "Aucune préférence enregistrée. Mentionnez vos champions et rôles préférés dans vos conversations avec moi!"

    await ctx.send(embed=embed)

# Commande pour afficher les champions meta actuels
@bot.command(name="meta")
async def meta(ctx):
    # Ce serait idéal de récupérer ces données dynamiquement, mais pour l'exemple nous utilisons des données statiques
    async with ctx.typing():
        # Créer un message système pour demander les champions meta
        system_message = SystemMessage(
            content="""Tu es Blitzcrank GPT, un assistant spécialisé sur League of Legends. 
Donne une liste très concise des 3 champions meta actuels pour chaque rôle.
Format ta réponse sous forme de liste par rôle. Sois bref et précis."""
        )

        # Obtenir la réponse du modèle
        human_message = HumanMessage(content="Quels sont les champions meta actuels pour chaque rôle?")
        response = llm.invoke([system_message, human_message])

        # Créer l'embed avec la réponse
        embed = discord.Embed(
            title="Champions Meta Actuels",
            description=response.content.replace("BLITZCRANK GPT:", "").strip(),
            color=discord.Color.purple()
        )
        embed.set_footer(text="Meta basée sur les dernières mises à jour et statistiques")
        await ctx.send(embed=embed)

# Commande pour obtenir le build d'un champion
@bot.command(name="build")
async def build(ctx, champion=None):
    if champion is None:
        await ctx.send("BLITZCRANK GPT: Veuillez spécifier un champion! Exemple: `!build Blitzcrank`")
        return

    async with ctx.typing():
        # Créer un message système pour demander le build
        system_message = SystemMessage(
            content=f"""Tu es Blitzcrank GPT, un assistant spécialisé sur League of Legends. 
Donne un build optimal pour {champion} incluant:
1. Runes
2. Items de départ
3. Build path principal
4. Boots
5. Items situationnels
Sois concis et précis. Format ta réponse pour Discord."""
        )

        # Obtenir la réponse du modèle
        human_message = HumanMessage(content=f"Quel est le meilleur build pour {champion}?")
        response = llm.invoke([system_message, human_message])

        # Créer l'embed avec la réponse
        embed = discord.Embed(
            title=f"Build Optimal pour {champion.capitalize()}",
            description=response.content.replace("BLITZCRANK GPT:", "").strip(),
            color=discord.Color.green()
        )
        embed.set_footer(text="Build recommandé par Blitzcrank GPT")
        await ctx.send(embed=embed)

# Lancer le bot avec le token (à définir dans les secrets de Replit)
if __name__ == "__main__":
    # Pour Replit, récupérer le token depuis les secrets
    from os import getenv
    from dotenv import load_dotenv

    # Charger les variables d'environnement
    load_dotenv()

    # Récupérer le token
    TOKEN = getenv('TOKEN_BOT_DISCORD')

    if not TOKEN:
        print("⚠️ ERREUR: Token Discord non trouvé!")
        print("Veuillez ajouter votre token Discord dans les secrets Replit avec la clé 'DISCORD_TOKEN'")
    else:
        try:
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            print("⚠️ ERREUR: Token Discord invalide!")