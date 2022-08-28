import datetime, os, pytz, re
import json
from dataclasses import dataclass
from dotenv import load_dotenv
from ioutils import read_file, read_sql, write_sql
from typing import Optional

import discord
from discord.ext import commands, tasks


load_dotenv()
token = os.getenv("TOKEN")

command_prefix = os.getenv("PREFIX")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!" if command_prefix is None else command_prefix, intents=intents)

class Copypastas(commands.Cog, name="Message Copypastas"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == bot.user:
            return
        copypastas = read_file("copypastas.json")
        for phrase in copypastas:
            if phrase in message.content.lower():
                await message.channel.send(copypastas[phrase])


class EventAlerts(commands.Cog, name="Event Alerts"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        for role in event.guild.roles:
            if role.name.replace(" Ping", "") in event.name:
                channel = await event.guild.fetch_channel(read_sql("settings", event.guild.id, "scheduled_event_alert_channel_id"))
                start_time = int(event.start_time.timestamp())
                await channel.send(f"{event.name} is set for <t:{start_time}>! {role.mention}")

    @commands.command()
    async def alerts(self, context: commands.Context, argument: str):
        if context.message.author.guild_permissions.manage_guild:
            for channel in context.guild.channels:
                if argument in [channel.name, channel.mention]:
                    #write("settings.json", channel.id, context.guild.id, "scheduled_event_alert_channel_id")
                    write_sql("settings", context.guild.id, "scheduled_event_alert_channel_id", channel.id)
                    await context.send(f"Event alert channel is set to {channel.mention}")
                    return
            await context.send("Channel not found. Try again.")
            return
        await context.send("User needs Manage Server permission to use this command.")
        return


class StreamPause(commands.Cog, name="Stream Pause"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.streampause_data: dict[str, discord.Message | discord.Member] = None
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        if self.streampause_data is not None:
            await self.attempt_to_finish_streampause(reaction, user, user.voice.channel if user.voice else None)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if self.streampause_data is not None:
            voice_channel = before.channel if after.channel is None else after.channel if before.channel is None else None
            reaction = discord.utils.get(self.streampause_data["message"].reactions, emoji="👍")

            await self.attempt_to_finish_streampause(reaction, member, voice_channel)

    @commands.command()
    async def streampause(self, context: commands.Context):
        if context.author.voice is None:
            await context.send("This command is only usable inside a voice channel.")
            return

        message = await context.send("React with 👍 when you're all set!")

        self.streampause_data = {
            "message": message,
            "author": context.author
        }

        await message.add_reaction("👍")

    async def attempt_to_finish_streampause(self, reaction: discord.Reaction, user: discord.Member, voice_channel: Optional[discord.VoiceChannel]):
        if user.bot or reaction.message != self.streampause_data["message"] or reaction.emoji != "👍" or voice_channel is None:
            return

        reacted_members = set(await reaction.users().flatten())
        vc_members = set(voice_channel.members)

        if reacted_members & vc_members == vc_members:
            original_author = self.streampause_data["author"]
            await reaction.message.channel.send(f"{original_author.mention} Everyone's here!")

            await reaction.message.delete()
            self.streampause_data = None


@dataclass(frozen=True)
class Reminder:
    command_message: discord.Message
    reminder_datetime: datetime.datetime
    reminder_str: str

    def to_json(self) -> str:
        json_obj = {
            "channel_id": self.command_message.channel.id,
            "command_message_id": self.command_message.id,
            "reminder_timestamp": self.reminder_datetime.timestamp(),
            "reminder_str": self.reminder_str
        }
        return json.dumps(json_obj)

    @staticmethod
    async def from_json(bot: commands.Bot, json_obj: dict[str, int | float | str]):
        channel = bot.get_channel(json_obj["channel_id"])

        command_message = await channel.fetch_message(json_obj["command_message_id"])
        reminder_datetime = datetime.datetime.fromtimestamp(json_obj["reminder_timestamp"])
        reminder_str = json_obj["reminder_str"]

        return Reminder(command_message, reminder_datetime, reminder_str)


class Reminders(commands.Cog, name="Reminders"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminders: dict[int, set[Reminder]] = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            if read_sql("reminders", guild.id, "reminders") is None:
                write_sql("reminders", guild.id, "reminders", None)
            self.reminders[guild.id] = {await Reminder.from_json(self.bot, json_str) for json_str in read_sql("reminders", guild.id, "reminders")}
        self.process_reminders.start()
 
    @commands.command()
    async def remindme(self, context: commands.Context, time: str, reminder_str: str = ""):
 
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
        
        await context.message.add_reaction("👍")

    @staticmethod
    def get_datetime_parameters(time: str):
        is_valid = True

        timer_parameters = re.fullmatch("(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time)
        if timer_parameters is None:
            timer_parameters = re.search("(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time)
            is_valid = False
        
        return (*tuple(map(lambda t: int(0 if t is None else t), timer_parameters.groups())), is_valid)

    
    @tasks.loop(seconds=0.1)
    async def process_reminders(self):
        for guild in self.bot.guilds:
            for reminder in self.reminders[guild.id].copy():
                if reminder.reminder_datetime <= datetime.datetime.now():
                    await reminder.command_message.reply(reminder.reminder_str)
                    self.reminders[guild.id].remove(reminder)
            write_sql("reminders", guild.id, "reminders", f"array{[reminder.to_json() for reminder in self.reminders[guild.id]]}::json[]")


class Announcements(commands.Cog, name="Periodic Announcements"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.periodic_announcements.start()

    @commands.command()
    async def announcements(self, context: commands.Context, argument: str):
        if context.message.author.guild_permissions.manage_guild:
            for channel in context.guild.channels:
                if argument in [channel.name, channel.mention]:
                    write_sql("settings", context.guild.id, "periodic_announcement_channel_id", channel.id)
                    await context.send(f"Periodic announcement channel is set to {channel.mention}")
                    return
            await context.send("Channel not found. Try again.")
            return
        await context.send("User needs Manage Server permission to use this command.")
        return

    @tasks.loop(minutes=0.2)
    async def periodic_announcements(self):
        now = datetime.datetime.now(pytz.timezone("US/Eastern"))
        for guild in self.bot.guilds:
            channel_id = read_sql("settings", guild.id, "periodic_announcement_channel_id")
            if channel_id is not None:
                channel = bot.get_channel(channel_id)
                if now.weekday() == 4 and now.hour == 17 and now.minute == 0 and now.second < 12: # Friday, 5:00 PM EST
                    await channel.send(file = discord.File("ninja_troll.png"))
                if now.day == 1 and now.hour == 0 and now.minute == 0 and now.second < 12: # 1st day of the month, 12:00 AM EST
                    await channel.send(file = discord.File("first_of_the_month.mov"))


cogs = Copypastas(bot), EventAlerts(bot), StreamPause(bot), Reminders(bot), Announcements(bot)
for cog in cogs:
    bot.add_cog(cog)

bot.run(token)
