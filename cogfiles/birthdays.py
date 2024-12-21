import datetime
import zoneinfo
from dataclasses import dataclass
from ioutils import  JsonSerializable, RandomColorEmbed, read_json, write_json, initialize_from_json

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

@dataclass(frozen=True, order=True)
class Birthday(JsonSerializable):
    user: discord.Member
    date: datetime.date

    def to_json(self) -> dict[str, int | str]:
        """Convert the current ReactionRole object to a JSON string."""
        return {
            "user_id": self.user.id,
            "date": datetime.datetime.strftime(self.date,"%Y-%m-%d")
        }

    @staticmethod
    async def from_json(bot: commands.Bot, json_obj: dict[str, int | str]):
        """Convert a JSON dictionary to a ReactionRole object."""
        user = await bot.fetch_user(int(json_obj["user_id"]))
        date = datetime.datetime.strptime(json_obj["date"], "%Y-%m-%d").date()
        return Birthday(user, date)

class Birthdays(commands.Cog, name="Birthdays"):
    "Send messages on members' birthdays."
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.birthdays: dict[int, set[Birthday]] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize the list of birthdays and sync application commands."""
        await initialize_from_json(self.bot, self.birthdays, Birthday, "birthdays")

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

        birthday = Birthday(interaction.user, date)
        old_birthday = next((b for b in self.birthdays[interaction.guild.id] if b.user == birthday.user), None)
        self.birthdays[interaction.guild.id].discard(old_birthday)
        self.birthdays[interaction.guild.id].add(birthday)
        write_json(interaction.guild.id, "birthdays", value=[birthday.to_json() for birthday in self.birthdays[interaction.guild.id]])
        await interaction.response.send_message(f"Added your birthday: {month.name} {ordinal(day)}{'' if year is None else f', {year}'}", ephemeral=True)

    @app_commands.command()
    async def birthdays(self, interaction: discord.Interaction):
        """Lists the next 10 birthdays in this server."""
        # Sort the birthday dates by month and day only, not year
        # Split the dates into two groups: dates that have already happened this year, and dates that haven't
        # Add the dates that have already happened after the dates that haven't
        # This gives a list of upcoming birthdays in sorted order, including some dates from next year after this year
        now = datetime.datetime.now().date()
        next_birthdays = {Birthday(birthday.user, birthday.date.replace(year=now.year)) for birthday in self.birthdays[interaction.guild.id]}        
        this_year_birthdays = {birthday for birthday in next_birthdays if now < birthday.date}
        next_year_birthdays = {Birthday(birthday.user, birthday.date.replace(year=birthday.date.year+1)) for birthday in next_birthdays if now >= birthday.date}
        sorted_birthdays = sorted(this_year_birthdays | next_year_birthdays, key=lambda birthday: birthday.date)

        description = ""
        n = min(10, len(sorted_birthdays))
        for birthday in list(sorted_birthdays)[:n]:
            birthday_str = f"{Month(birthday.date.month).name} {ordinal(birthday.date.day)}, {birthday.date.year}"
            description += f"**{birthday_str}**\n{birthday.user.mention}\n\n"

        embed = RandomColorEmbed(title="Upcoming Birthdays", description=description)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=0, tzinfo=zoneinfo.ZoneInfo("US/Eastern"))) # 12:00 AM EST
    async def send_birthday_message(self):
        """Sends a message to users on their birthday at midnight EST."""
        for guild in self.bot.guilds:
            channel_id = read_json(guild.id, "birthday_channel_id")
            if channel_id is None:
                continue
            
            for birthday in self.birthdays[guild.id]:
                now = datetime.datetime.now(tz=zoneinfo.ZoneInfo("US/Eastern"))
                if birthday.date.month == now.month and birthday.date.day == now.day:
                    # Send birthday message in the correct channel
                    channel = await self.bot.fetch_channel(channel_id)
                    
                    if birthday.date.year == datetime.MINYEAR:
                        await channel.send(f"Happy birthday {birthday.user.mention}!")
                    else:
                        age = now.year - birthday.date.year
                        await channel.send(f"Happy {ordinal(age)} birthday {birthday.user.mention}!")


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