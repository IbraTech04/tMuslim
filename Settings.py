import nextcord
from nextcord import SlashOption
from nextcord.ext import commands, application_checks
from timezonefinder import TimezoneFinder
from Mongo import ServerManager
import pytz
from geopy.geocoders import Nominatim
import json
import PrayerManager

class Settings(commands.Cog):
    """
    Class which handles all settings-related commands
    i.e: setup, location, etc.
    """
    def __init__(self, bot: commands.Bot, database: ServerManager, athan_loops: dict, prayers: PrayerManager):
        self.bot = bot
        self.database = database    
        self.athan_loops = athan_loops
        self.prayers = prayers
    
    @nextcord.slash_command(name="settings", description="base command for settings")
    async def settings(self, interaction: nextcord.Interaction):
        pass
    
    @settings.subcommand(name="reminders", description="Enable or disable 5-minute warnings for prayers")
    @application_checks.has_guild_permissions(manage_guild=True)
    async def toggle(self, interaction: nextcord.Interaction, value: str = SlashOption(required=True, description="The value to set", choices=["On", "Off"])):
        value = value == "On"
        if not await self.database.is_server_registered(interaction.guild.id):
            await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="Your server is not registered!", color=nextcord.Color.red()), ephemeral=True)
            return
        # Get the current value of the setting
        await self.database.set_five_minute_reminder(interaction.guild.id, value)
        await interaction.response.send_message(embed=nextcord.Embed(title="Success", description=f"5-minute reminder set to {value}", color=nextcord.Color.green()), ephemeral=True)
        
        
    @settings.subcommand(name="unregister", description="Delete all data associated with your server")
    @application_checks.has_guild_permissions(manage_guild=True)
    async def unregister(self, interaction: nextcord.Interaction):
        if not await self.database.is_server_registered(interaction.guild.id):
            await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="Your server is not registered!", color=nextcord.Color.red()), ephemeral=True)
            return
        self._unregister(interaction.guild)
        await interaction.response.send_message(embed=nextcord.Embed(title="Success", description="Your server has been unregistered!", color=nextcord.Color.green()), ephemeral=True)
    
    def _unregister(self, guild: nextcord.Guild):
        self.database.unregister_server(guild.id)
        # Remove them from teh athan_loops
        self.athan_loops[guild.id].cancel()
        del self.athan_loops[guild.id]
    
    @settings.subcommand(name="register", description="Setup your server for use with the bot")
    @application_checks.has_guild_permissions(manage_guild=True)
    async def setup(self, interaction: nextcord.Interaction, city: str = SlashOption(required=True, description="Your city"),
                    country: str = SlashOption(required=True, description="Your country"),
                    role: nextcord.Role = SlashOption(required=False, description="The role to ping for prayer times. If not provided, the bot will create a new role."),
                    reaction_roles: nextcord.TextChannel = SlashOption(required=False, description="Channel for prayer-time reaction roles. If not provided, the bot will create a new channel."),
                    channel: nextcord.TextChannel = SlashOption(required=False, description="The channel to send prayer notifications to. If not provided, the bot will create a new channel."),
                    athaan_channel: nextcord.VoiceChannel = SlashOption(required=False, description="The channel to play athaan in. If not provided, the bot will create a new channel.")):

        if await self.database.is_server_registered(interaction.guild.id):
            await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="Your server is already registered!", color=nextcord.Color.red()), ephemeral=True)
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
                # Add tMuslim as a user to the channel
            await channel.set_permissions(interaction.guild.me, read_messages=True, send_messages=True)

            if not reaction_roles:
                if not category:
                    category = await interaction.guild.create_category("🕌tMuslim")
                # If no channel is provided, create a new one called "tMuslim Notifications"
                reaction_roles = await interaction.guild.create_text_channel(name="🕌tMuslim Reaction Roles", category=category, topic="Channel for prayer reaction roles")
            await reaction_roles.set_permissions(interaction.guild.me, read_messages=True, send_messages=True)
            await reaction_roles.set_permissions(interaction.guild.me, read_messages=True, send_messages=True)
            if not athaan_channel:
                if not category:
                    category = await interaction.guild.create_category("🕌tMuslim")
                # Make a new channel called "tMuslim Athaan"
                # Only people with "role" should be able to see the channel
                athaan_channel = await interaction.guild.create_voice_channel(name="🕌tMuslim Athaan", category=category, overwrites={interaction.guild.default_role: nextcord.PermissionOverwrite(connect=False), role: nextcord.PermissionOverwrite(connect=True)})
            await athaan_channel.set_permissions(interaction.guild.me, connect=True, speak=True)
            message = await reaction_roles.send(embed=nextcord.Embed(title="Prayer Times", description="React to this message to get pinged for prayer times", color=nextcord.Color.green()))
            
            default_settings = json.load(open("default_settings.json"))
            default_settings["role"] = role.id
            default_settings["channel"] = channel.id
            default_settings["athaanchannel"] = athaan_channel.id
            default_settings["reaction_role_message"] = message.id
            default_settings["city"] = city
            default_settings["country"] = country
            default_settings["timezone"] = time_zone
            
            await self.database.register_server(interaction.guild.id, default_settings)

            await message.add_reaction("🕌")
            # Finally, add the athan loop
            self.athan_loops[interaction.guild.id] = self.bot.loop.create_task(self.prayers.athan(interaction.guild.id))
            await interaction.followup.send(embed=nextcord.Embed(title="🕌 Setup Complete", description="Setup complete! tMuslim's feature are now active in this server", color=nextcord.Color.green()))
        except Exception as e:
            print(e)
            await interaction.followup.send(embed=nextcord.Embed(title="Error", description="An error occurred. Please check your city/country spelling and try again. If this problem persists, contact `TechMaster04#5002`. In the meantime, try a more common city/country in your timezone", color=nextcord.Color.red()))

    # reaction roles
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: nextcord.RawReactionActionEvent):
        # check if the server is registered
        if not await self.database.is_server_registered(payload.guild_id):
            return
        #check if it's the bot
        if payload.user_id == self.bot.user.id:
            return
        if payload.message_id != await self.database.get_reaction_message_id(payload.guild_id):
            return
        if payload.emoji.name == "🕌":
            guild = self.bot.get_guild(payload.guild_id)
            await payload.member.add_roles(nextcord.Object(id=await self.database.get_athaan_role(payload.guild_id)))
            await payload.member.send(embed=nextcord.Embed(title="🕌 Prayer Times", description=f"You have subscribed to tMuslim notifications in {guild.name}", color=nextcord.Color.green()))
    
    # If the user removes the reaction, remove the role
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: nextcord.RawReactionActionEvent):
        if not await self.database.is_server_registered(payload.guild_id):
            return
        if payload.message_id != await self.database.get_reaction_message_id(payload.guild_id):
            return
        if payload.emoji.name == "🕌":
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            await member.remove_roles(nextcord.Object(id=await self.database.get_athaan_role(payload.guild_id)))
            await member.send(embed=nextcord.Embed(title="🕌 Prayer Times", description=f"You have unsubscribed from tMuslim notifications in {guild.name}", color=nextcord.Color.green()))
    
    @settings.subcommand(name="time", description="Set your preffered time format (12/24 hour)")
    async def toggletime(self, interaction: nextcord.Interaction, value: str = SlashOption(required=True, description="The value to set", choices=["12-Hour Time", "24-Hour Time"])):
        value = value == "24-Hour Time"
        if not await self.database.is_server_registered(interaction.guild.id):
            await interaction.response.send_message(embed=nextcord.Embed(title="Error", description="Your server is not registered!", color=nextcord.Color.red()), ephemeral=True)
            return
        await interaction.response.defer()
        await self.database.toggle_24hrtime(interaction.guild.id, value)
        if value:
            await interaction.followup.send(embed=nextcord.Embed(title="24 Hour Time", description=f"24 Hour Time has been enabled", color=nextcord.Color.green()))
            return
        await interaction.followup.send(embed=nextcord.Embed(title="12 Hour Time", description=f"12 Hour Time has been enabled", color=nextcord.Color.green()))
