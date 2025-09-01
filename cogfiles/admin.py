import discord

from discord import app_commands
from discord.ext import commands
from enum import Enum
from ioutils import read_json, write_json


class ChannelType(Enum):
    Announcements = "Announcements"
    Birthdays = "Birthdays"
    DailyMessages = "Daily messages"
    Events = "Events"
    NewThreads = "New thread announcements"

CHANNEL_TYPE_TO_DATABASE_STR = {
    ChannelType.Announcements: "periodic_announcement_channel_id",
    ChannelType.Birthdays: "birthday_channel_id",
    ChannelType.DailyMessages: "daily_message_channel_id",
    ChannelType.Events: "scheduled_event_alert_channel_id",
    ChannelType.NewThreads: "new_threads_channel_id"
}

class Admin(commands.Cog, name="Administrator"):
    """Save settings for your server."""

    def __init__(self, bot: commands.Bot):
        "Initialize the cog."
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        "Sync the application commands."
        try:
            synced = await self.bot.tree.sync()
        except discord.DiscordException as error:
            print(f"Failed to sync command(s): {error}")
        else:
            print(f"Synced {len(synced)} command(s).")
    
    @commands.Cog.listener()
    async def on_command_error(self, context: commands.Context, error: commands.CommandError):
        "Inform the user of slash commands if attempting to use an old-style command."
        if isinstance(error, commands.CommandNotFound) and self.bot.tree.get_command(context.invoked_with) is not None:
            await context.send(f"Looks like you just tried to use the `{context.invoked_with}` command.\nJENOVA has moved over to slash commands — be sure to type `/{context.invoked_with}` instead.")
    
    @app_commands.command()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def sync(self, interaction: discord.Interaction):
        "Sync the application commands."
        try:
            synced = await self.bot.tree.sync()
        except discord.DiscordException as error:
            await interaction.response.send_message(f"Failed to sync command(s): {error}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Synced {len(synced)} command(s).", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel_type: ChannelType, channel: discord.TextChannel | discord.ForumChannel):
        """Set which channel to send certain automated messages (announcements, birthdays, daily messages, events, new threads, etc)."""
        if channel_type != ChannelType.Events and isinstance(channel, discord.ForumChannel):
            return await interaction.response.send_message("Forum channels are only possible when setting the Events channel.", ephemeral=True)
        write_json(interaction.guild.id, CHANNEL_TYPE_TO_DATABASE_STR[channel_type], value=channel.id)
        await interaction.response.send_message(f"{channel_type.value} will be sent in {channel.mention}", ephemeral=True)

    @channel.error
    async def permissions_or_channel_fail(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handles errors for the given command (insufficient permissions, etc)."""
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You need the Manage Server permission to use this command.", ephemeral=True)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        """Sends a message informing users of a new thread."""
        if not isinstance(thread.parent, discord.ForumChannel) or thread.is_private():
            return

        new_thread_channel_id = read_json(thread.guild.id, "new_threads_channel_id")
        if new_thread_channel_id is None:
            return

        new_thread_channel = await self.bot.fetch_channel(new_thread_channel_id)
        await new_thread_channel.send(f"{thread.owner.mention} has created a new thread in {thread.parent.mention}: {thread.mention}")