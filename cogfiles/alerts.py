from ioutils import read_json, write_json
import discord, datetime
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import format_dt


MINUTES_BEFORE_EVENT_START_TIME = 30


class EventAlerts(commands.Cog, name="Event Alerts"):
    """Send a timestamped ping message whenever an event is created for a particular role."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.yet_to_ping: set[discord.ScheduledEvent] = set() # Events that have not yet been pinged, to avoid double pings
        self.wait_until_announcement_tasks: dict[discord.ScheduledEvent, tasks.Loop] = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Initializes the list of events in memory and creates task loops for each announcement not already pinged."""
        for guild in self.bot.guilds:
            for event in await guild.fetch_scheduled_events():
                if event.status == discord.EventStatus.scheduled:
                    await self.create_wait_until_announcement_task(event)
                    self.yet_to_ping.add(event)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initializes the class on server join."""
        await self.on_ready()

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        """Send a ping message when an event tied to a role is created."""
        await self.send_event_start_time_message(event)

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
        """Updates the status of the event in memory when an event tied to a role is updated."""
        if before.status != after.status and after.status != discord.EventStatus.scheduled: # Event is no longer scheduled
            self.cancel_wait_until_announcement_task(before)
            self.yet_to_ping.remove(before)
        elif before.start_time != after.start_time: # Event has been rescheduled
            await self.send_event_start_time_message(after, rescheduling=True)
    
    async def send_event_start_time_message(self, event: discord.ScheduledEvent, *, rescheduling: bool = False):
        """Attempts to send a message about the event start time. 
        Runs whenever an event is created or rescheduled. 
        Does nothing if no matching role is found for this event."""
        role = EventAlerts.get_role_from_event(event)
        if role is None:
            return
        
        channel = await event.guild.fetch_channel(read_json(event.guild.id, "scheduled_event_alert_channel_id"))
        # If the server has its event alerts channel set to a forum, then the forum should have a thread with a name matching the role
        if isinstance(channel, discord.ForumChannel):
            channel = EventAlerts.get_channel_from_role(channel, role)
        await channel.send(f"{event.name} {'has been rescheduled to' if rescheduling else 'is set for'} {format_dt(event.start_time, style='F')}! {role.mention}\n{event.url}")

        await self.create_wait_until_announcement_task(event)
        self.yet_to_ping.add(event)
    
    async def create_wait_until_announcement_task(self, event: discord.ScheduledEvent):
        """Creates a task loop that completes when the event creator joins a voice channel 30 minutes or less before the event start time."""
        event = await event.guild.fetch_scheduled_event(event.id)
        if event in self.wait_until_announcement_tasks:
            self.cancel_wait_until_announcement_task(event)

        @tasks.loop(time=(event.start_time - datetime.timedelta(minutes=MINUTES_BEFORE_EVENT_START_TIME)).timetz())
        async def wait_until_announcement():
            """Loops until the event creator joins a voice channel, then sends a starting message."""  
            if datetime.datetime.now(event.start_time.tzinfo).date() == event.start_time.date():
                event_creator = await event.guild.fetch_member(event.creator.id)
                if isinstance(event_creator, discord.Member) and event_creator.voice is not None:
                    await self.send_event_is_starting_message(event)
                    self.cancel_wait_until_announcement_task(event)
        
        self.wait_until_announcement_tasks[event] = wait_until_announcement
        self.wait_until_announcement_tasks[event].start()
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Sends an event starting message when an event creator joins a voice channel 30 minutes or less before the event start time."""
        if (before.channel is None and after.channel is not None): # If member has not joined a voice channel
            return
        
        for event in self.yet_to_ping.copy():
            event = await event.guild.fetch_scheduled_event(event.id)
            event_creator = await EventAlerts.get_event_creator(event)
            if event_creator.id == member.id:
                await self.send_event_is_starting_message(event)
    
    async def send_event_is_starting_message(self, event: discord.ScheduledEvent):
        """Attempts to send a message that the event is starting. 
        Does nothing if the event start time is more than 30 minutes away."""
        role = EventAlerts.get_role_from_event(event)
        time_until_event_start = event.start_time - datetime.datetime.now(event.start_time.tzinfo)
        
        if time_until_event_start <= datetime.timedelta(minutes=MINUTES_BEFORE_EVENT_START_TIME):
            channel = await event.guild.fetch_channel(read_json(event.guild.id, "scheduled_event_alert_channel_id"))
            # If the server has its event alerts channel set to a forum, then the forum should have a thread with a name matching the role
            if isinstance(channel, discord.ForumChannel):
                channel = EventAlerts.get_channel_from_role(channel, role)
            await channel.send(f"{event.name} is starting {format_dt(event.start_time, style='R')}! {role.mention}\n{event.url}")
            self.yet_to_ping.remove(event)
    
    def cancel_wait_until_announcement_task(self, event: discord.ScheduledEvent):
        """Stop the task loop that would send an announcement for this event and clear the event from memory."""
        if event in self.wait_until_announcement_tasks:
            self.wait_until_announcement_tasks[event].cancel()
            del self.wait_until_announcement_tasks[event]

    @app_commands.command()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def alertchannel(self, interaction: discord.Interaction, channel: discord.TextChannel | discord.ForumChannel):
        """Set which channel to send event alert ping messages."""
        write_json(interaction.guild.id, "scheduled_event_alert_channel_id", value=channel.id)
        await interaction.response.send_message(f"Event alert channel is set to {channel.mention}", ephemeral=True)
    
    @alertchannel.error
    async def permissions_or_channel_fail(self, context: commands.Context, error: commands.errors.CommandError):
        """Handles errors for the given command (insufficient permissions, etc)."""
        if isinstance(error, commands.errors.MissingPermissions):
            await context.send("User needs Manage Server permission to use this command.")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await context.send("Channel not found. Try again.")

    @staticmethod
    async def get_event_creator(event: discord.ScheduledEvent):
        """Returns the creator of the given event."""
        fetched_event = await event.guild.fetch_scheduled_event(event.id)
        return await fetched_event.guild.fetch_member(fetched_event.creator.id)

    @staticmethod
    def get_role_from_event(event: discord.ScheduledEvent) -> discord.Role:
        """Returns the role that should be pinged for a given event. Returns None if no role found."""
        # For some reason, event.guild.roles iterates through the roles from the bottom of the list to the top.
        # We want to look through the roles list starting from the top (i.e. starting from "Witch of Storycasting"),
        # so we reverse the event.guild.roles iterator here to do so.
        for role in reversed(event.guild.roles):
            if EventAlerts.matches_role(role, event=event):                
                return role
        return None

    @staticmethod
    def get_channel_from_role(channel: discord.TextChannel | discord.ForumChannel, role: discord.Role) -> discord.TextChannel | discord.Thread:
        """Returns the channel/thread that matches the given role.  
        If a forum channel is given, this function checks every thread inside of the forum. 
        Returns None if no channel/thread found."""
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
        """Determines if an event or channel matches a given role, by checking if the role's name minus the word "Ping" is contained in the event/channel."""
        if " ping" not in role.name.lower():
            return False
        
        if channel is not None:
            string_to_check = channel.name
        elif event is not None:
            string_to_check = event.name + event.description
        else:
            return False
        
        return role.name.lower().replace(" ping", "") in string_to_check.lower()