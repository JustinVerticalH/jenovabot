import discord

from discord import app_commands
from discord.ext import commands
from enum import Enum
from ioutils import write_json


class ChannelType(Enum):
    Announcements = "Announcements"
    Birthdays = "Birthdays"
    DailyMessages = "Daily messages"
    Events = "Events"

CHANNEL_TYPE_TO_DATABASE_STR = {
    ChannelType.Announcements: "periodic_announcement_channel_id",
    ChannelType.Birthdays: "birthday_channel_id",
    ChannelType.DailyMessages: "daily_message_channel_id",
    ChannelType.Events: "scheduled_event_alert_channel_id"
}

class Admin(commands.Cog, name="Administrator"):
    """Save settings for your server."""

    def __init__(self, bot: commands.Bot):
        "Initialize the cog."
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        "Sync the application commands."
        synced = await self.bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    
    @app_commands.command()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel_type: ChannelType, channel: discord.TextChannel | discord.ForumChannel):
        """Set which channel to send certain automated messages (announcements, birthdays, daily messages, events, etc)."""
        if channel_type != ChannelType.Events and isinstance(channel, discord.ForumChannel):
            return await interaction.response.send_message("Forum channels are only possible when setting the Events channel.", ephemeral=True)
        write_json(interaction.guild.id, CHANNEL_TYPE_TO_DATABASE_STR[channel_type], value=channel.id)
        await interaction.response.send_message(f"{channel_type.value} will be sent in {channel.mention}", ephemeral=True)

    @channel.error
    async def permissions_or_channel_fail(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handles errors for the given command (insufficient permissions, etc)."""
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You need the Manage Server permission to use this command.", ephemeral=True)