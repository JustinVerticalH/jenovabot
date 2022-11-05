import datetime, pytz
from ioutils import read_sql, write_sql, DATABASE_SETTINGS

import discord
from discord.ext import commands, tasks


class Announcements(commands.Cog, name="Periodic Announcements"):
    """Periodically send specific messages in certain channels at scheduled times."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Start the periodic announcements processing loop."""

        self.ninja_troll.start()
        self.first_of_the_month.start()

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def announcements(self, context: commands.Context, channel: discord.TextChannel):
        """Set which channel to send periodic announcement messages."""
        
        write_sql(DATABASE_SETTINGS, context.guild.id, "periodic_announcement_channel_id", channel.id)
        await context.send(f"Periodic announcement channel is set to {channel.mention}")

    @announcements.error
    async def permissions_or_channel_fail(self, context: commands.Context, error: commands.errors.CommandError):
        if isinstance(error, commands.errors.MissingPermissions):
            await context.send("User needs Manage Server permission to use this command.")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await context.send("Channel not found. Try again.")

    @tasks.loop(time=datetime.time(hour=17, minute=0, second=0, tzinfo=pytz.timezone("US/Eastern"))) # 5:00 PM EST
    async def ninja_troll(self):
        """Send periodic announcement messages at their appropriate times."""
        
        if datetime.date.today().weekday() != 4: # Friday
            return
        
        for guild in self.bot.guilds:
            channel_id = read_sql(DATABASE_SETTINGS, guild.id, "periodic_announcement_channel_id")
            if channel_id is not None:
                channel = await self.bot.fetch_channel(channel_id)
                await channel.send(file=discord.File("ninja_troll.png"))

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=0, tzinfo=pytz.timezone("US/Eastern"))) # 12:00 AM EST
    async def first_of_the_month(self):
        """Send periodic announcement messages at their appropriate times."""
        
        if datetime.date.today().day != 1: # 1st day of the month
            return
        
        for guild in self.bot.guilds:
            channel_id = read_sql(DATABASE_SETTINGS, guild.id, "periodic_announcement_channel_id")
            if channel_id is not None:
                channel = await self.bot.fetch_channel(channel_id)
                await channel.send(file=discord.File("first_of_the_month.mov"))