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
    if fajr:  # If we're calculating Fajr do this
        prayerHour += 24 if prayerHour < hour else 0
        time_diff = (prayerHour - hour) * 60 + prayerMin - minute
    else:  # If we're not calculating Fajr, we can calculate normally 
        prayerHour += 24 if prayerHour <= hour and prayerMin <= minute else 0
        time_diff = (prayerHour - hour - (prayerMin < minute)) * 60 + (prayerMin - minute) % 60
    return divmod(time_diff, 60)


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
    tz = pytz.timezone(db.servers.find_one({"_id": guild.id})["timezone"])
    return datetime.now(tz).hour, datetime.now(tz).minute

async def get_prayer_list(guild: nextcord.Guild):
    city = db.servers.find_one({"_id": guild.id})["city"]  # get city
    country = db.servers.find_one({"_id": guild.id})["country"]  # get country
    time_in_server_tz = datetime.now(pytz.timezone(db.servers.find_one({"_id": guild.id})["timezone"]))
    
    # To avoid getting API-rate limited, we will cache the prayer times for 24 hours in Mongodb
    
    # First, we check if the prayer times are cached in the database
    # Check if db.prayerTimes.find_one({"_id": f"city:country"}) is not None
    if db.prayerTimes.find_one({"_id": f"{city}:{country}"}):
        # Check if the prayer times are for todays date (in the timezone of the server)
        if db.prayerTimes.find_one({"_id": f"{city}:{country}"})["date"] == time_in_server_tz.strftime("%d/%m/%Y"):
            return db.prayerTimes.find_one({"_id": f"{city}:{country}"})["prayerTimes"]
    db.prayerTimes.delete_one({"_id": f"{city}:{country}"})
    # If the prayer times are not for todays date (or they don't exist), we will delete the old prayer times from the database and get new ones
    
    times = requests.get(f"http://api.aladhan.com/v1/timingsByCity?city={city}&country={country}").json()
    # Append the prayer times to the database
    db.prayerTimes.insert_one({"_id": f"{city}:{country}", "prayerTimes": times, "date": time_in_server_tz.strftime("%d/%m/%Y")})
    return times

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

@tasks.loop(seconds=60)
async def athan():
    for guild in tMuslim.guilds:
        if not db.servers.find_one({"_id": guild.id}):
            continue
        hour, minute = await get_time(guild)  # get time
        prayerTimes = await get_prayer_list(guild)
        nextPrayer = await getNextPrayer(prayerTimes, hour, minute)  # get next prayer
        nextPrayerTime = prayerTimes["data"]["timings"][nextPrayer]  # get next prayer time from API data
        # check if current time is equal to nextPrayerTime
        if hour == int(nextPrayerTime[:2]) and minute == int(nextPrayerTime[3:5]) or True:
            # check if bot is in VC
            if guild.voice_client:
                continue
            # get channel for VC
            vc = guild.get_channel(db.servers.find_one({"_id": guild.id})["athaanchannel"])
            await vc.connect()
            role = guild.get_role(db.servers.find_one({"_id": guild.id})["role"])
            # Get a list of everyone in a VC, and check if they have the role
            # If they do, move them to the athan VC
            server_vcs = guild.voice_channels
            for channel in server_vcs:
                for member in channel.members:
                    if role in member.roles:
                        await member.move_to(vc)
            if nextPrayer == "Fajr":
                audio = nextcord.FFmpegOpusAudio("Athan1.wav")
            else:
                audio = nextcord.FFmpegOpusAudio('Athan2.flac')
            voice = guild.voice_client  # Getting the voice client
            # leave the vc after playing the audio
            player = voice.play(audio, after=lambda x=None: (tMuslim.loop.create_task(voice.disconnect())))
            # get role to ping
            role = guild.get_role(db.servers.find_one({"_id": guild.id})["role"])
            channel = guild.get_channel(db.servers.find_one({"_id": guild.id})["channel"])
            await channel.send(f"{role.mention} {nextPrayer} has started!")
        # if it's five minutes before the next prayer, send a reminder
        if hour == int(nextPrayerTime[:2]) and minute == int(nextPrayerTime[3:5]) - 5:
            role = guild.get_role(db.servers.find_one({"_id": guild.id})["role"])
            channel = guild.get_channel(db.servers.find_one({"_id": guild.id})["channel"])
            await channel.send(f"{role.mention} {nextPrayer} will start in 5 minutes!")
athan.start()

@tMuslim.event
async def on_ready():
    # set status to "Do not disturb"
    await tMuslim.change_presence(status=nextcord.Status.dnd, activity=nextcord.Game("Starting up... Please wait"))
    print(f"{tMuslim.user} is ready to go!")
    # set status to "Online"
    await tMuslim.change_presence(status=nextcord.Status.online, activity=nextcord.Game("Mosque Building Simulator"))
tMuslim.run(os.getenv("TMUSLIM_TOKEN"))