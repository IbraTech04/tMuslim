import os
import random
from typing import Optional
import nextcord
from nextcord.ext import commands, tasks
from Mongo import ServerManager
from APITools import APIHelper
from TimeManager import TimeManager
import datetime
from PrayerManager import PrayerManager
class RamadanSpecial(commands.Cog):
    """
    Class containing all the Ramadan special commands
    
    ====== Attributes ======
    db: ServerManager
        The database manager used to access the database
    api: APIHelper
        The API helper used to access the API
    bot: commands.Bot
        The bot instance
    
    
    ======= Representation Invariants =======
    None! 
    Yay!
    
    """
    
    def __init__(self, client: commands.Bot, db: ServerManager, prayermanager: PrayerManager) -> None:
        self.bot = client
        self.database = db
        self.api = APIHelper()
        self.timehelper = TimeManager()
        self.prayermanager = prayermanager
    
    @nextcord.slash_command(description="ramadan")
    async def ramadan(self, interaction: nextcord.Interaction):
        pass
    
    @ramadan.subcommand(description="Returns the days left until Eid")
    async def days_left(self, interaction: nextcord.Interaction) -> None:
        # Step one: Get the current date relative to the server's timezone
        # But before that, check if the server is registered
        if not await self.database.is_server_registered(interaction.guild.id):
            # Set the date to the current date
            date = datetime.datetime.now()
        # Otherwise, get the date from the database
        date = await self.timehelper.get_time_in_timezone(await self.database.get_timezone(interaction.guild.id))
        days_until_eid = await self.api.get_eid_al_adha(date, await self.database.get_timezone(interaction.guild.id))
        
        # time to make an embed
        embed = nextcord.Embed(title="Days left until Eid al-Adha", description=f"{days_until_eid} days left until Eid al-Adha!", color=nextcord.Color.green())
        await interaction.response.send_message(embed=embed)
    
    @ramadan.subcommand(description="Return a summary of today's fasting times")
    async def summary(self, interaction: nextcord.Interaction) -> None:
        # Step one: make sure the server is registered
        if not await self.database.is_server_registered(interaction.guild.id):
            await interaction.response.send_message("This server is not registered! Please use the /setup command to register this server!")
            return
        
        location = await self.database.get_server_location(interaction.guild.id)
        time = await self.timehelper.get_time_in_timezone(await self.database.get_timezone(interaction.guild.id))
        prayer_times = await self.prayermanager._get_prayer_list(location, time)
        
        embed = nextcord.Embed(title="Ramadan Summary", description=f"Here is a summary of today's fasting times for {location}", color=nextcord.Color.green())
        embed.add_field(name="Fajr", value=prayer_times["Fajr"], inline=False)
        embed.add_field(name="Maghrib", value=prayer_times["Maghrib"], inline=False)

        
        total_fast_time = await self.timehelper.calculateRemainingTime(int(prayer_times["Maghrib"][0:2]), int(prayer_times["Maghrib"][3:5]), int(prayer_times["Fajr"][0:2]), int(prayer_times["Fajr"][3:5]), False)
        total_fast_time = f"{total_fast_time[0]} hours and {total_fast_time[1]} minutes"
        embed.add_field(name="Total Fast Time", value=total_fast_time, inline=False)
        await interaction.response.send_message(embed=embed)