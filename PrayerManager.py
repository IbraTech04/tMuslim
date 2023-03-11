import nextcord
from nextcord.ext import commands, tasks
from Mongo import ServerManager
from APITools import APIHelper
from TimeManager import TimeManager


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
        formatted_location = f"{location[0]}:{location[1]}"

        time = await self.timehelper.get_time_in_timezone(await self.database.get_timezone(interaction.guild.id))
        hour = time.hour
        minute = time.minute

        if self.database.is_location_in_database(location, time):
            prayerTimes = await self.database.get_prayer_list(location)
        else:
            prayerTimes = await self.api.get_prayer_time_list(location[0], location[1], time, 2)
            # add date to the dictionary
            prayerTimes["date"] = f"{time.year}/{time.month}/{time.day}"
            await self.database.insert_prayer_list(location, prayerTimes)

        # get next prayer
        nextPrayer = await self._get_next_prayer(prayerTimes, hour, minute)
        # get next prayer time from API data
        nextPrayerTime = prayerTimes[nextPrayer]
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

        if self.database.is_location_in_database(location, time):
            prayerTimes = await self.database.get_prayer_list(location)
        else:
            prayerTimes = await self.api.get_prayer_time_list(location[0], location[1], time, 2)
            # add date to the dictionary
            prayerTimes["date"] = f"{time.year}/{time.month}/{time.day}"
            await self.database.insert_prayer_list(location, prayerTimes)
        hour = time.hour
        minute = time.minute

        embed = nextcord.Embed(
            title="Prayer Times", description=f"Prayer times for {location[0]}, {location[1]} on {time.month}/{time.day}", color=nextcord.Color.green())
        next_prayer = await self._get_next_prayer(prayerTimes, hour, minute)

        # Sort the prayer times in order - Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha

        for prayer in self.PRAYER_ORDER:
            if prayer == next_prayer:
                embed.add_field(
                    name=f"**{prayer}**", value=f"**{prayerTimes[prayer]}**", inline=False)
                continue
            embed.add_field(
                name=f"{prayer}", value=f"{prayerTimes[prayer]}", inline=False)

        await interaction.response.send_message(embed=embed)

    @tasks.loop(seconds=60)
    async def athan(self):
        for guild in self.bot.guilds:
            if not await self.database.is_server_registered(guild.id):
                continue

            location = await self.database.get_server_location(guild.id)
            time = await self.timehelper.get_time_in_timezone(await self.database.get_timezone(guild.id))
            if self.database.is_location_in_database(location, time):
                prayer_times = await self.database.get_prayer_list(location)
            else:
                prayer_times = await self.api.get_prayer_time_list(location[0], location[1], time, 2)
                # add date to the dictionary
                prayer_times["date"] = f"{time.year}/{time.month}/{time.day}"
                await self.database.insert_prayer_list(location, prayer_times)

            next_prayer = await self._get_next_prayer(prayer_times, time.hour, time.minute)
            next_prayer_time = prayer_times[next_prayer]

            hour = time.hour
            minute = time.minute

            if f"{hour:02d}:{minute:02d}" == next_prayer_time:
                vc = guild.get_channel(
                    self.database.get_athaan_chanel(guild.id))

                # check if the bot is already in a voice channel
                voice = nextcord.utils.get(self.bot.voice_clients, guild=guild)
                if voice and voice.is_connected():
                    continue
                voice = await vc.connect()

                role = guild.get_role(self.database.get_athaan_role(guild.id))
                members_with_role=[
                    member
                    for channel in guild.voice_channels
                    for member in channel.members
                    if role in member.roles
                ]
                for member in members_with_role:
                    await member.move_to(vc)

                audio_path="Athan1.wav" if next_prayer == "Fajr" else "Athan2.flac"
                audio=nextcord.FFmpegOpusAudio(audio_path)
                voice.play(audio, after=lambda x=None: (
                    self.bot.loop.create_task(voice.disconnect())))

                channel=guild.get_channel(self.database.get_announcement_channel(guild.id))
                await channel.send(f"{role.mention} {next_prayer} has started!")

            elif f"{hour:02d}:{minute:02d}" == f"{int(next_prayer_time[:2]):02d}:{(int(next_prayer_time[3:5])-5)%60:02d}":
                role = guild.get_role(self.database.get_athaan_role(guild.id))
                channel=guild.get_channel(self.database.get_announcement_channel(guild.id))
                await channel.send(f"{role.mention} {next_prayer} will start in 5 minutes!")
