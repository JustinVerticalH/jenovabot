from ioutils import read_json, write_json
import discord, datetime
from discord.ext import commands, tasks
from discord.utils import format_dt


class EventAlerts(commands.Cog, name="Event Alerts"):
    """Send a timestamped ping message whenever an event is created for a particular role."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.yet_to_ping: set[discord.ScheduledEvent] = set()
        self.wait_until_announcement_tasks: dict[discord.ScheduledEvent, tasks.Loop] = {}
    
    async def initialize(self):
        for guild in self.bot.guilds:
            for event in await guild.fetch_scheduled_events():
                if event.status == discord.EventStatus.scheduled:
                    await self.create_wait_until_announcement_task(event)
                    self.yet_to_ping.add(event)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.initialize()

    @commands.Cog.listener()
    async def on_guild_join(self):
        await self.initialize()

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        """Send a ping message when an event tied to a role is created."""

        await self.send_event_start_time_message(event)

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
        if before.status != after.status and after.status != discord.EventStatus.scheduled:
            self.cancel_wait_until_announcement_task(before)
        elif before.start_time != after.start_time:
            await self.send_event_start_time_message(after, rescheduling=True)
    
    async def send_event_start_time_message(self, event: discord.ScheduledEvent, *, rescheduling: bool = False):
        role = EventAlerts.get_role_from_event(event)
        if role is None:
            return
        
        channel = await event.guild.fetch_channel(read_json(event.guild.id, "scheduled_event_alert_channel_id"))
        if isinstance(channel, discord.ForumChannel):
            channel = EventAlerts.get_channel_from_role(channel, role)
        await channel.send(f"{event.name} {'has been rescheduled to' if rescheduling else 'is set for'} {format_dt(event.start_time, style='F')}! {role.mention}\n{event.url}")

        await self.create_wait_until_announcement_task(event)
        self.yet_to_ping.add(event)
    
    async def create_wait_until_announcement_task(self, event: discord.ScheduledEvent):
        event = await event.guild.fetch_scheduled_event(event.id)
        if event in self.wait_until_announcement_tasks:
            self.cancel_wait_until_announcement_task(event)

        @tasks.loop(time=(event.start_time - datetime.timedelta(minutes=30)).timetz())
        async def wait_until_announcement():
            if datetime.datetime.now(event.start_time.tzinfo).date() == event.start_time.date():
                event_creator = await event.guild.fetch_member(event.creator.id)
                if isinstance(event_creator, discord.Member) and event_creator.voice is not None:
                    await self.send_event_is_starting_message(event)
                    self.cancel_wait_until_announcement_task(event)
        
        self.wait_until_announcement_tasks[event] = wait_until_announcement
        self.wait_until_announcement_tasks[event].start()
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if not (before.channel is None and after.channel is not None): # Member has joined a voice channel
            return
        
        for event in self.yet_to_ping.copy():
            event = await event.guild.fetch_scheduled_event(event.id)
            event_creator = await EventAlerts.get_event_creator(event)
            if event_creator.id == member.id:
                await self.send_event_is_starting_message(event)
    
    async def send_event_is_starting_message(self, event: discord.ScheduledEvent):
        role = EventAlerts.get_role_from_event(event)
        time_until_event_start = event.start_time - datetime.datetime.now(event.start_time.tzinfo)
        
        if time_until_event_start <= datetime.timedelta(minutes=30):
            channel = await event.guild.fetch_channel(read_json(event.guild.id, "scheduled_event_alert_channel_id"))
            # If the server has its event alerts channel set to a forum, then the forum should have a thread with a name matching the role
            if isinstance(channel, discord.ForumChannel):
                channel = EventAlerts.get_channel_from_role(channel, role)
            await channel.send(f"{event.name} is starting {format_dt(event.start_time, style='R')}! {role.mention}\n{event.url}")
            self.yet_to_ping.remove(event)
    
    def cancel_wait_until_announcement_task(self, event: discord.ScheduledEvent):
        if event in self.wait_until_announcement_tasks:
            self.wait_until_announcement_tasks[event].cancel()
            del self.wait_until_announcement_tasks[event]

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def alertchannel(self, context: commands.Context, channel: discord.TextChannel | discord.ForumChannel):
        """Set which channel to send event alert ping messages."""

        write_json(context.guild.id, "scheduled_event_alert_channel_id", value=channel.id)
        await context.send(f"Event alert channel is set to {channel.mention}")
    
    @alertchannel.error
    async def permissions_or_channel_fail(self, context: commands.Context, error: commands.errors.CommandError):
        if isinstance(error, commands.errors.MissingPermissions):
            await context.send("User needs Manage Server permission to use this command.")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await context.send("Channel not found. Try again.")

    @staticmethod
    async def get_event_creator(event: discord.ScheduledEvent):
        fetched_event = await event.guild.fetch_scheduled_event(event.id)
        return await fetched_event.guild.fetch_member(fetched_event.creator.id)

    @staticmethod
    def get_role_from_event(event: discord.ScheduledEvent) -> discord.Role:
        # For some reason, event.guild.roles iterates through the roles from the bottom of the list to the top.
        # We want to look through the roles list starting from the top (i.e. starting from "Witch of Storycasting"),
        # so we reverse the event.guild.roles iterator here to do so.
        
        for role in reversed(event.guild.roles):
            if EventAlerts.matches_role(role, event=event):                
                return role
        return None

    @staticmethod
    def get_channel_from_role(channel: discord.TextChannel | discord.ForumChannel, role: discord.Role) -> discord.TextChannel | discord.Thread:
        if isinstance(channel, discord.ForumChannel):
            for thread in channel.threads:
                if EventAlerts.matches_role(role, channel=thread):
                    return thread
        else:
            if EventAlerts.matches_role(role, channel=channel):
                return channel
        return None

    @staticmethod
    def matches_role(role: discord.Role, event: discord.ScheduledEvent = None, channel: discord.TextChannel | discord.Thread = None) -> bool:
        if " ping" not in role.name.lower():
            return False
        
        if channel is not None:
            string_to_check = channel.name
        elif event is not None:
            string_to_check = event.name + event.description
        else:
            return False
        
        return role.name.lower().replace(" ping", "") in string_to_check.lower()