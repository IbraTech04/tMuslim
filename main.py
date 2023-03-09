from asyncio import tasks
import os
import nextcord
from nextcord.ext import commands
from pymongo import MongoClient
import requests
from datetime import datetime
from nextcord.ext import tasks
import dotenv
import pytz
from geopy.geocoders import Nominatim
from nextcord import Interaction, SlashOption, slash_command
from timezonefinder import TimezoneFinder
dotenv.load_dotenv("token.env")

intents = nextcord.Intents.all()
tMuslim = commands.Bot(command_prefix='tmm', intents=intents, activity=nextcord.Activity(type=nextcord.ActivityType.listening, name="Qur'aan"))  # initializing the bot

mongo = MongoClient(os.getenv("PYMONGO_CREDS"))
db = mongo.tMuslim

async def elapsed_time(start_hour, start_minute, end_hour, end_minute):
    """
    >>>elapsed_time(23, 59, 0, 0)
    (0, 1)
    :param start_hour:
    :param start_minute:
    :param end_hour:
    :param end_minute:
    :return:
    """
    hour_left = 0
    min_left = 60 - start_minute
    end_hour -= 1
    min_left += end_minute
    if min_left >= 60:
        hour_left += 1
        min_left = min_left - 60
    hour_left = hour_left + (end_hour - start_hour)
    if hour_left < 0:
        hour_left += 24
    return hour_left, min_left

async def getNextPrayer(prayerTimes, hour, minute):
    fajrTime = prayerTimes["data"]["timings"]["Fajr"]
    duhurTime = prayerTimes["data"]["timings"]["Dhuhr"]
    asrTime = prayerTimes["data"]["timings"]["Asr"]
    maghribTime = prayerTimes["data"]["timings"]["Maghrib"]
    ishaaTime = prayerTimes["data"]["timings"]["Isha"]
    if hour > int(ishaaTime[0:2]) or hour <= int(fajrTime[0:2]):
        if hour == int(fajrTime[0:2]):
            if minute <= int(fajrTime[3:5]):
                return "Fajr"
            else:
                return "Dhuhr"
        return "Fajr"
    elif int(fajrTime[0:2]) <= hour <= int(duhurTime[0:2]):
        if hour == int(duhurTime[0:2]):
            if minute <= int(duhurTime[3:5]):
                return "Dhuhr"
            else:
                return "Asr"
        return "Dhuhr"
    elif int(duhurTime[0:2]) <= hour <= int(asrTime[0:2]):
        if hour == int(asrTime[0:2]):
            if minute <= int(asrTime[3:5]):
                return "Asr"
            else:
                return "Maghrib"
        return "Asr"
    elif int(asrTime[0:2]) <= hour <= int(maghribTime[0:2]):
        if hour == int(maghribTime[0:2]):
            if minute <= int(maghribTime[3:5]):
                return "Maghrib"
            else:
                return "Isha"
        return "Maghrib"
    elif int(maghribTime[0:2]) <= hour <= int(ishaaTime[0:2]):
        if hour == int(ishaaTime[0:2]):
            if minute <= int(ishaaTime[3:5]):
                return "Isha"
            else:
                return "Fajr"
        return "Isha"

async def get_time(guild: nextcord.Guild) -> tuple[int, int]:
    zone = db.servers.find_one({"_id": guild.id})["timezone"]
    tz = pytz.timezone(zone)
    return datetime.now(tz).hour, datetime.now(tz).minute

async def get_prayer_list(guild: nextcord.Guild):
    city = db.servers.find_one({"_id": guild.id})["city"]  # get city
    country = db.servers.find_one({"_id": guild.id})["country"]  # get country
    prayerTimes = requests.get(f"http://api.aladhan.com/v1/timingsByCity?city={city}&country={country}").json()
    return prayerTimes

@tMuslim.slash_command(guild_ids=tMuslim.guilds, name="nextprayer", description="Get the next prayer time")
async def nextprayer(interaction: Interaction):
    if not db.servers.find_one({"_id": interaction.guild.id}):
        await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="You haven't set up your server yet! Please use /setup command to set up your server.", color=nextcord.Color.red()), ephemeral=True)
        return
    prayerTimes = await get_prayer_list(interaction.guild)
    hour, minute = await get_time(interaction.guild)  # get time
    nextPrayer = await getNextPrayer(prayerTimes, hour, minute)  # get next prayer
    nextPrayerTime = prayerTimes["data"]["timings"][nextPrayer]  # get next prayer time from API data
    timeUntil = await elapsed_time(int(nextPrayerTime[0:2]), int(nextPrayerTime[3:5]), hour, minute)  # calculate remaining time
    await interaction.response.send_message(embed=nextcord.Embed(title="Next Prayer", description=f"The next prayer is **{nextPrayer}** in **{timeUntil[0]} hours and {timeUntil[1]} minutes** ({nextPrayerTime})", color=nextcord.Color.green()))


@tMuslim.slash_command(guild_ids=tMuslim.guilds, description="Setup your server for use with the bot")
async def setup(interaction: nextcord.Interaction, city: str = SlashOption(required=True, description="Your city"), country: str = SlashOption(required=True, description="Your country"), reaction_role_channel: nextcord.TextChannel = SlashOption(required=True, description="Channel to send reaction roles to for prayer timings"), role: nextcord.Role = SlashOption(required=False, description="The role to ping for prayer times. If not provided, the bot will create a new role."), channel: nextcord.TextChannel = SlashOption(required=False, description="The channel to send prayer times to. If not provided, the bot will create a new channel.")):
    if db.servers.find_one({"_id": interaction.guild.id}):
        await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="You have already set up your server! To edit your preferences, use the /set command", color=nextcord.Color.red()), ephemeral=True)
        return
    try:
        geolocator = Nominatim(user_agent="geoapiExercises")
        location = geolocator.geocode(f"{city}, {country}")
        obj = TimezoneFinder()
        time_zone = obj.timezone_at(lng=location.longitude, lat=location.latitude)
        if not role:
            # If no role is provided, create a new one called "tMuslim Notifications"
            role = await interaction.guild.create_role(name="🕌tMuslim Notifications", mentionable=True, color=nextcord.Color.green())
        if not channel:
            # If no channel is provided, create a new one called "tMuslim Notifications"
            # Only people with "role" should be able to see the channel
            channel = await interaction.guild.create_text_channel(name="🕌tMuslim Notifications", topic="Channel for prayer pings", overwrites={interaction.guild.default_role: nextcord.PermissionOverwrite(read_messages=False, view_channel = False), role: nextcord.PermissionOverwrite(read_messages=True, view_channel = True, send_messages=False)})
        
        message = await reaction_role_channel.send(embed=nextcord.Embed(title="Prayer Times", description="React to this message to get pinged for prayer times", color=nextcord.Color.green()))
        db.servers.insert_one({"_id": interaction.guild.id, "city": city, "country": country, "timezone": time_zone, "role": role.id, "channel": channel.id, 'reaction_role_message': message.id})
        await message.add_reaction("🕌")
        await interaction.response.send_message(embed=nextcord.Embed(title="🕌 Setup Complete", description="Setup complete! tMuslim's feature are now active in this server", color=nextcord.Color.green()))
    except:
        await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="An error occurred. Please check your city/country spelling and try again. If this problem persists, contact `TechMaster04#5002`. In the meantime, try a more common city/country in your timezone", color=nextcord.Color.red()))

# reaction roles
@tMuslim.event
async def on_raw_reaction_add(payload: nextcord.RawReactionActionEvent):
    if payload.message_id == db.servers.find_one({"_id": payload.guild_id})["reaction_role_message"]:
        #check if it's the bot
        if payload.user_id == tMuslim.user.id:
            return
        if payload.emoji.name == "🕌":
            await payload.member.add_roles(nextcord.Object(id=db.servers.find_one({"_id": payload.guild_id})["role"]))
            await payload.member.send(embed=nextcord.Embed(title="Prayer Times", description="You have been pinged for prayer times. You can change this by removing the reaction from the message in the channel you set up your server in", color=nextcord.Color.green()))
# If the user removes the reaction, remove the role
@tMuslim.event
async def on_raw_reaction_remove(payload: nextcord.RawReactionActionEvent):
    if payload.message_id == db.servers.find_one({"_id": payload.guild_id})["reaction_role_message"]:
        if payload.emoji.name == "🕌":
            guild = tMuslim.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            await member.remove_roles(nextcord.Object(id=db.servers.find_one({"_id": payload.guild_id})["role"]))
            await member.send(embed=nextcord.Embed(title="Prayer Times", description="You have been removed from the prayer times role. You can change this by adding the reaction back to the message in the channel you set up your server in", color=nextcord.Color.green()))
    
@tMuslim.slash_command(guild_ids=tMuslim.guilds, name="prayerlist", description="View a list of all prayer times in your city")
async def prayerlist(interaction: nextcord.Interaction):
    if not db.servers.find_one({"_id": interaction.guild.id}):
        await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="You haven't set up your server yet! Please use /setup command to set up your server.", color=nextcord.Color.red()), ephemeral=True)
        return
    city = db.servers.find_one({"_id": interaction.guild.id})["city"]
    country = db.servers.find_one({"_id": interaction.guild.id})["country"]
    prayerTimes = await get_prayer_list(interaction.guild)
    hour, minute = await get_time(interaction.guild)  # get time
    embed = nextcord.Embed(title="Prayer Times", description=f"Prayer times for {city}, {country} on {datetime.now().month}/{datetime.now().day}", color=nextcord.Color.green())
    nextPrayer = await getNextPrayer(prayerTimes, hour, minute)  # get next prayer
    for prayer in prayerTimes["data"]["timings"]:
        if prayer == nextPrayer:
            embed.add_field(name=f"**{prayer}**", value=f"**{prayerTimes['data']['timings'][prayer]}**", inline=False)
            continue
        if (prayer == "Imsak"):
            break
        if (prayer == "Sunset"):
            continue
        embed.add_field(name=f"{prayer}", value=f"{prayerTimes['data']['timings'][prayer]}", inline=False)
        
    await interaction.response.send_message(embed=embed)

@tMuslim.command(pass_context=True)
async def delete(ctx):
    # remove server from db
    db.servers.delete_one({"_id": ctx.guild.id})

@tMuslim.command(pass_context=True)
async def ping(ctx):
    # get role
    role = ctx.guild.get_role(db.servers.find_one({"_id": ctx.guild.id})["role"])
    channel = ctx.guild.get_channel(db.servers.find_one({"_id": ctx.guild.id})["channel"])
    await channel.send(f"{role.mention} tMuslim Prayer Notification Test")

@tasks.loop(seconds=60)
async def athan():
    for guild in tMuslim.guilds:
        if not db.servers.find_one({"_id": guild.id}):
            continue
        prayerTimes = await get_prayer_list(guild)
        nextPrayer = await getNextPrayer(prayerTimes, hour, minute)  # get next prayer
        hour, minute = await get_time(guild)  # get time
        nextPrayerTime = prayerTimes["data"]["timings"][nextPrayer]  # get next prayer time from API data
        # check if current time is equal to nextPrayerTime
        if hour == int(nextPrayerTime[:2]) and minute == int(nextPrayerTime[3:5]):
            currentMax = 0
            currentVC = None
            for channel in guild.voice_channels:
                users = len(channel.voice_states.keys())
                if users > currentMax:
                    currentMax = users
                    currentVC = channel
                # check if bot is already in VC
            if currentVC and currentVC.permissions_for(guild.me).connect and currentVC.permissions_for(
                    guild.me).speak and not guild.voice_client:
                await currentVC.connect()
                audio = None
                # if next prayer is fajr, play Athan1
                if nextPrayer == "Fajr":
                    audio = nextcord.FFmpegOpusAudio("Athan1.wav")
                else:
                    audio = nextcord.FFmpegOpusAudio('Athan2.mp3')
                voice = guild.voice_client  # Getting the voice client
                # leave the vc after playing the audio
                player = voice.play(audio, after=lambda x=None: (tMuslim.loop.create_task(voice.disconnect())))
                # get role to ping
                role = guild.get_role(db.servers.find_one({"_id": guild.id})["role"])
                await guild.system_channel.send(f"{role.mention} {nextPrayer} has started!")
athan.start()

@tMuslim.event
async def on_ready():
    print(f"{tMuslim.user} is ready to go!")

tMuslim.run(os.getenv("TMUSLIM_TOKEN"))