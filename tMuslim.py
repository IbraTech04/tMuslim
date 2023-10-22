import json
import nextcord
from nextcord.ext import commands, application_checks
from PrayerManager import PrayerManager
from Settings import Settings
from Mongo import ServerManager
# from Ramadan import RamadanSpecial
import os
intents = nextcord.Intents.all()

client = commands.Bot(intents=intents)

import dotenv
dotenv.load_dotenv("token.env")
athan_loops = {}

database = ServerManager(os.getenv("PYMONGO_CREDS"), "tMuslim")
prayers = PrayerManager(client, database)

client.add_cog(prayers)
client.add_cog(Settings(client, database, athan_loops, prayers))


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    await client.change_presence(status=nextcord.Status.online, activity=nextcord.Game("Praying for a successful API call"))
    
    for guild in client.guilds:
        if not await database.is_server_registered(guild.id):
            continue
        athan_loops[guild.id] = client.loop.create_task(prayers.athan(guild.id))

# When the bot leaves a server
@client.event
async def on_guild_remove(self, guild: nextcord.Guild):
    await database.unregister_server(guild.id)
    # Remove them fro mteh athan_loops
    athan_loops[guild.id].cancel()
    del athan_loops[guild.id]
            
client.run(os.getenv("TMUSLIM_TOKEN"))
