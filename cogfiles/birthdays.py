import datetime, zoneinfo
from ioutils import read_json, write_json, RandomColorEmbed

import discord
from discord import app_commands
from discord.ext import commands, tasks
from enum import Enum


class Month(Enum):
    January = 1
    February = 2
    March = 3
    April = 4
    May = 5
    June = 6
    July = 7
    August = 8
    September = 9
    October = 10
    November = 11
    December = 12

class Birthdays(commands.Cog, name="Birthdays"):
    "Send messages on members' birthdays."
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.birthdays: dict[int, dict[discord.User, datetime.date]] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize the list of birthdays and sync application commands."""
        for guild in self.bot.guilds:
            guild_birthdays = read_json(guild.id, "birthdays")
            if guild_birthdays is None:
                write_json(guild.id, "birthdays", value={})
                self.birthdays[guild.id] = {}
            else:
                self.birthdays[guild.id] = {await self.bot.fetch_user(user_id): datetime.datetime.strptime(birthday, "%Y-%m-%d").date() for user_id, birthday in guild_birthdays.items()}

        self.send_birthday_message.start()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initializes the class on server join."""
        await self.on_ready()

    @app_commands.command()
    async def birthday(self, interaction: discord.Interaction, month: Month, day: app_commands.Range[int, 1, 31], year: int | None):
        """Saves your birthday. On your birthday, JENOVA will send a happy birthday message."""
        try:
            date = datetime.date(year=datetime.MINYEAR if year is None else year, month=month.value, day=day) # Setting the year to MINYEAR represents no year provided
        except ValueError:
            return await interaction.response.send_message("Invalid date.", ephemeral=True)
        if self.birthdays[interaction.guild.id] is None:
            self.birthdays[interaction.guild.id] = {}
        self.birthdays[interaction.guild.id][interaction.user] = date
        write_json(interaction.guild.id, "birthdays", value={user.id: birthday.isoformat() for user, birthday in self.birthdays[interaction.guild.id].items()})
        await interaction.response.send_message(f"Added your birthday: {month.name} {ordinal(day)}{'' if year == None else f', {year}'}", ephemeral=True)

    @app_commands.command()
    async def birthdays(self, interaction: discord.Interaction):
        """Lists the next 10 birthdays in this server."""
        # Sort the birthday dates by month and day only, not year
        # Split the dates into two groups: dates that have already happened this year, and dates that haven't
        # Add the dates that have already happened after the dates that haven't
        # This gives a list of upcoming birthdays in sorted order, including some dates from next year after this year
        now = datetime.datetime.now().date()
        next_birthdays = {user: birthday.replace(year=now.year) for user, birthday in self.birthdays[interaction.guild.id].items()}
        sorted_birthdays = {user: birthday for user, birthday in sorted(next_birthdays.items(), key=lambda item: item[1])}
        sorted_birthdays = {user: birthday for user, birthday in sorted_birthdays.items() if now < birthday} | {user: birthday.replace(year=now.year+1) for user, birthday in sorted_birthdays.items() if now >= birthday}

        description = ""
        n = min(10, len(sorted_birthdays.values()))
        for user, birthday in list(sorted_birthdays.items())[:n]:
            birthday_str = f"{Month(birthday.month).name} {ordinal(birthday.day)}, {birthday.year}"
            description += f"**{birthday_str}**\n{user.mention}\n\n"

        embed = RandomColorEmbed(title="Upcoming Birthdays", description=description)
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
    """Converts a number to a string representation of the number in ordinal form (1st, 2nd, 3rd, etc)."""
    if n % 100 in [11, 12, 13]:
        return f"{n}th"
    if n % 10 == 1:
        return f"{n}st"
    if n % 10 == 2:
        return f"{n}nd"
    if n % 10 == 3:
        return f"{n}rd"
    return f"{n}th"