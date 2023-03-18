import json
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
    
    # iterate through all the guilds and leave the vc if the bot is in one
    for guild in client.guilds:
        if guild.voice_client:
            await guild.voice_client.disconnect()
    

@client.slash_command(name="sendpatchnotes", description="Send the latest patch notes")
@commands.is_owner()
async def send_patch_notes(interaction: nextcord.Interaction, patch_notes: nextcord.Attachment):
    # The file will be a JSON file representing an embed of the patch notes
    
    # Read the file
    await interaction.response.defer()
    await patch_notes.save(patch_notes.filename)
    js = json.load(open(patch_notes.filename))
    data = js["embed"]
    embed=  nextcord.embeds.Embed.from_dict(data)
    
    for guild in client.guilds:
        channel = client.get_channel(await database.get_announcement_channel(guild.id))
        await channel.send(embed=embed)
    
    await interaction.followup.send("Patch notes sent!")
            
client.run(os.getenv("TMUSLIM_TOKEN"))
