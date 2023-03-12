import nextcord
from nextcord.ext import commands
from PrayerManager import PrayerManager
from Settings import Settings
from Mongo import ServerManager
import os
intents = nextcord.Intents.all()

client = commands.Bot(intents=intents)

import dotenv
dotenv.load_dotenv("token.env")

database = ServerManager(os.getenv("PYMONGO_CREDS"), "tMuslim")

client.add_cog(PrayerManager(client, database))
client.add_cog(Settings(client, database))

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    await client.change_presence(status=nextcord.Status.online, activity=nextcord.Game("Praying for a successful API call"))


client.run(os.getenv("TMUSLIM_TOKEN"))
