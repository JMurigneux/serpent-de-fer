import discord
from discord.ext import commands
from typing import Optional
import json
import aiohttp
from datetime import datetime

from CTS_API import prochains_departs

from dotenv import load_dotenv
import os

load_dotenv()
DISCORD_TOKEN=os.getenv("DISCORD_TOKEN")
CONFIG_FILE = "bot_config.json"

IMAGE_LIGNE="https://drive.google.com/uc?id="+"1cb5x3OAewXwKsYAqZPDIdVzMRncfxQsJ"#https://drive.google.com/file/d/1cb5x3OAewXwKsYAqZPDIdVzMRncfxQsJ/view?usp=sharing


# emojis
async def fetch_application_emojis(application_id):
    # L'URL de l'API pour les emojis d'application
    url = f"https://discord.com/api/v10/applications/{application_id}/emojis"
    
    # Les headers nécessaires, incluant le token du bot
    headers = {
        "Authorization": f"Bot {bot.http.token}",
        "Content-Type": "application/json"
    }
    
    try:
        async with bot.http_session.get(url, headers=headers) as response:
            if response.status == 200:
                emojis_data = await response.json()
                
                # structurer les informations utiles
                emojis_dict=dict()
                for emo in emojis_data["items"]:
                    emojis_dict[emo["name"]]=emo["id"]

                # Stocker les données pour utilisation ultérieure
                bot.application_emojis = emojis_dict
                print(f"Emojis récupérés!")
                return emojis_dict
            else:
                error_text = await response.text()
                print(f"Erreur API récupération emojis: {response.status}, {error_text}")
                return None
    except Exception as e:
        print(f"Erreur lors de la requête: {e}")
        return None


class SerpentDeFerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.none()  # Aucun intent
        intents.guilds = True  # Nécessaire pour les slash commands
        # intents = discord.Intents.default()
        # intents.message_content = True
        # intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.answer_channels = {}
        self.load_config()
    
    # async def setup_hook(self):
    #     # Synchronise les commandes avec Discord
    #     await self.tree.sync()
    #     print("Commandes synchronisées!")

    async def setup_hook(self):
        # Sync pour un serveur spécifique (instantané)
        guild = discord.Object(id=1288175813614899276)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Commandes synchronisées sur le serveur de test!")

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                self.answer_channels = json.load(f)
        except FileNotFoundError:
            self.answer_channels = {}
    
    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.answer_channels, f, indent = 4)

bot = SerpentDeFerBot()

@bot.event
async def on_ready() -> None:
    print(f'{bot.user} is now running!')

    ### récupération des emoji
    # Initialiser une session HTTP si elle n'existe pas déjà
    if not hasattr(bot, 'http_session'):
        bot.http_session = aiohttp.ClientSession()
    # Récupérer les informations de l'application
    application = await bot.application_info()    
    # Récupérer les emojis d'application via l'API HTTP
    await fetch_application_emojis(application.id)

@bot.tree.command(name="reponse_setup", description="Setup l'arrêt, lignes, etc. de ce canal")
async def reponse_setup(interaction: discord.Interaction, channel: discord.TextChannel,
                            monitoring_ref: int,
                            line_ref_list: Optional[str] = None,
                            direction_ref_list: Optional[str] = None,
                            vehicle_mode: Optional[str] = None,
                            preview_interval: Optional[str] = None,
                            maximum_stop_visits: Optional[int] = None,
                            minimum_stop_visits_per_line: Optional[int] = None,
                            include_general_message: Optional[bool] = None,
                            start_time: Optional[str] = None
                        ):
    # Appliquer les valeurs par défaut
    LineRefList = line_ref_list.split(",") if line_ref_list else []
    LineRefList = [line.strip() for line in LineRefList]
    DirectionRefList = direction_ref_list.split(",") if direction_ref_list else []
    DirectionRefList = [line.strip() for line in DirectionRefList]
    VehicleMode = vehicle_mode or "undefined"
    PreviewInterval = preview_interval or "PT30M"
    MaximumStopVisits = maximum_stop_visits if maximum_stop_visits is not None else 3
    MinimumStopVisitsPerLine = minimum_stop_visits_per_line if minimum_stop_visits_per_line is not None else 3
    IncludeGeneralMessage = include_general_message if include_general_message is not None else True
    StartTime = start_time or "now"


    guild_id=str(interaction.guild.id)
    channel_id=str(channel.id)
    MonitoringRef=str(monitoring_ref)
    if not guild_id in bot.answer_channels.keys(): #si le serveur n'est pas connu
        bot.answer_channels[guild_id] = {}
    if not channel_id in bot.answer_channels[guild_id].keys(): #si le channel n'est pas connu
        bot.answer_channels[guild_id][channel_id] = {}

    bot.answer_channels[guild_id][channel_id][MonitoringRef] =  {
                                "LineRefList" : LineRefList,
                                "DirectionRefList" : DirectionRefList,
                                "VehicleMode" : VehicleMode,
                                "PreviewInterval" : PreviewInterval,
                                "MaximumStopVisits" : MaximumStopVisits,
                                "MinimumStopVisitsPerLine" : MinimumStopVisitsPerLine,
                                "IncludeGeneralMessage" : IncludeGeneralMessage,
                                "StartTime" : StartTime 
                            }
    
    bot.save_config()
    await interaction.response.send_message(
        f"Réponses du canal {channel.mention} modifiées.",
        # ephemeral=True
    )

@bot.tree.command(name="depart", description="Initie un départ, renvoie les prochains départs des lignes prévues aux arrêts prévus.")
async def depart(interaction: discord.Interaction):
    await interaction.response.defer()  #pour si l'opération est trop longue
    guild_id=str(interaction.guild.id)
    channel_id=str(interaction.channel.id)

    departs_list=[]
    for MonitoringRef,param in bot.answer_channels[guild_id][channel_id].items():
        temp=prochains_departs(MonitoringRef
                          ,LineRefList=param["LineRefList"]
                          ,DirectionRefList=param["DirectionRefList"]
                          ,VehicleMode=param["VehicleMode"]
                          ,PreviewInterval=param["PreviewInterval"]
                          ,MaximumStopVisits=param["MaximumStopVisits"]
                          ,MinimumStopVisitsPerLine=param["MinimumStopVisitsPerLine"]
                          ,IncludeGeneralMessage=param["IncludeGeneralMessage"]
                          ,StartTime=param["StartTime"]
                          )
        departs_list+=temp

    #trier la liste selon les heures de départ
    departs_list.sort(key=lambda x: datetime.fromisoformat(x["hdepart"]))

    embed = discord.Embed(
                title=f"Prochains départs",
                color=0x9a3b27
            )
    embed.set_thumbnail(url=IMAGE_LIGNE)  # URL d'une image pour l'illustration
    content=""
    for depart in departs_list:
        line_padded=f"{depart['ligne']:{'_'}<2}"
        emoji=f"<:{line_padded}:{bot.application_emojis[line_padded]}>"
        dt = datetime.fromisoformat(depart["hdepart"])
        content+=f"- {emoji} {depart["StopPointName"]} : **{dt.strftime("%H:%M")}**\n"

    embed.add_field(name="",value=content[:1020], inline=False)
    await interaction.followup.send(
        embed=embed,
    )

bot.run(DISCORD_TOKEN)