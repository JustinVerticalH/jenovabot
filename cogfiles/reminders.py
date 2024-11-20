import datetime, json, re
from dataclasses import dataclass, field
from ioutils import RandomColorEmbed, read_json, write_json

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import format_dt


@dataclass(frozen=True, order=True)
class Reminder:
    """Data associated with a scheduled reminder."""
    author: discord.User = field(compare=False)
    channel: discord.TextChannel | discord.ForumChannel = field(compare=False)
    command_message: discord.Message = field(compare=False) # This will be None when the reminder is created via slash command
    reminder_datetime: datetime.datetime
    reminder_str: str = field(compare=False)
    subscribers: set[discord.User] = field(hash=False)

    def __str__(self):
        if self.command_message is None:
            return f"{self.author.mention} @ {format_dt(self.reminder_datetime, style='F')}: {self.reminder_str!r}"
        else:
            return f"{self.command_message.author.mention} - {self.command_message.jump_url} @ {format_dt(self.reminder_datetime, style='F')}: {self.reminder_str!r}"

    def __repr__(self):
        MAX_LENGTH = 100
        if self.command_message is None:
            out = f"{self.author.name} - #{self.channel.name} @ {self.reminder_datetime:%a %b %d, %I:%M %p}: {self.reminder_str!r}"
        else:
            out = f"{self.command_message.author.name} - #{self.command_message.channel.name} @ {self.reminder_datetime:%a %b %d, %I:%M %p}: {self.reminder_str!r}"
        if len(out) > MAX_LENGTH:
            out = out[:MAX_LENGTH-3] + "..."
        return out

    def to_json(self) -> dict[str, int | float | str]:
        """Convert the current reminder object to a JSON string."""
        return {
            "author_id": self.author.id,
            "channel_id": self.channel.id,
            "command_message_id": -1 if self.command_message is None else self.command_message.id,
            "reminder_timestamp": self.reminder_datetime.timestamp(),
            "reminder_str": self.reminder_str,
            "subscriber_ids": [subscriber.id for subscriber in self.subscribers]
        }

    @staticmethod
    async def from_json(bot: commands.Bot, json_obj: dict[str, int | float | str]):
        """Convert a JSON dictionary to a Reminder object."""
        channel = bot.get_channel(json_obj["channel_id"])
        
        if channel is not None:
            command_message = None if json_obj["command_message_id"] < 0 else await channel.fetch_message(json_obj["command_message_id"])
            reminder_datetime = datetime.datetime.fromtimestamp(json_obj["reminder_timestamp"])
            reminder_str = json_obj["reminder_str"]
            author = await bot.fetch_user(json_obj["author_id"]) if command_message is None else command_message.author
            channel = await bot.fetch_channel(json_obj["channel_id"]) if command_message is None else command_message.channel
            subscribers = [] if json_obj["subscriber_ids"] is None else [await bot.fetch_user(subscriber_id) for subscriber_id in json_obj["subscriber_ids"]]

            return Reminder(author, channel, command_message, reminder_datetime, reminder_str, subscribers)
    
    def copy(self):
        # We need to ensure that different Reminder objects do not point to the same subscribers list
        # This ensures that when the list of subscribers in one Reminder is modified, copies of that Reminder are not also modified (such as Reminders._cached_reminders)
        return Reminder(self.author, self.channel, self.command_message, self.reminder_datetime, self.reminder_str, self.subscribers.copy())

class ReminderSubscribeButton(discord.ui.Button):

    def __init__(self, reminder: Reminder):
        super().__init__()
        self.reminder = reminder
        self.label = "I want to be reminded too!"

    async def callback(self, interaction: discord.Interaction):
        if interaction.user == self.reminder.author or interaction.user in self.reminder.subscribers:
            return await interaction.response.send_message("You are already set to be notified of this reminder.", ephemeral=True) #TODO: Make this a toggleable button
        self.reminder.subscribers.append(interaction.user)
        return await interaction.response.send_message("👍", ephemeral=True)

class ReminderCancelSelect(discord.ui.Select):

    def __init__(self, interaction: discord.Interaction, reminders: set[Reminder]):
        self.bot = interaction.client
        self.reminders = reminders

        options = [discord.SelectOption(label=repr(reminder)) for reminder in sorted(reminders, key=lambda r: r.reminder_datetime.timestamp())]
        super().__init__(placeholder="Select reminders to cancel...", max_values=len(reminders), options=options)
    
    async def callback(self, interaction: discord.Interaction):
        """The callback associated with this UI item."""
        cancelled_reminders = {reminder for reminder in self.reminders if repr(reminder) in self.values}
        self.bot.get_cog("Reminders").reminders[interaction.guild_id] -= cancelled_reminders

        cancelled_reminder_list = RandomColorEmbed(
            title="Cancelled Reminders", 
            description='\n'.join([str(reminder) for reminder in sorted(cancelled_reminders, key=lambda r: r.reminder_datetime.timestamp())])
        )
        await interaction.response.send_message(embed=cancelled_reminder_list, ephemeral=True)

class ReminderCancelView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, reminders: set[Reminder]):
        super().__init__()
        self.member = interaction.user
        self.add_item(ReminderCancelSelect(interaction, reminders))
    
    async def interaction_check(self, interaction: discord.Interaction):
        """Checks whether the callback should be processed."""
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
            try:
                self.reminders[guild.id] = {await Reminder.from_json(self.bot, json_str) for json_str in read_json(guild.id, "reminders")}
            except json.JSONDecodeError as e:
                print()
            self._cached_reminders[guild.id] = deepcopy(self.reminders[guild.id])
        
        self.send_reminders.start()
        self.sync_json.start()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initializes the class on server join."""
        await self.on_ready()

    @app_commands.command()
    @app_commands.rename(reminder_str="message")
    @app_commands.describe(time="When you want to be reminded")
    @app_commands.describe(reminder_str="The message you want to be reminded of")
    async def remindme(self, interaction: discord.Interaction, time: str, *, reminder_str: str):
        """Set a scheduled reminder. Example: remindme 1h30m Join stream!\n
        Format time as: _d_h_m_s (may omit individual parameters)."""
        # Determine the amount of time based on the time inputted
        num_days, num_hours, num_minutes, num_seconds, is_valid = Reminders.get_datetime_parameters(time)
        if not is_valid:
            time_string_guess = re.sub("0.", "", f"{num_days}d{num_hours}h{num_minutes}m{num_seconds}s")
            if time_string_guess == "":
                await interaction.response.send_message("Time string is not formatted correctly; not sure what you meant to type here.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Time string is not formatted correctly; did you mean to type {time_string_guess}?", ephemeral=True)
            return
        
        # If the next word looks like it could be part of the time, issue a warning
        next_word = reminder_str.split(" ")[0]
        _, _, _, _, is_valid = Reminders.get_datetime_parameters(next_word)
        if is_valid:
            await interaction.response.send_message("Warning: The timestamp should be typed as one word, without spaces.", ephemeral=True)

        # Calculate the time when the reminder should be sent at, and create a new reminder object with that timestamp
        timedelta = datetime.timedelta(days=num_days, hours=num_hours, minutes=num_minutes, seconds=num_seconds)
        reminder_datetime = datetime.datetime.now() + timedelta
        reminder = await self.create_reminder(interaction, reminder_datetime, reminder_str)

        embed = RandomColorEmbed(title = "Reminder")
        embed.description = f"You set a reminder for {format_dt(reminder_datetime, style='f')}:\n{reminder_str}"
        view = discord.ui.View()
        view.add_item(ReminderSubscribeButton(reminder))
        await interaction.response.send_message(embed=embed, view=view)

    async def create_reminder(self, interaction: discord.Interaction, time: datetime.datetime, reminder_str: str):
        "Creates a new reminder and adds it to the list of reminders."
        reminder = Reminder(interaction.user, interaction.channel, None, time, reminder_str, [])
        if interaction.guild.id not in self.reminders:
            self.reminders[interaction.guild.id] = set()
        self.reminders[interaction.guild.id].add(reminder)

        return reminder
        
    @staticmethod
    def get_datetime_parameters(time: str):
        """Convert a time string into parameters for a datetime object."""
        is_valid = True

        timer_parameters = re.fullmatch("(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time)
        if timer_parameters is None:
            timer_parameters = re.search("(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time)
            is_valid = False
        
        return (*tuple(map(lambda t: int(0 if t is None else t), timer_parameters.groups())), is_valid)

    @app_commands.command()
    @app_commands.describe(ephemeral="The message will be visible only to you")
    async def reminders(self, interaction: discord.Interaction, ephemeral: bool = False):
        """View scheduled reminders of every server member.""" 
        if len(self.reminders[interaction.guild.id]) == 0:
            return await interaction.response.send_message("No reminders currently set.", ephemeral=ephemeral)

        reminder_list = RandomColorEmbed(
            title="Scheduled Reminders",
            description='\n'.join([f"{i+1}. {reminder}" for i, reminder in enumerate(sorted(self.reminders[interaction.guild.id], key=lambda r: r.reminder_datetime.timestamp()))])
        )
        await interaction.response.send_message(embed=reminder_list, ephemeral=ephemeral)

    @app_commands.command()
    async def remindcancel(self, interaction: discord.Interaction):
        """Cancel scheduled reminders."""
        is_viewable = lambda reminder: interaction.user.guild_permissions.manage_guild or reminder.command_message.author == interaction.user
        filtered_reminders = {reminder for reminder in self.reminders[interaction.guild.id] if is_viewable(reminder)}
        
        if len(filtered_reminders) == 0:
            return await interaction.response.send_message("No reminders currently set.", ephemeral=True)

        await interaction.response.send_message(view=ReminderCancelView(interaction, filtered_reminders, ephemeral=True))

    @tasks.loop(seconds=0.2)
    async def send_reminders(self):
        """Send any reminders past their scheduled date."""
        for guild in self.bot.guilds:
            reminders = self.reminders[guild.id].copy()
            for reminder in reminders:
                if reminder.reminder_datetime.timestamp() <= datetime.datetime.now().timestamp():
                    # Read the list of reactions to the message, and create a string to mention each user (besides the bot) who reacted
                    if reminder.command_message is None: # This reminder was created via slash command
                        subscribers_mention = "\n" + " ".join(user.mention for user in reminder.subscribers if user != self.bot.user and user != reminder.author)
                        await reminder.channel.send(f"**Reminder**: {reminder.reminder_str} {reminder.author.mention}{subscribers_mention}")
                    else:
                        for reaction in reminder.command_message.reactions:
                            if reaction.emoji == "👍":
                                subscribers = [user async for user in reaction.users()]
                                subscribers_mention = "\n" + " ".join(user.mention for user in subscribers if user != self.bot.user and user != reminder.command_message.author)
                                await reminder.command_message.reply(f"{reminder.reminder_str} {subscribers_mention}")

                    self.reminders[guild.id].remove(reminder)
    
    @tasks.loop(seconds=0.3)
    async def sync_json(self):
        """Sync with the JSON file if any changes are detected."""
        for guild in self.bot.guilds:
            if self.reminders[guild.id] != self._cached_reminders[guild.id]:
                write_json(guild.id, "reminders", value=[reminder.to_json() for reminder in self.reminders[guild.id]])
                self._cached_reminders[guild.id] = deepcopy(self.reminders[guild.id])
    
def deepcopy(reminders: set[Reminder]) -> set[Reminder]:
    copied_reminders = set()
    for reminder in reminders:
        copied_reminders.add(reminder.copy())
    return copied_reminders