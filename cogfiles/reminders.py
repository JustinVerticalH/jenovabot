import datetime
from dataclasses import dataclass, field
from ioutils import JsonSerializable, RandomColorEmbed, write_json, initialize_from_json

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import format_dt


@dataclass(frozen=True, order=True)
class Reminder(JsonSerializable):
    """Data associated with a scheduled reminder."""
    author: discord.User = field(compare=False)
    channel: discord.TextChannel | discord.ForumChannel = field(compare=False)
    command_message: discord.Message = field(compare=False) # This will be None when the reminder is created via slash command
    original_message_datetime: datetime.datetime = field(compare=False)
    reminder_datetime: datetime.datetime
    reminder_str: str = field(compare=False)
    slash_message: discord.Message = field(compare=False) # This will be None when the reminder is created via regular command
    subscribers: set[discord.User] = field(hash=False)

    def __str__(self):
        message = self.slash_message if self.command_message is None else self.command_message
        return f"{self.author.mention} - {message.jump_url} @ {format_dt(self.reminder_datetime, style='F')}: {self.reminder_str!r}"

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
            "original_message_timestamp": -1 if self.original_message_datetime is None else self.original_message_datetime.timestamp(),
            "reminder_timestamp": self.reminder_datetime.timestamp(),
            "reminder_str": self.reminder_str,
            "slash_message_id": -1 if self.slash_message is None else self.slash_message.id,
            "subscriber_ids": [subscriber.id for subscriber in self.subscribers]
        }

    @staticmethod
    async def from_json(bot: commands.Bot, json_obj: dict[str, int | float | str]):
        """Convert a JSON dictionary to a Reminder object."""
        channel = bot.get_channel(json_obj["channel_id"])
        
        if channel is not None:
            command_message = None if json_obj["command_message_id"] < 0 else await channel.fetch_message(json_obj["command_message_id"])
            original_message_datetime = datetime.datetime.fromtimestamp(json_obj["original_message_timestamp"]) if command_message is None else command_message.created_at
            reminder_datetime = datetime.datetime.fromtimestamp(json_obj["reminder_timestamp"])
            reminder_str = json_obj["reminder_str"]
            author = await bot.fetch_user(json_obj["author_id"]) if command_message is None else command_message.author
            channel = await bot.fetch_channel(json_obj["channel_id"]) if command_message is None else command_message.channel
            slash_message = None if json_obj["slash_message_id"] < 0 else await channel.fetch_message(json_obj["slash_message_id"])
            subscribers = [await bot.fetch_user(subscriber_id) for subscriber_id in json_obj["subscriber_ids"]] if command_message is None else []

            return Reminder(author, channel, command_message, original_message_datetime, reminder_datetime, reminder_str, slash_message, subscribers)

    def copy(self):
        # We need to ensure that different Reminder objects do not point to the same subscribers list
        # This ensures that when the list of subscribers in one Reminder is modified, copies of that Reminder are not also modified (such as Reminders._cached_reminders)
        return Reminder(self.author, self.channel, self.command_message, self.original_message_datetime, self.reminder_datetime, self.reminder_str, self.slash_message, self.subscribers.copy())

class ReminderSubscribeView(discord.ui.View):

    def __init__(self, reminder):
        super().__init__(timeout=None)
        self.reminder: Reminder | None = reminder # This will be None after the reminder has been sent

    @discord.ui.button(label="I want to be reminded too!", emoji="👍", custom_id="reminder_subscribe_button")
    async def subscribe_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.reminder is None:
            return await interaction.response.send_message("This reminder has already been sent.", ephemeral=True)
        if interaction.user == self.reminder.author:
            return await interaction.response.send_message("You are already set to be notified of this reminder.", ephemeral=True) #TODO: Make this a toggleable button
        if interaction.user in self.reminder.subscribers:
            self.reminder.subscribers.remove(interaction.user)
            return await interaction.response.send_message("You will no longer be reminded of this.", ephemeral=True)
        else:
            self.reminder.subscribers.append(interaction.user)
            return await interaction.response.send_message(f"You will be reminded of this {format_dt(self.reminder.reminder_datetime, style='R')}.", ephemeral=True)

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
        super().__init__(timeout=None)
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
        await initialize_from_json(self.bot, self.reminders, Reminder, "reminders")
        for guild in self.bot.guilds:
            self._cached_reminders[guild.id] = deepcopy(self.reminders[guild.id])
            for reminder in self.reminders[guild.id]:
                if reminder.slash_message is not None:
                    # This makes the views on existing reminders persistent between application restarts
                    view = ReminderSubscribeView(reminder)
                    self.bot.add_view(view=view, message_id=reminder.slash_message.id)
        self.send_reminders.start()
        self.sync_json.start()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initializes the class on server join."""
        await self.on_ready()

    @app_commands.command()
    @app_commands.rename(reminder_str="message")
    async def remindme(self, interaction: discord.Interaction, reminder_str: str, days: int=0, hours: int=0, minutes: int=0, seconds: int=0):
        """Set a scheduled reminder. JENOVA will ping you once the time has passed."""
        # Calculate the time when the reminder should be sent at, and create a new reminder object with that timestamp
        timedelta = datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        reminder_datetime = datetime.datetime.now() + timedelta
        if reminder_datetime <= datetime.datetime.now():
            return await interaction.response.send_message("Reminders cannot be set for the past.", ephemeral=True)

        embed = RandomColorEmbed(title="Reminder")
        embed.description = f"You set a reminder for {format_dt(reminder_datetime, style='f')}:\n\"{reminder_str}\""
        view = ReminderSubscribeView(None)
        await interaction.response.send_message(embed=embed, view=view)
        reminder = await self.create_reminder(interaction, reminder_datetime, reminder_str)
        view.reminder = reminder
        self.bot.add_view(view=view, message_id=reminder.slash_message.id)

    async def create_reminder(self, interaction: discord.Interaction, time: datetime.datetime, reminder_str: str):
        "Creates a new reminder and adds it to the list of reminders."
        message = await interaction.original_response()
        reminder = Reminder(interaction.user, interaction.channel, None, datetime.datetime.now(), time, reminder_str, message, [])
        if interaction.guild.id not in self.reminders:
            self.reminders[interaction.guild.id] = set()
        self.reminders[interaction.guild.id].add(reminder)

        return reminder

    @app_commands.command()
    async def reminders(self, interaction: discord.Interaction):
        """View scheduled reminders of every server member.""" 
        if len(self.reminders[interaction.guild.id]) == 0:
            return await interaction.response.send_message("No reminders currently set.", ephemeral=True)

        reminder_list = RandomColorEmbed(
            title="Scheduled Reminders",
            description='\n'.join([f"{i+1}. {reminder}" for i, reminder in enumerate(sorted(self.reminders[interaction.guild.id], key=lambda r: r.reminder_datetime.timestamp()))])
        )
        await interaction.response.send_message(embed=reminder_list, ephemeral=True)

    @app_commands.command()
    async def remindcancel(self, interaction: discord.Interaction):
        """Cancel scheduled reminders."""
        is_viewable = lambda reminder: interaction.user.guild_permissions.manage_guild or reminder.author == interaction.user
        filtered_reminders = {reminder for reminder in self.reminders[interaction.guild.id] if is_viewable(reminder)}
        
        if len(filtered_reminders) == 0:
            return await interaction.response.send_message("No reminders currently set.", ephemeral=True)

        await interaction.response.send_message(view=ReminderCancelView(interaction, filtered_reminders), ephemeral=True)

    @tasks.loop(seconds=0.2)
    async def send_reminders(self):
        """Send any reminders past their scheduled date."""
        for guild in self.bot.guilds:
            reminders = self.reminders[guild.id].copy()
            for reminder in reminders:
                if reminder.reminder_datetime.timestamp() <= datetime.datetime.now().timestamp():
                    # Read the list of reactions to the message, and create a string to mention each user (besides the bot) who reacted
                    if reminder.command_message is None: # This reminder was created via slash command
                        message = reminder.slash_message
                        subscribers_mention = " ".join(user.mention for user in reminder.subscribers if user != self.bot.user and user != reminder.author)
                    else: # This reminder was created via regular command
                        message = reminder.command_message
                        subscribers_mention = ""
                        for reaction in reminder.command_message.reactions:
                            if reaction.emoji == "👍":
                                subscribers = [user async for user in reaction.users()]
                                subscribers_mention = " ".join(user.mention for user in subscribers if user != self.bot.user and user != reminder.command_message.author)
                    await message.reply(f"**Reminder** from {format_dt(reminder.original_message_datetime, 'R')}\n\"{reminder.reminder_str}\"\n{reminder.author.mention}{subscribers_mention}")

                    # Remove the reminder from memory
                    self.reminders[guild.id].remove(reminder)
                    view = ReminderSubscribeView(None)
                    self.bot.add_view(view=view, message_id=reminder.slash_message.id)
    
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