import datetime, json, pytz
from ioutils import read_sql, write_sql, DATABASE_SETTINGS
from dateutil.parser import parse

import discord
from discord.ext import commands, tasks

class Birthdays(commands.Cog, name="Birthdays"):
    "Send messages on members' birthdays."
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.birthdays: dict[int, dict[int, str]] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize the list of birthdays."""
        for guild in self.bot.guilds:
            guild_birthdays = read_sql(DATABASE_SETTINGS, guild.id, "birthdays")
            if guild_birthdays is None:
                write_sql(DATABASE_SETTINGS, guild.id, "birthdays", json.dumps({}))
                self.birthdays[guild.id] = {}
            else:
                self.birthdays[guild.id] = guild_birthdays

        self.send_birthday_message.start()


    @commands.group(invoke_without_command=True)
    async def birthday(self, context: commands.Context, *, date_str: str):
        """Registers a user's birthday, given a month, day, and optional year."""
        date = parse(date_str).date()
        now = datetime.datetime.now(tzinfo=pytz.timezone("US/Eastern"))
        if (date.year == now.year):
            date.year = 0
        
        if self.birthdays[context.guild.id] is None:
            self.birthdays[context.guild.id] = {}
        self.birthdays[context.guild.id][str(context.author.id)] = date.isoformat()
        write_sql(DATABASE_SETTINGS, context.guild.id, "birthdays", json.dumps(self.birthdays[context.guild.id]))
        await context.message.add_reaction("👍")

    @birthday.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def channel(self, context: commands.Context, channel: discord.TextChannel):
        """Set which channel to send event alert ping messages."""
        write_sql(DATABASE_SETTINGS, context.guild.id, "birthday_channel_id", channel.id)
        await context.message.add_reaction("👍")

    @channel.error
    async def permissions_or_channel_fail(self, context: commands.Context, error: commands.errors.CommandError):
        if isinstance(error, commands.errors.MissingPermissions):
            await context.send("User needs Manage Server permission to use this command.")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await context.send("Channel not found. Try again.")

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=0, tzinfo=pytz.timezone("US/Eastern"))) # 12:00 AM EST
    async def send_birthday_message(self):
        """Sends a message to users on their birthday at midnight EST."""
        for guild in self.bot.guilds:
            channel_id = read_sql(DATABASE_SETTINGS, guild.id, "birthday_channel_id")
            if channel_id is None:
                return
            
            for user_id, birthday_iso in self.birthdays[guild.id].items():
                birthday = datetime.datetime.strptime(birthday_iso, "%Y-%m-%d")
                now = datetime.datetime.now(tzinfo=pytz.timezone("US/Eastern"))
                if birthday.month == now.month and birthday.day == now.day:
                    # Send birthday message in the correct channel
                    user = await self.bot.fetch_user(user_id)
                    channel = await self.bot.fetch_channel(channel_id)
                    
                    if birthday.year == 0:
                        await channel.send(f"Happy birthday {user.mention}!")
                    else:
                        age = now.year - birthday.year
                        await channel.send(f"Happy {ordinal(age)} birthday {user.mention}!")


def ordinal(n: int) -> str:
    if n % 100 == 11 or n % 100 == 12 or n % 100 == 13:
        return f"{n}th"
    if n % 10 == 1:
        return f"{n}st"
    if n % 10 == 2:
        return f"{n}nd"
    if n % 10 == 3:
        return f"{n}rd"
    return f"{n}th"