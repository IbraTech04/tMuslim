import os
import random
from typing import Optional
import nextcord
from nextcord.ext import commands, tasks
from Mongo import ServerManager
from APITools import APIHelper
from TimeManager import TimeManager
import datetime

class PrayerManager(commands.Cog):
    """
    Class which deals with all prayer-related functions for the bot
    Like pinging for prayers, joining prayer channels, etc.

    == Attributes ==
    bot: The bot object
    PRAYER_ORDER: The order of the prayers
    """
    bot: commands.Bot
    PRAYER_ORDER: list[str]

    def __init__(self, bot: commands.Bot, database: ServerManager):
        self.bot = bot
        self.database = database
        self.api = APIHelper()
        self.timehelper = TimeManager()
        self.PRAYER_ORDER = ["Fajr", "Sunrise",
            "Dhuhr", "Asr", "Maghrib", "Isha"]
        self.athan.start()

    async def _get_next_prayer(self, prayer_times, hour, minute):
        # Remove the _id key from the dictionary, if it exists
        prayer_times.pop("_id", None)
        current_time = hour * 60 + minute

        for i in self.PRAYER_ORDER:
            prayer_hour = int(prayer_times[i][0:2])
            prayer_minute = int(prayer_times[i][3:5])
            prayer_time_minutes = prayer_hour * 60 + prayer_minute
            if prayer_time_minutes >= current_time:
                return i
        # If we've reached the end of the list, the next prayer is Fajr the next day
        return "Fajr"

    async def _get_prayer_list(self, location, time):
        if self.database.is_location_in_database(location, time):
            prayer_times = await self.database.get_prayer_list(location)
        else:
            prayer_times = await self.api.get_prayer_time_list(location[0], location[1], time)
            # add date to the dictionary
            prayer_times["date"] = f"{time.year}/{time.month}/{time.day}"
            await self.database.insert_prayer_list(location, prayer_times)
        return prayer_times
            
    @nextcord.slash_command(name="nextprayer", description="Returns the time until the next prayer")
    async def nextprayer(self, interaction: nextcord.Interaction):
        """
        Method which returns the time until the next prayer
        Precondition: The server is registered
        """
        # Check if the server is registered
        if not await self.database.is_server_registered(interaction.guild.id):
            await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="You haven't set up your server yet! Please use /setup command to set up your server.", color=nextcord.Color.red()), ephemeral=True)

        # Get the location of the server
        location = await self.database.get_server_location(interaction.guild.id)

        time = await self.timehelper.get_time_in_timezone(await self.database.get_timezone(interaction.guild.id))
        hour = time.hour
        minute = time.minute
        prayer_times = await self._get_prayer_list(location, time)
        nextPrayer = await self._get_next_prayer(prayer_times, hour, minute)

        # If the next prayer is Fajr, we need to check if it's today's fajr or tomorrow's
        # i.e: if we're calculating for Fajr after Ishaa, we need to get tomorrow's Fajr

        # Check if the next prayer is Fajr. If it is fajr, check if the current time is past Ishaa
        if nextPrayer == "Fajr" and (hour > int(prayer_times["Isha"][0:2]) or (hour == int(prayer_times["Isha"][0:2]) and minute > int(prayer_times["Isha"][3:5]))):
            time = time + datetime.timedelta(days=1)
            prayer_times = await self._get_prayer_list(location, time)

        nextPrayerTime = prayer_times[nextPrayer]
        # calculate remaining time
        timeUntil = await self.timehelper.calculateRemainingTime(int(nextPrayerTime[0:2]), int(nextPrayerTime[3:5]), hour, minute, nextPrayer == "Fajr")
        await interaction.response.send_message(embed=nextcord.Embed(title="Next Prayer", description=f"The next prayer is **{nextPrayer}** in **{timeUntil[0]} hours and {timeUntil[1]} minutes** ({nextPrayerTime})", color=nextcord.Color.green()))

    @nextcord.slash_command(name="prayerlist", description="View a list of all prayer times in your city")
    async def prayerlist(self, interaction: nextcord.Interaction):
        """
        Method which returns a list of all prayer times in the user's city
        Preconditions: The server must be registered
        """
        if not await self.database.is_server_registered(interaction.guild.id):
            await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="You haven't set up your server yet! Please use /setup command to set up your server.", color=nextcord.Color.red()), ephemeral=True)

        location = await self.database.get_server_location(interaction.guild.id)
        time = await self.timehelper.get_time_in_timezone(await self.database.get_timezone(interaction.guild.id))

        prayer_times = await self._get_prayer_list(location, time)
        hour = time.hour
        minute = time.minute


        next_prayer = await self._get_next_prayer(prayer_times, hour, minute)

        if next_prayer == "Fajr" and (hour > int(prayer_times["Isha"][0:2]) or (hour == int(prayer_times["Isha"][0:2]) and minute > int(prayer_times["Isha"][3:5]))):
            time = time + datetime.timedelta(days=1)
            prayer_times = await self._get_prayer_list(location, time)
        embed = nextcord.Embed(
            title="Prayer Times", description=f"Prayer times for {location[0]}, {location[1]} on {time.month}/{time.day}", color=nextcord.Color.green())
        for prayer in self.PRAYER_ORDER:
            if prayer == next_prayer:
                embed.add_field(
                    name=f"**{prayer}**", value=f"**{prayer_times[prayer]}**", inline=False)
                continue
            embed.add_field(
                name=f"{prayer}", value=f"{prayer_times[prayer]}", inline=False)

        await interaction.response.send_message(embed=embed)

    async def disconnect_from_vc(self, guild: nextcord.Guild):
        """
        Method which disconnects the bot from the voice channel
        """
        if guild.voice_client is not None:
            await guild.voice_client.disconnect()

    @tasks.loop(seconds=60)
    async def athan(self):
        for guild in self.bot.guilds:
            if not await self.database.is_server_registered(guild.id):
                continue

            location = await self.database.get_server_location(guild.id)
            time = await self.timehelper.get_time_in_timezone(await self.database.get_timezone(guild.id))
            prayer_times = await self._get_prayer_list(location, time)
            
            next_prayer = await self._get_next_prayer(prayer_times, time.hour, time.minute)
            next_prayer_time = prayer_times[next_prayer]

            hour = time.hour
            minute = time.minute

            if f"{hour:02d}:{minute:02d}" == next_prayer_time:
                if next_prayer != "Sunrise":
                    vc = guild.get_channel(await
                        self.database.get_athaan_chanel(guild.id))

                    # check if the bot is already in a voice channel
                    voice = nextcord.utils.get(self.bot.voice_clients, guild=guild)
                    if voice and voice.is_connected():
                        continue
                    voice = await vc.connect()

                    role = guild.get_role(await self.database.get_athaan_role(guild.id))
                    members_with_role=[
                        member
                        for channel in guild.voice_channels
                        for member in channel.members
                        if role in member.roles
                    ]
                    for member in members_with_role:
                        await member.move_to(vc)

                    athaans_path = os.path.join(os.getcwd(), "Athaans")
                    if next_prayer == "Fajr":
                        athaans_path = os.path.join(athaans_path, "Fajr")
                    else:
                        athaans_path = os.path.join(athaans_path, "Other")
                    # pick a random athaan 
                    audio_path = os.path.join(athaans_path, random.choice(os.listdir(athaans_path)))
                    audio=nextcord.FFmpegOpusAudio(audio_path)
                    voice.play(audio, after=lambda x=None: (
                        self.bot.loop.create_task(self.disconnect_from_vc(guild))))

                channel=guild.get_channel(await self.database.get_announcement_channel(guild.id))
                await channel.send(f"{role.mention} {next_prayer} has started!")

            elif f"{hour:02d}:{minute:02d}" == f"{int(next_prayer_time[:2]):02d}:{(int(next_prayer_time[3:5])-5)%60:02d}":
                # Check to see if they've enabled 5-minute reminders
                if not await self.database.get_five_minute_reminder(guild.id):
                    continue
                role = guild.get_role(await self.database.get_athaan_role(guild.id))
                channel=guild.get_channel(await self.database.get_announcement_channel(guild.id))
                await channel.send(f"{role.mention} {next_prayer} will start in 5 minutes!")
    
    @nextcord.slash_command(name="names", description="Returns a random name of Allah and its meaning")
    async def names(self, interaction:nextcord.Interaction, number: int = nextcord.SlashOption(name="number", description="The number of the name you want to view", required=False)):
        """
        Method which returns a random name of Allah and its meaning
        """
        embed = nextcord.Embed(title="99 Names of Allah", color=nextcord.Color.green())
        if number is None:
            name = await self.api.get_99_names()
        else:
            name = await self.api.get_99_names(number)
        embed.add_field(name="Name", value=name[0])
        embed.add_field(name="Transliteration", value=name[1])
        embed.add_field(name="Meaning", value=name[2])
        await interaction.response.send_message(embed=embed)
        
    @nextcord.slash_command(name="hijridate", description="Get the current Hijri date")
    async def hijridate(self, interaction:nextcord.Interaction):
        """
        Method which returns the current Hijri date
        """
        embed = nextcord.Embed(title="Hijri Date", color=nextcord.Color.green())
        if not await self.database.is_server_registered(interaction.guild.id):
            date = datetime.datetime.now()
            embed.set_footer(text="Server not registered; using UTC time. The date may be incorrect, use /setup to set up your server.")
        else:
            date = await self.timehelper.get_time_in_timezone(await self.database.get_timezone(interaction.guild.id))
        hijri_date = await self.api.get_hijri_date(date)
        
        ar_year = await self.timehelper.conv_to_arabic(hijri_date[2])
        ar_day = await self.timehelper.conv_to_arabic(hijri_date[0])
        
        description = f"{await self.timehelper.return_suffix(hijri_date[0])} of {hijri_date[1]} {hijri_date[2]}\n {ar_day} {hijri_date[3]} {ar_year}"
        
        embed.add_field(name="Date", value=description)
        await interaction.response.send_message(embed=embed)