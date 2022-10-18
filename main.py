from asyncio import tasks
import os
import nextcord
from nextcord.ext import commands
from pymongo import MongoClient
import requests
from datetime import datetime
from nextcord.ext import tasks
import dotenv

dotenv.load_dotenv("token.env")

intents = nextcord.Intents.all()

client = commands.Bot(command_prefix='tmm', intents=intents, activity = nextcord.Activity(type=nextcord.ActivityType.listening, name="quran")) #initializing the bot

mongo = MongoClient(os.getenv("PYMONGO_CREDS"))

db = mongo.servers


#command to get the next prayer time
@client.command(pass_context=True)
async def nextPrayer(ctx):
    #check if server is setup (has entry in database)
    if (not db.servers.find_one({"_id": ctx.message.guild.id})):
        await ctx.send("Server not setup. Please use the setup command to setup the server.")
        return
    else:
        #get server settings
        city = db.servers.find_one({"_id": ctx.message.guild.id})["city"] #get city
        country = db.servers.find_one({"_id": ctx.message.guild.id})["country"] #get country
        utcOffset = db.servers.find_one({"_id": ctx.message.guild.id})["timezone"] #get UTC offset
        #get UTC time
        prayerTimes = requests.get("http://api.aladhan.com/v1/timingsByCity?city={0}&country={1}&method=2".format(city,country)).json()
        #get current time in UTC
        time = datetime.utcnow()
        #adjust UTC time to match users timezone
        hour = time.hour + int(utcOffset) 
        if (hour < 0): #if time is negative, add 24 to get correct time
            hour = 24 + hour
        minute = time.minute   #get minyte
        nextPrayer = await getNextPrayer(prayerTimes, hour, minute) #get next prayer
        nextPrayerTime = prayerTimes["data"]["timings"][nextPrayer] #get next prayer time from API data
        
        timeUntil = await calculateRemainingTime(int(nextPrayerTime[0:2]), int(nextPrayerTime[3:5]), hour, minute, nextPrayer == "Fajr") #calculate remaining time
        await ctx.send("The next prayer is {0} at {1}, in {2} hours and {3} minutes".format(nextPrayer, nextPrayerTime, timeUntil[0], timeUntil[1]))        

@client.command(pass_context=True)
async def setup(ctx):
    await ctx.send("Welcome to tMuslim - Discord Edition! For best results, please specify your time zone and city.\n\nPlease enter your offset from UTC:")
    #get message from user
    timezone = await client.wait_for('message', check=lambda message: message.author == ctx.author)
    #check if user entered a number
    timeZone = int(timezone.content)
    await ctx.send("Please enter your city:")
    city = await client.wait_for('message', check=lambda message: message.author == ctx.author)
    await ctx.send("Please enter your country:")
    country = await client.wait_for('message', check=lambda message: message.author == ctx.author)
    #check if city is valid
    requestURL = " http://api.aladhan.com/v1/calendarByCity?city={0}&country={1}&method=2"
    #make request
    request = requests.get(requestURL.format(city,country))
    #check request code
    if request.status_code == 404:
        await ctx.send("Setup Failed. Invalid city or country. Please try again.")
    else:
        #save data to db
        db.servers.insert_one({"_id": ctx.guild.id, "timezone": timezone.content, "city": city.content, "country": country.content})
        await ctx.send("Setup Successful! tMuslim can now be used in this server!")  

@tasks.loop(seconds=60)
async def athan():
    for guild in client.guilds:
        if (not db.servers.find_one({"_id": guild.id})):
            continue
        else:
            city = db.servers.find_one({"_id": guild.id})["city"] #get city
            country = db.servers.find_one({"_id": guild.id})["country"] #get country
            utcOffset = db.servers.find_one({"_id": guild.id})["timezone"] #get UTC offset
            #get UTC time
            prayerTimes = requests.get("http://api.aladhan.com/v1/timingsByCity?city={0}&country={1}&method=2".format(city,country)).json()
            #get current time in UTC
            time = datetime.utcnow()
            #adjust UTC time to match users timezone
            hour = time.hour + int(utcOffset) 
            if (hour < 0): #if time is negative, add 24 to get correct time
                hour = 24 + hour
            minute = time.minute   #get minyte
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
                        audio = nextcord.FFmpegOpusAudio("Athan1.mp3")
                    else:
                        audio = nextcord.FFmpegOpusAudio('Athan2.wav')
                    voice = guild.voice_client #Getting the voice client
                    #leave the vc after playing the audio
                    player = voice.play(audio, after=lambda x=None: (client.loop.create_task(voice.disconnect())))

@client.command(pass_context=True)  
async def joinVC(ctx):
    VC = ctx.message.author.voice.channel
    await VC.connect()
    audio = nextcord.FFmpegOpusAudio('Athan2.mp3')
    voice = ctx.message.guild.voice_client #Getting the voice client
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
    else: #Otherwise proceed normally
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