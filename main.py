import random
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

async def conv_to_arabic(number):
    arabicNumbers = {0: '۰', 1: '١', 2: '٢', 3: '۳', 4: '۴', 5: '۵', 6: '٦', 7: '۷', 8: '۸', 9: '۹'}
    return ''.join([arabicNumbers[int(digit)] for digit in str(number)])

async def calculateRemainingTime(prayerHour, prayerMin, hour, minute, fajr):
    if prayerHour == hour and prayerMin == minute:  # If the current time matches the prayer time, return 0, 0
        return 0, 0
    if fajr:  # If we're calculating Fajr do this
        prayerHour += 24 if prayerHour < hour else 0
        time_diff = (prayerHour - hour) * 60 + prayerMin - minute
    else:  # If we're not calculating Fajr, we can calculate normally 
        prayerHour += 24 if prayerHour <= hour and prayerMin <= minute else 0
        time_diff = (prayerHour - hour - (prayerMin < minute)) * 60 + (prayerMin - minute) % 60
    return divmod(time_diff, 60)

async def getNextPrayer(prayerTimes, hour, minute):
    prayer_order = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
    prayer_times = [prayerTimes["data"]["timings"][prayer] for prayer in prayer_order]

    current_time = hour * 60 + minute
    for i, prayer_time in enumerate(prayer_times):
        prayer_hour = int(prayer_time[0:2])
        prayer_minute = int(prayer_time[3:5])
        prayer_time_minutes = prayer_hour * 60 + prayer_minute
        if prayer_time_minutes > current_time:
            return prayer_order[i]
    # If we've reached the end of the list, the next prayer is Fajr the next day
    return "Fajr"


async def get_time(guild: nextcord.Guild) -> tuple[int, int]:
    tz = pytz.timezone(db.servers.find_one({"_id": guild.id})["timezone"])
    return datetime.now(tz).hour, datetime.now(tz).minute

async def get_prayer_list(guild: nextcord.Guild):
    city = db.servers.find_one({"_id": guild.id})["city"]
    country = db.servers.find_one({"_id": guild.id})["country"]
    tz = pytz.timezone(db.servers.find_one({"_id": guild.id})["timezone"])
    date_str = datetime.now(tz).strftime("%d/%m/%Y")
    
    prayer_times = db.prayerTimes.find_one({"_id": f"{city}:{country}"})
    if prayer_times and prayer_times.get("date") == date_str:
        return prayer_times["prayerTimes"]
    
    db.prayerTimes.delete_one({"_id": f"{city}:{country}"})
    response = requests.get(f"http://api.aladhan.com/v1/timingsByCity?city={city}&country={country}").json()
    db.prayerTimes.insert_one({"_id": f"{city}:{country}", "prayerTimes": response, "date": date_str})
    return response


@tMuslim.slash_command(guild_ids=tMuslim.guilds, name="nextprayer", description="Get the next prayer time")
async def nextprayer(interaction: Interaction):
    if not db.servers.find_one({"_id": interaction.guild.id}):
        await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="You haven't set up your server yet! Please use /setup command to set up your server.", color=nextcord.Color.red()), ephemeral=True)
        return
    prayerTimes = await get_prayer_list(interaction.guild)
    hour, minute = await get_time(interaction.guild)  # get time
    nextPrayer = await getNextPrayer(prayerTimes, hour, minute)  # get next prayer
    nextPrayerTime = prayerTimes["data"]["timings"][nextPrayer]  # get next prayer time from API data
    timeUntil = await calculateRemainingTime(int(nextPrayerTime[0:2]), int(nextPrayerTime[3:5]), hour, minute, nextPrayer == "Fajr")  # calculate remaining time
    await interaction.response.send_message(embed=nextcord.Embed(title="Next Prayer", description=f"The next prayer is **{nextPrayer}** in **{timeUntil[0]} hours and {timeUntil[1]} minutes** ({nextPrayerTime})", color=nextcord.Color.green()))


@tMuslim.slash_command(guild_ids=tMuslim.guilds, description="Setup your server for use with the bot")
async def setup(interaction: nextcord.Interaction, city: str = SlashOption(required=True, description="Your city"),
                country: str = SlashOption(required=True, description="Your country"),
                role: nextcord.Role = SlashOption(required=False, description="The role to ping for prayer times. If not provided, the bot will create a new role."),
                reaction_roles: nextcord.TextChannel = SlashOption(required=False, description="Channel for prayer-time reaction roles. If not provided, the bot will create a new channel."),
                channel: nextcord.TextChannel = SlashOption(required=False, description="The channel to send prayer notifications to. If not provided, the bot will create a new channel."),
                athaan_channel: nextcord.VoiceChannel = SlashOption(required=False, description="The channel to play athaan in. If not provided, the bot will create a new channel.")):


    if db.servers.find_one({"_id": interaction.guild.id}):
        await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="You have already set up your server! To edit your preferences, use the /set command", color=nextcord.Color.red()), ephemeral=True)
        return
    try:
        await interaction.response.defer()
        geolocator = Nominatim(user_agent="geoapiExercises")
        location = geolocator.geocode(f"{city}, {country}")
        obj = TimezoneFinder()
        time_zone = obj.timezone_at(lng=location.longitude, lat=location.latitude)
        category = None
        if not role:
            # If no role is provided, create a new one called "tMuslim Notifications"
            role = await interaction.guild.create_role(name="🕌tMuslim Notifications", mentionable=True, color=nextcord.Color.green())
        if not channel:
            if not category:
                category = await interaction.guild.create_category("🕌tMuslim")
            # If no channel is provided, create a new one called "tMuslim Notifications"
            # Only people with "role" should be able to see the channel
            channel = await interaction.guild.create_text_channel(name="🕌tMuslim Notifications", category=category, topic="Channel for prayer pings", overwrites={interaction.guild.default_role: nextcord.PermissionOverwrite(read_messages=False, view_channel = False), role: nextcord.PermissionOverwrite(read_messages=True, view_channel = True, send_messages=False)})
        if not reaction_roles:
            if not category:
                category = await interaction.guild.create_category("🕌tMuslim")
            # If no channel is provided, create a new one called "tMuslim Notifications"
            reaction_roles = await interaction.guild.create_text_channel(name="🕌tMuslim Reaction Roles", category=category, topic="Channel for prayer reaction roles")
        if not athaan_channel:
            if not category:
                category = await interaction.guild.create_category("🕌tMuslim")
            # Make a new channel called "tMuslim Athaan"
            # Only people with "role" should be able to see the channel
            athaan_channel = await interaction.guild.create_voice_channel(name="🕌tMuslim Athaan", category=category, overwrites={interaction.guild.default_role: nextcord.PermissionOverwrite(connect=False), role: nextcord.PermissionOverwrite(connect=True)})
        message = await reaction_roles.send(embed=nextcord.Embed(title="Prayer Times", description="React to this message to get pinged for prayer times", color=nextcord.Color.green()))
        db.servers.insert_one({"_id": interaction.guild.id, "city": city, "country": country, "timezone": time_zone, "role": role.id, "channel": channel.id, "athaanchannel": athaan_channel.id, "reaction_role_message": message.id})
        await message.add_reaction("🕌")
        await interaction.followup.send(embed=nextcord.Embed(title="🕌 Setup Complete", description="Setup complete! tMuslim's feature are now active in this server", color=nextcord.Color.green()))
    except Exception as e:
        print(e)
        await interaction.followup.send(embed=nextcord.Embed(title="Error", description="An error occurred. Please check your city/country spelling and try again. If this problem persists, contact `TechMaster04#5002`. In the meantime, try a more common city/country in your timezone", color=nextcord.Color.red()))

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

def return_suffix(day):
    if day == 1 or day == 21 or day == 31:
        return "st"
    elif day == 2 or day == 22:
        return "nd"
    elif day == 3 or day == 23:
        return "rd"
    else:
        return "th"

@tMuslim.slash_command(guild_ids=tMuslim.guilds, name="hijridate", description="View the current hijri date")
async def hijridate(interaction: nextcord.Interaction):
    DD_MM_YY = datetime.now().strftime("%d-%m-%Y")
    hijri_date = requests.get(f"http://api.aladhan.com/v1/gToH?date={DD_MM_YY}").json()
    date = f"{hijri_date['data']['hijri']['day']}{return_suffix(int(hijri_date['data']['hijri']['day']))} of {hijri_date['data']['hijri']['month']['en']} {hijri_date['data']['hijri']['year']}\n{await conv_to_arabic(hijri_date['data']['hijri']['day'])} {hijri_date['data']['hijri']['month']['ar']} {await conv_to_arabic(hijri_date['data']['hijri']['year'])}"
    footer = f"Gregorian date: {hijri_date['data']['gregorian']['date']}"
    embed = nextcord.Embed(title="Hijri Date", description=date, color=nextcord.Color.green())
    embed.set_footer(text=footer)
    await interaction.response.send_message(embed=embed)

@tMuslim.slash_command(guild_ids=tMuslim.guilds, name="names", description="View the name and definition of one of Allah's names")
async def names(interaction: nextcord.Interaction, number: int = SlashOption(name="number", description="The number of the name you want to view", required=False)):
    if not number:
        number = random.randint(1, 99)
    if (number > 99 or number < 1):
        await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="Please enter a number between 1 and 99", color=nextcord.Color.red()), ephemeral=True)
        return
    name = requests.get(f"https://api.aladhan.com/v1/asmaAlHusna/{number}").json()
    embed = nextcord.Embed(title=name["data"][0]["name"] + " (" + name["data"][0]['transliteration'] + ")", description=name["data"][0]["en"]['meaning'], color=nextcord.Color.green())
    await interaction.response.send_message(embed=embed)

@tMuslim.command(pass_context=True)
async def delete(ctx):
    if ctx.message.author.id == 516413751155621899:
        # remove server from db
        db.servers.delete_one({"_id": ctx.guild.id})

@tMuslim.command(pass_context=True)
async def ping(ctx):
    # get role
    role = ctx.guild.get_role(db.servers.find_one({"_id": ctx.guild.id})["role"])
    channel = ctx.guild.get_channel(db.servers.find_one({"_id": ctx.guild.id})["channel"])
    await channel.send(f"{role.mention} tMuslim Prayer Notification Test")

@tasks.loop(seconds=40)
async def athan():
    for guild in tMuslim.guilds:
        server_info = db.servers.find_one({"_id": guild.id})
        if not server_info:
            continue
        
        hour, minute = await get_time(guild)
        prayer_times = await get_prayer_list(guild)
        next_prayer = await getNextPrayer(prayer_times, hour, minute)
        next_prayer_time = prayer_times["data"]["timings"][next_prayer]
        
        next_prayer_time = f"{hour:02d}:{minute:02d}"
        
        if f"{hour:02d}:{minute:02d}" == next_prayer_time:
            vc = guild.get_channel(server_info["athaanchannel"])
            
            # check if the bot is already in a voice channel
            voice = nextcord.utils.get(tMuslim.voice_clients, guild=guild) 
            if voice and voice.is_connected():
                continue
            voice = await vc.connect()

            role = guild.get_role(server_info["role"])
            members_with_role = [
                member
                for channel in guild.voice_channels
                for member in channel.members
                if role in member.roles
            ]
            for member in members_with_role:
                await member.move_to(vc)

            audio_path = "Athan1.wav" if next_prayer == "Fajr" else "Athan2.flac"
            audio = nextcord.FFmpegOpusAudio(audio_path)
            voice.play(audio, after=lambda x=None: (tMuslim.loop.create_task(voice.disconnect())))

            channel = guild.get_channel(server_info["channel"])
            await channel.send(f"{role.mention} {next_prayer} has started!")

        elif f"{hour:02d}:{minute:02d}" == f"{int(next_prayer_time[:2]):02d}:{int(next_prayer_time[3:5])-5:02d}":
            role = guild.get_role(server_info["role"])
            channel = guild.get_channel(server_info["channel"])
            await channel.send(f"{role.mention} {next_prayer} will start in 5 minutes!")


athan.start()

@tMuslim.event
async def on_ready():
    # set status to "Do not disturb"
    await tMuslim.change_presence(status=nextcord.Status.dnd, activity=nextcord.Game("Starting up... Please wait"))
    print(f"{tMuslim.user} is ready to go!")
    # set status to "Online"
    await tMuslim.change_presence(status=nextcord.Status.online, activity=nextcord.Game("Mosque Building Simulator"))
tMuslim.run(os.getenv("TMUSLIM_TOKEN"))