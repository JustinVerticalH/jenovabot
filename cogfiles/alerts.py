from ioutils import read_sql, write_sql

import discord
from discord.ext import commands


class EventAlerts(commands.Cog, name="Event Alerts"):
    """Send a timestamped ping message whenever an event is created for a particular role."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        """Send a ping message when an event tied to a role is created."""

        for role in event.guild.roles:
            if role.name.replace(" Ping", "") in event.name:
                channel = await event.guild.fetch_channel(read_sql("test_settings", event.guild.id, "scheduled_event_alert_channel_id"))
                start_time = int(event.start_time.timestamp())
                await channel.send(f"{event.name} is set for <t:{start_time}>! {role.mention}")
    
    @commands.command()
    async def alerts(self, context: commands.Context, channel: discord.TextChannel):
        """Set which channel to send event alert ping messages."""

        if not context.author.guild_permissions.manage_guild:
            await context.send("User needs Manage Server permission to use this command.")
            return
        
        write_sql("test_settings", context.guild.id, "scheduled_event_alert_channel_id", channel.id)
        await context.send(f"Event alert channel is set to {channel.mention}")
    
    @alerts.error
    async def channel_not_found(self, context: commands.Context, error):
        if isinstance(error, commands.errors.ChannelNotFound):
            await context.send("Channel not found. Try again.")