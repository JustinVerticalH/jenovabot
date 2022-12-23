import datetime, re
from dataclasses import dataclass, field
from ioutils import RandomColorEmbed, read_json, write_json

import discord
from discord.ext import commands, tasks
from discord.utils import format_dt


@dataclass(frozen=True, order=True)
class Reminder:
    """Data associated with a scheduled reminder."""

    command_message: discord.Message = field(compare=False)
    reminder_datetime: datetime.datetime
    reminder_str: str = field(compare=False)

    def __str__(self):
        return f"{self.command_message.author.mention} - {self.command_message.channel.mention} @ {format_dt(self.reminder_datetime, style='F')}: {self.reminder_str!r}"

    def __repr__(self):
        out = f"{self.command_message.author.name} - #{self.command_message.channel.name} @ {self.reminder_datetime:%a %b %d, %I:%M %p}: {self.reminder_str!r}"
        if len(out) > 100:
            out = out[:97] + "..."
        return out

    def to_json(self) -> dict[str, int | float | str]:
        """Convert the current reminder object to a JSON string."""

        return {
            "channel_id": self.command_message.channel.id,
            "command_message_id": self.command_message.id,
            "reminder_timestamp": self.reminder_datetime.timestamp(),
            "reminder_str": self.reminder_str
        }

    @staticmethod
    async def from_json(bot: commands.Bot, json_obj: dict[str, int | float | str]):
        """Convert a JSON dictionary to a Reminder object."""

        channel = bot.get_channel(json_obj["channel_id"])

        command_message = await channel.fetch_message(json_obj["command_message_id"])
        reminder_datetime = datetime.datetime.fromtimestamp(json_obj["reminder_timestamp"])
        reminder_str = json_obj["reminder_str"]

        return Reminder(command_message, reminder_datetime, reminder_str)

class ReminderCancelSelect(discord.ui.Select):
    def __init__(self, context: commands.Context, reminders: set[Reminder]):
        self.bot = context.bot
        self.reminders = reminders

        options = [discord.SelectOption(label=repr(reminder)) for reminder in sorted(reminders)]
        super().__init__(placeholder="Select reminders to cancel...", max_values=len(reminders), options=options)
    
    async def callback(self, interaction: discord.Interaction):
        cancelled_reminders = {reminder for reminder in self.reminders if repr(reminder) in self.values}
        self.bot.get_cog("Reminders").reminders[interaction.guild_id] -= cancelled_reminders

        cancelled_reminder_list = RandomColorEmbed(
            title="Cancelled Reminders",
            description='\n'.join([str(reminder) for reminder in sorted(cancelled_reminders)])
        )
        await interaction.response.send_message(embed=cancelled_reminder_list, ephemeral=True)

class ReminderCancelView(discord.ui.View):
    def __init__(self, context: commands.Context, reminders: set[Reminder]):
        super().__init__()
        self.member = context.author
        self.add_item(ReminderCancelSelect(context, reminders))
    
    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user == self.member

class Reminders(commands.Cog, name="Reminders"):
    """Create and send scheduled reminder messages."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminders: dict[int, set[Reminder]] = {}
        self._cached_reminders: dict[int, set[Reminder]] = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize the reminders instance dictionary from JSON data and start the reminder processing loop."""

        for guild in self.bot.guilds:
            if read_json(guild.id, "reminders") is None:
                write_json(guild.id, "reminders", value={})
            self.reminders[guild.id] = {await Reminder.from_json(self.bot, json_str) for json_str in read_json(guild.id, "reminders")}
            self._cached_reminders[guild.id] = self.reminders[guild.id].copy()
        
        self.send_reminders.start()
        self.sync_json.start()
 
    @commands.group(aliases=["remindme", "rm"], invoke_without_command=True)
    async def remind(self, context: commands.Context, time: str, *, reminder_str: str = ""):
        """Set a scheduled reminder. Format time as: _d_h_m_s (may omit individual parameters)"""
        
        # Determine the amount of time based on the time inputted
        num_days, num_hours, num_minutes, num_seconds, is_valid = Reminders.get_datetime_parameters(time)
        if not is_valid:
            time_string_guess = re.sub("0.", "", f"{num_days}d{num_hours}h{num_minutes}m{num_seconds}s")
            if time_string_guess == "":
                await context.send(f"Time string is not formatted correctly; not sure what you meant to type here.")
            else:
                await context.send(f"Time string is not formatted correctly; did you mean to type {time_string_guess}?")
            return

        timedelta = datetime.timedelta(days=num_days, hours=num_hours, minutes=num_minutes, seconds=num_seconds)
        time = context.message.created_at + timedelta
        await self.create_reminder(context.message, time, reminder_str)
        await context.message.add_reaction("👍")
    
    @remind.command(aliases=["periodic"])
    async def every(self, context: commands.Context, time: str, *, reminder_str: str):
        # Determine the amount of time based on the time inputted
        num_days, num_hours, num_minutes, num_seconds, is_valid = Reminders.get_datetime_parameters(time)
        if not is_valid:
            time_string_guess = re.sub("0.", "", f"{num_days}d{num_hours}h{num_minutes}m{num_seconds}s")
            if time_string_guess == "":
                await context.send(f"Time string is not formatted correctly; not sure what you meant to type here.")
            else:
                await context.send(f"Time string is not formatted correctly; did you mean to type {time_string_guess}?")
            return
        timedelta = datetime.timedelta(days=num_days, hours=num_hours, minutes=num_minutes, seconds=num_seconds)
        time = context.message.created_at + timedelta
        await self.create_reminder(context.message, time, reminder_str)
        await context.message.add_reaction("👍")

    async def create_reminder(self, message: discord.Message, time: datetime.datetime, reminder_str: str):
        "Creates a new reminder and adds it to the list of reminders."

        reminder = Reminder(message, time, reminder_str)
        if message.guild.id not in self.reminders:
            self.reminders[message.guild.id] = set()
        self.reminders[message.guild.id].add(reminder)
        
    @staticmethod
    def get_datetime_parameters(time: str):
        """Convert a time string into parameters for a datetime object."""

        is_valid = True

        timer_parameters = re.fullmatch("(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time)
        if timer_parameters is None:
            timer_parameters = re.search("(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time)
            is_valid = False
        
        return (*tuple(map(lambda t: int(0 if t is None else t), timer_parameters.groups())), is_valid)

    @remind.command()
    async def viewall(self, context: commands.Context):
        """View scheduled reminders of every server member."""
        
        if len(self.reminders[context.guild.id]) == 0:
            await context.send("No reminders currently set.")
            return

        reminder_list = RandomColorEmbed(
            title="Scheduled Reminders",
            description='\n'.join([f"{i+1}. {reminder}" for i, reminder in enumerate(sorted(self.reminders[context.guild.id]))])
        )
        await context.send(embed=reminder_list)

    @remind.command()
    async def cancel(self, context: commands.Context):
        """Cancel scheduled reminders."""
        
        is_viewable = lambda reminder: context.author.guild_permissions.manage_guild or reminder.command_message.author == context.author
        filtered_reminders = {reminder for reminder in self.reminders[context.guild.id] if is_viewable(reminder)}
        
        if len(filtered_reminders) == 0:
            await context.send("No reminders currently set.")
            return

        await context.send(view=ReminderCancelView(context, filtered_reminders))
    
    @tasks.loop(seconds=0.2)
    async def send_reminders(self):
        """Send any reminders past their scheduled date."""

        for guild in self.bot.guilds:
            reminders = self.reminders[guild.id].copy()
            for reminder in reminders:
                if reminder.reminder_datetime.timestamp() <= datetime.datetime.now().timestamp():
                    # Read the list of reactions to the message, and create a string to mention each user (besides the bot) who reacted
                    for reaction in reminder.command_message.reactions:
                        if reaction.emoji == "👍":
                            subscribers = [user async for user in reaction.users()]
                            subscribers_mention = "\n"
                            for user in subscribers:
                                if user != self.bot.user:
                                    subscribers_mention += user.mention + " "

                    await reminder.command_message.reply(f"{reminder.reminder_str} {subscribers_mention}")
                    self.reminders[guild.id].remove(reminder)

                    # If the reminder is periodic, create a new reminder with the same time interval
                    #if reminder.periodic:
                        #timedelta = datetime.datetime.now() - reminder.reminder_datetime
                        #time = datetime.datetime.now() + timedelta
                        #await self.create_reminder(reminder.command_message, time, reminder.reminder_str)
    
    @tasks.loop(seconds=0.3)
    async def sync_json(self):
        """Sync with the JSON file if any changes are detected."""

        for guild in self.bot.guilds:
            if self.reminders[guild.id] != self._cached_reminders[guild.id]:
                write_json(guild.id, "reminders", value=[reminder.to_json() for reminder in self.reminders[guild.id]])
                self._cached_reminders[guild.id] = self.reminders[guild.id].copy()