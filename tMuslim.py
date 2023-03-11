import nextcord
from nextcord.ext import commands
from PrayerManager import PrayerManager
from Mongo import ServerManager
import os
intents = nextcord.Intents.all()

client = commands.Bot(intents=intents)

import dotenv
dotenv.load_dotenv("token.env")

client.add_cog(PrayerManager(client, ServerManager(os.getenv("PYMONGO_CREDS"), "tMuslim")))

client.run(os.getenv("TMUSLIM_TOKEN"))

