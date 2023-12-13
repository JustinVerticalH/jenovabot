import datetime, zoneinfo
from ioutils import read_json, write_json, RandomColorEmbed
from dateutil.parser import parse

import discord
from discord.ext import commands, tasks

class Birthdays(commands.Cog, name="Birthdays"):
    "Send messages on members' birthdays."
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.birthdays: dict[int, dict[discord.User, datetime.date]] = {}

    async def initialize(self):
        """Initialize the list of birthdays."""
        
        for guild in self.bot.guilds:
            guild_birthdays = read_json(guild.id, "birthdays")
            if guild_birthdays is None:
                write_json(guild.id, "birthdays", value={})
                self.birthdays[guild.id] = {}
            else:
                self.birthdays[guild.id] = {await self.bot.fetch_user(user_id): datetime.datetime.strptime(birthday, "%Y-%m-%d").date() for user_id, birthday in guild_birthdays.items()}

        self.send_birthday_message.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.initialize()

    @commands.Cog.listener()
    async def on_guild_join(self):
        await self.initialize()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        write_json(guild.id, "birthdays", value={})
        self.bot.birthdays[guild.id] = {}

    @commands.group(invoke_without_command=True)
    async def birthday(self, context: commands.Context, *, date_str: str):
        """Registers a user's birthday, given a month, day, and optional year."""
        date = parse(date_str).date()
        now = datetime.datetime.now(tz=zoneinfo.ZoneInfo("US/Eastern"))
        if (date.year == now.year):
            date = datetime.date(year=datetime.MINYEAR, month=date.month, day=date.day)
        
        if self.birthdays[context.guild.id] is None:
            self.birthdays[context.guild.id] = {}
        self.birthdays[context.guild.id][context.author] = date
        write_json(context.guild.id, "birthdays", value={user.id: birthday.isoformat() for user, birthday in self.birthdays[context.guild.id].items()})
        await context.message.add_reaction("👍")

    @birthday.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def channel(self, context: commands.Context, channel: discord.TextChannel):
        """Set which channel to send event alert ping messages."""
        write_json(context.guild.id, "birthday_channel_id", value=channel.id)
        await context.message.add_reaction("👍")

    @channel.error
    async def permissions_or_channel_fail(self, context: commands.Context, error: commands.errors.CommandError):
        if isinstance(error, commands.errors.MissingPermissions):
            await context.send("User needs Manage Server permission to use this command.")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await context.send("Channel not found. Try again.")

    @commands.command()
    async def nextbirthdays(self, context: commands.Context):

        # Sort the birthday dates by month and day only, not year
        # Split the dates into two groups: dates that have already happened this year, and dates that haven't
        # Add the dates that have already happened after the dates that haven't
        # This gives a list of upcoming birthdays in sorted order, including some dates from next year after this year

        now = datetime.datetime.now().date()
        next_birthdays = {user: birthday.replace(year=now.year) for user, birthday in self.birthdays[context.guild.id].items()}
        sorted_birthdays = {user: birthday for user, birthday in sorted(next_birthdays.items(), key=lambda item: item[1])}
        sorted_birthdays = {user: birthday for user, birthday in sorted_birthdays.items() if now < birthday} | {user: birthday.replace(year=now.year+1) for user, birthday in sorted_birthdays.items() if now >= birthday}

        description = ""
        n = min(10, len(sorted_birthdays.values()))
        for user, birthday in list(sorted_birthdays.items())[:n]:
            birthday_str = f"{birthday.strftime('%B')} {ordinal(int(birthday.strftime('%d')))}, {birthday.strftime('%Y')}"
            description += f"**{birthday_str}**\n{user.mention}\n\n"

        embed = RandomColorEmbed(title="Upcoming Birthdays", description=description)
        await context.send(embed=embed)

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=0, tzinfo=zoneinfo.ZoneInfo("US/Eastern"))) # 12:00 AM EST
    async def send_birthday_message(self):
        """Sends a message to users on their birthday at midnight EST."""
        for guild in self.bot.guilds:
            channel_id = read_json(guild.id, "birthday_channel_id")
            if channel_id is None:
                continue
            
            for user, birthday in self.birthdays[guild.id].items():
                now = datetime.datetime.now(tz=zoneinfo.ZoneInfo("US/Eastern"))
                if birthday.month == now.month and birthday.day == now.day:
                    # Send birthday message in the correct channel
                    channel = await self.bot.fetch_channel(channel_id)
                    
                    if birthday.year == datetime.MINYEAR:
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