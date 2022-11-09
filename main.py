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

client = commands.Bot(command_prefix='tmm', intents=intents, activity = nextcord.Activity(type=nextcord.ActivityType.listening, name="Qur'aan")) #initializing the bot

mongo = MongoClient(os.getenv("PYMONGO_CREDS"))

db = mongo.tMuslim

@client.slash_command(guild_ids=client.guilds, name = "nextprayer",description="Get the next prayer time")
async def nextprayer(interaction: Interaction):
    if (not db.servers.find_one({"_id": interaction.guild.id})):
            await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="You haven't set up your server yet! Please use /setup command to set up your server.", color=nextcord.Color.red()), ephemeral=True)
            return
    city = db.servers.find_one({"_id": interaction.guild.id})["city"] #get city
    country = db.servers.find_one({"_id": interaction.guild.id})["country"] #get country
    timezone = db.servers.find_one({"_id": interaction.guild.id})["timezone"] #get UTC offset
    tz = pytz.timezone(timezone) #get timezone
    time = datetime.now(tz) #get current time
    hour = time.hour
    minute = time.minute
    prayerTimes = requests.get(f"http://api.aladhan.com/v1/timingsByCity?city={city}&country={country}&method=2").json()
    nextPrayer = await getNextPrayer(prayerTimes, hour, minute) #get next prayer
    nextPrayerTime = prayerTimes["data"]["timings"][nextPrayer] #get next prayer time from API data

    timeUntil = await calculateRemainingTime(int(nextPrayerTime[0:2]), int(nextPrayerTime[3:5]), hour, minute, nextPrayer == "Fajr") #calculate remaining time
    await interaction.response.send_message(embed=nextcord.Embed(title="Next Prayer", description=f"The next prayer is **{nextPrayer}** in **{timeUntil[0]} hours and {timeUntil[1]} minutes** ({nextPrayerTime})", color=nextcord.Color.green()))
    
@client.slash_command(guild_ids=client.guilds, description="Setup your server for use with the bot")
async def setup(interaction: nextcord.Interaction, city: str = SlashOption(required=True, description="Your city"), country: str = SlashOption(required=True, description="Your country")):
    if (db.servers.find_one({"_id": interaction.guild.id})):
        await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="You have already set up your server! To edit your preferences, use the /set command", color=nextcord.Color.red()), ephemeral=True)
        return
    try:
        geolocator = Nominatim(user_agent="geoapiExercises")
        location = geolocator.geocode(f"{city}, {country}")
        obj = TimezoneFinder()
        time_zone = obj.timezone_at(lng=location.longitude, lat=location.latitude)
        db.servers.insert_one({"_id": interaction.guild.id, "timezone": time_zone, "city": city, "country": country})
        await interaction.response.send_message(embed = nextcord.Embed(title = "Setup Complete", description = "Setup complete. tMuslim's feature are now active in this server", color = nextcord.Color.green()))
    except:
        await interaction.response.send_message(embed = nextcord.Embed(title = "Error", description = "An error occurred. Please check your city/country spelling and try again. If this problem persists, contact `TechMaster04#5002`. In the meantime, try a more common city/country in your timezone", color = nextcord.Color.red()))            
 
@tasks.loop(seconds=60)
async def athan():
    for guild in client.guilds:
        if (not db.servers.find_one({"_id": guild.id})):
            continue
        city = db.servers.find_one({"_id": guild.id})["city"] #get city
        country = db.servers.find_one({"_id": guild.id})["country"] #get country
        timezone = db.servers.find_one({"_id": guild.id})["timezone"] #get UTC offset
        tz = pytz.timezone(timezone) #get timezone
        time = datetime.now(tz) #get current time
        hour = time.hour
        minute = time.minute
        prayerTimes = requests.get(f"http://api.aladhan.com/v1/timingsByCity?city={city}&country={country}&method=2").json()
        nextPrayer = await getNextPrayer(prayerTimes, hour, minute) #get next prayer
        nextPrayerTime = prayerTimes["data"]["timings"][nextPrayer] #get next prayer time from API data
        #check if current time is equal to nextPrayerTime
        if (hour == int(nextPrayerTime[:2]) and minute == int(nextPrayerTime[3:5])):
            currentMax = 0
            currentVC = None
            for channel in guild.voice_channels:
                users = len(channel.voice_states.keys())
                if users > currentMax:
                    currentMax = users
                    currentVC = channel
                #check if bot is already in VC
            if (currentVC and currentVC.permissions_for(guild.me).connect and currentVC.permissions_for(guild.me).speak and not guild.voice_client):
                await currentVC.connect()
                audio = None
                #if next prayer is fajr, play Athan1
                if (nextPrayer == "Fajr"):
                    audio = nextcord.FFmpegOpusAudio("Athan1.wav")
                else:
                    audio = nextcord.FFmpegOpusAudio('Athan2.mp3')
                voice = guild.voice_client #Getting the voice client
                #leave the vc after playing the audio
                player = voice.play(audio, after=lambda x=None: (client.loop.create_task(voice.disconnect())))
athan.start()

async def calculateRemainingTime(prayerHour, prayerMin, hour, minute, fajr):
    localMinLeft = 0
    localHourLeft = 0
    localHours = prayerHour
    
    if (fajr) : #If we're calculating Fajr do this (This is because calculating Fajr is a bit more involved than other prayers)
        if (hour == 0) :
            localMinLeft = 60 - minute
            localHours -= 1
            localMinLeft += int(prayerMin)
        if (localMinLeft >= 60) :
            localHourLeft += 1
            localMinLeft = localMinLeft - 60
            localHourLeft += int(prayerHour)
        
        elif (hour > 0 and hour < 5) :
            localMinLeft = 60 - minute
            localHourLeft -= 1
            localMinLeft += int(prayerMin)
            
        if (localMinLeft >= 60) :
            localHourLeft += 1
            localMinLeft = localMinLeft - 60        
            localHourLeft = localHourLeft + (int(prayerHour) - hour())
        
        else :
            localMinLeft = 60 - minute
            localHourLeft -= 1
            localMinLeft += int(prayerMin)
        
        if (localMinLeft >= 60) :
            localHourLeft += 1
            localMinLeft = localMinLeft - 60
        
        localHourLeft += 24 - hour

        localHourLeft += int(prayerHour)
        if (localMinLeft >= 60):
            localHourLeft += 1
            localMinLeft = localMinLeft - 60
        return localHourLeft, localMinLeft
    localMinLeft = 60 - minute
    localHours -= 1
    localMinLeft += prayerMin
    if (localMinLeft >= 60) :
        localHourLeft += 1
        localMinLeft = localMinLeft - 60        
    localHourLeft = localHourLeft + ((localHours) - hour)
    return localHourLeft, localMinLeft
    
async def getNextPrayer(prayerTimes, hour, minute):
    fajrTime = prayerTimes["data"]["timings"]["Fajr"]
    duhurTime = prayerTimes["data"]["timings"]["Dhuhr"]
    asrTime = prayerTimes["data"]["timings"]["Asr"]
    maghribTime = prayerTimes["data"]["timings"]["Maghrib"]
    ishaaTime = prayerTimes["data"]["timings"]["Isha"]
    if (hour > int(ishaaTime[0:2]) or hour <= int(fajrTime[0:2])):
        if (hour == int(fajrTime[0:2])):
            if (minute <= int(fajrTime[3:5])):
                return "Fajr"
            else:
                return "Dhuhr"
        return "Fajr"
    elif (hour >= int(fajrTime[0:2]) and hour <= int(duhurTime[0:2])):
        if (hour == int(duhurTime[0:2])):
            if (minute <= int(duhurTime[3:5])):
                return "Dhuhr"
            else:
                return "Asr"
        return "Dhuhr"
    elif (hour >= int(duhurTime[0:2]) and hour <= int(asrTime[0:2])):
        if (hour == int(asrTime[0:2])):
            if (minute <= int(asrTime[3:5])):
                return "Asr"
            else:
                return "Maghrib"
        return "Asr"
    elif (hour >= int(asrTime[0:2]) and hour <= int(maghribTime[0:2])):
        if (hour == int(maghribTime[0:2])):
            if (minute <= int(maghribTime[3:5])):
                return "Maghrib"
            else:
                return "Isha"
        return "Maghrib"
    elif (hour >= int(maghribTime[0:2]) and hour <= int(ishaaTime[0:2])):
        if (hour == int(ishaaTime[0:2])):
            if (minute <= int(ishaaTime[3:5])):
                return "Isha"
            else:
                return "Fajr"
        return "Isha"
    
#on ready event
@client.event
async def on_ready():
    print(f"{client.user} is ready to go!")
client.run(os.getenv("TMUSLIM_TOKEN"))