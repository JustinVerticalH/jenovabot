import datetime, json, re
from dataclasses import dataclass
from ioutils import read_sql, write_sql

import discord
from discord.ext import commands, tasks


@dataclass(frozen=True)
class Reminder:
    """A container for data associated with a scheduled reminder."""

    command_message: discord.Message
    reminder_datetime: datetime.datetime
    reminder_str: str

    def __str__(self):
        return f"Reminder in {self.command_message.channel.mention} by {self.command_message.author.name} for <t:{int(self.reminder_datetime.timestamp())}>: {self.reminder_str!r}"

    def to_json(self) -> str:
        """A method for converting the current reminder object to a JSON string."""

        json_obj = {
            "channel_id": self.command_message.channel.id,
            "command_message_id": self.command_message.id,
            "reminder_timestamp": self.reminder_datetime.timestamp(),
            "reminder_str": self.reminder_str
        }
        return json.dumps(json_obj)

    @staticmethod
    async def from_json(bot: commands.Bot, json_obj: dict[str, int | float | str]):
        """A static method for converting a JSON dictionary to a Reminder object."""

        channel = bot.get_channel(json_obj["channel_id"])

        command_message = await channel.fetch_message(json_obj["command_message_id"])
        reminder_datetime = datetime.datetime.fromtimestamp(json_obj["reminder_timestamp"])
        reminder_str = json_obj["reminder_str"]

        return Reminder(command_message, reminder_datetime, reminder_str)

class Reminders(commands.Cog, name="Reminders"):
    """A Cog to handle creating and sending scheduled reminder messages."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminders: dict[int, set[Reminder]] = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        """A listener for initializing the reminders instance dictionary from SQL data and starting the reminder processing loop."""

        for guild in self.bot.guilds:
            if read_sql("test_reminders", guild.id, "reminders") is None:
                write_sql("test_reminders", guild.id, "reminders", "array[[]]::json[]")
            self.reminders[guild.id] = {await Reminder.from_json(self.bot, json_str) for json_str in read_sql("test_reminders", guild.id, "reminders")}
        self.process_reminders.start()
 
    @commands.group(aliases=["remindme", "rm"], invoke_without_command=True)
    async def remind(self, context: commands.Context, time: str, *, reminder_str: str = ""):
        """A command for setting a scheduled reminder for the given user. May also be used to view or cancel existing reminders."""

        # Determine the amount of time based on the time inputted
        num_days, num_hours, num_minutes, num_seconds, is_valid = Reminders.get_datetime_parameters(time)
        if not is_valid:
            time_string_guess = re.sub("0.", "", f"{num_days}d{num_hours}h{num_minutes}m{num_seconds}s")
            if time_string_guess == "":
                await context.send(f"Time string is not formatted correctly; not sure what you meant to type here.")
            else:
                await context.send(f"Time string is not formatted correctly; did you mean to type {time_string_guess}?")
            return
        reminder_datetime = datetime.datetime.now() + datetime.timedelta(days = num_days, hours = num_hours, minutes = num_minutes, seconds = num_seconds)

        reminder = Reminder(context.message, reminder_datetime, reminder_str)
        if context.guild.id not in self.reminders:
            self.reminders[context.guild.id] = set()
        self.reminders[context.guild.id].add(reminder)
        write_sql("test_reminders", context.guild.id, "reminders", f"array{[reminder.to_json() for reminder in self.reminders[context.guild.id]]}::json[]")
        await context.message.add_reaction("👍")
    
    @staticmethod
    def get_datetime_parameters(time: str):
        """A helper method for converting a time string into parameters for a datetime object."""

        is_valid = True

        timer_parameters = re.fullmatch("(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time)
        if timer_parameters is None:
            timer_parameters = re.search("(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time)
            is_valid = False
        
        return (*tuple(map(lambda t: int(0 if t is None else t), timer_parameters.groups())), is_valid)

    @remind.command()
    async def viewall(self, context: commands.Context):
        if len(self.reminders[context.guild.id]) == 0:
            await context.send("No reminders currently set.")
            return

        reminder_list = discord.Embed()
        for i, reminder in enumerate(self.reminders[context.guild.id]):
            reminder_list.add_field(name=f"{i+1}.", value=reminder, inline=False)
        await context.send(embed=reminder_list)

    @remind.command()
    async def cancel(self, context: commands.Context):
        pass
        #TODO: This function
    
    @tasks.loop(seconds=0.1)
    async def process_reminders(self):
        """A task loop for sending any reminders past their scheduled date and syncing with the SQL database when appropriate."""

        for guild in self.bot.guilds:
            reminders = self.reminders[guild.id].copy()
            for reminder in reminders:
                if reminder.reminder_datetime <= datetime.datetime.now():
                    await reminder.command_message.reply(reminder.reminder_str)
                    self.reminders[guild.id].remove(reminder)
            if reminders != self.reminders[guild.id]:
                write_sql("test_reminders", guild.id, "reminders", f"array{[reminder.to_json() for reminder in self.reminders[guild.id]]}::json[]")