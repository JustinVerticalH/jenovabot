import datetime, dateparser, json, pytz
from ioutils import read_sql, write_sql, DATABASE_SETTINGS

import discord
from discord.ext import commands, tasks

class Birthdays(commands.Cog, name="Birthdays"):
    "Send messages on members' birthdays."
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.birthdays: dict[int, dict[int, datetime.date]] = {}

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
        date = dateparser.parse(date_str).date()
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

    @tasks.loop(seconds=1)
    async def send_birthday_message(self):
        """Sends a message to users on their birthday at midnight EST."""
        now = datetime.datetime.now(pytz.timezone("US/Eastern"))
        if now.hour == 0 and now.minute == 0 and now.second == 0: # Start of the day
            for guild in self.bot.guilds:
                channel_id = read_sql(DATABASE_SETTINGS, guild.id, "birthday_channel_id")
                if channel_id is not None:
                    guild_birthdays = self.birthdays[guild.id]
                    for user_birthdays in guild_birthdays.items():
                        user_id = int(user_birthdays[0])
                        birthday = datetime.datetime.strptime(user_birthdays[1], "%Y-%m-%d")
                        if birthday.month == now.month and birthday.day == now.day:

                            # Send birthday message in the correct channel
                            user = await self.bot.fetch_user(user_id)
                            channel = self.bot.get_channel(channel_id)
                            age = now.year - birthday.year
                            if age == 0:
                                await channel.send(f"Happy birthday {user.mention}!")
                            else:
                                await channel.send(f"Happy {Birthdays.ordinal(age)} birthday {user.mention}!")              

    @staticmethod
    def ordinal(n: int) -> str:
        n_str = str(n)
        last_char = n_str[-1]
        if n_str in ["11", "12", "13"]:
            return n_str + "th"
        if last_char == "1":
            return n_str + "st"
        if last_char == "2":
            return n_str + "nd"
        if last_char == "3":
            return n_str + "rd"
        return n_str + "th"