from ioutils import read_sql, write_sql

import discord, datetime
from discord.ext import commands


class EventAlerts(commands.Cog, name="Event Alerts"):
    """Send a timestamped ping message whenever an event is created for a particular role."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.already_pinged_events = []

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        """Send a ping message when an event tied to a role is created."""

        for role in event.guild.roles:
            if role.name.replace(" Ping", "") in event.name:
                channel = await event.guild.fetch_channel(read_sql("test_settings", event.guild.id, "scheduled_event_alert_channel_id"))
                start_time = int(event.start_time.timestamp())
                await channel.send(f"{event.name} is set for <t:{start_time}>! {role.mention}")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel is None and after.channel is not None: # Member has joined a voice channel
            events = await member.guild.fetch_scheduled_events()
            for event in events:
                if event.id not in self.already_pinged_events:
                    if event.creator.id == member.id:
                        role = EventAlerts.get_role_from_event(event)
                        time_until_event_start = event.start_time - datetime.datetime.now().astimezone(event.start_time.tzinfo)
                        if time_until_event_start <= datetime.timedelta(minutes = 30):
                            channel = await event.guild.fetch_channel(read_sql("test_settings", event.guild.id, "scheduled_event_alert_channel_id"))
                            await channel.send(f"{event.name} is starting soon! {role.mention}")
                            self.already_pinged_events.append(event.id)

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
        if before.status == discord.EventStatus.active and after.status == discord.EventStatus.completed: # Event has just finished
            self.already_pinged_events.remove(before.id)

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def alerts(self, context: commands.Context, channel: discord.TextChannel):
        """Set which channel to send event alert ping messages."""

        write_sql("test_settings", context.guild.id, "scheduled_event_alert_channel_id", channel.id)
        await context.send(f"Event alert channel is set to {channel.mention}")
    
    @alerts.error
    async def permissions_or_channel_fail(self, context: commands.Context, error: commands.errors.CommandError):
        if isinstance(error, commands.errors.MissingPermissions):
            await context.send("User needs Manage Server permission to use this command.")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await context.send("Channel not found. Try again.")

    @staticmethod
    def get_role_from_event(event: discord.ScheduledEvent) -> discord.Role:
        for role in event.guild.roles:
            if "Ping" in role.name and role.name.replace(" Ping", "") in event.name:
                return role
        return None