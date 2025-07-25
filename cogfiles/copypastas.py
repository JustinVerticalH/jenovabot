import discord
import json

from discord import app_commands
from discord.ext import commands
from ioutils import read_json, write_json


class Copypastas(commands.Cog, name="Message Copypastas"):
    """Send a copypasta whenever a key phrase is found in a message."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.is_copypasta_enabled: dict[int, bool] = {} # Whether or not copypastas are enabled for each server
        with open("copypastas.json", "r") as file:
            self.copypastas = json.load(file)
    
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            self.is_copypasta_enabled[guild.id] = read_json(guild.id, "copypasta") or False

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initialize copypasta settings when the bot joins a new server."""
        await self.on_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detect key phrases in messages."""
        # The bot shouldn't respond to its own copypastas
        if message.author == self.bot.user:
            return
        if not self.is_copypasta_enabled[message.guild.id]:
            return
        for phrase in self.copypastas:
            if phrase in message.content.lower():
                await message.channel.send(self.copypastas[phrase])

    @app_commands.command()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def togglecopypastas(self, interaction: discord.Interaction, toggle: bool):
        """Toggle whether the bot will send a copypasta when a message contains a certain phrase."""
        self.is_copypasta_enabled[interaction.guild.id] = toggle
        write_json(interaction.guild.id, "copypasta", value=toggle)
        await interaction.response.send_message(f"Copypastas in this server are now {'on' if toggle else 'off'}.", ephemeral=True)

    @togglecopypastas.error
    async def permissions_or_channel_fail(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handles errors for the given command (insufficient permissions, etc)."""
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You need the Manage Server permission to use this command.", ephemeral=True)