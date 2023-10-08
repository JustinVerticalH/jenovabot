import datetime, zoneinfo
from ioutils import read_json, write_json

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
        self.umineko_video_1.start()
        self.umineko_video_2.start()
        self.umineko_video_3.start()

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def announcements(self, context: commands.Context, channel: discord.TextChannel):
        """Set which channel to send periodic announcement messages."""
        
        write_json(context.guild.id, "periodic_announcement_channel_id", value=channel.id)
        await context.send(f"Periodic announcement channel is set to {channel.mention}")

    @announcements.error
    async def permissions_or_channel_fail(self, context: commands.Context, error: commands.errors.CommandError):
        if isinstance(error, commands.errors.MissingPermissions):
            await context.send("User needs Manage Server permission to use this command.")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await context.send("Channel not found. Try again.")

    @tasks.loop(time=datetime.time(hour=17, minute=0, second=0, tzinfo=zoneinfo.ZoneInfo("US/Eastern"))) # 5:00 PM EST
    async def ninja_troll(self):
        """Send periodic announcement messages at their appropriate times."""
        
        if datetime.date.today().weekday() != 4: # Friday
            return
        
        for guild in self.bot.guilds:
            channel_id = read_json(guild.id, "periodic_announcement_channel_id")
            if channel_id is not None:
                channel = await self.bot.fetch_channel(channel_id)
                await channel.send(file=discord.File("ninja_troll.png"))

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=0, tzinfo=zoneinfo.ZoneInfo("US/Eastern"))) # 12:00 AM EST
    async def first_of_the_month(self):
        """Send periodic announcement messages at their appropriate times."""
        
        if datetime.date.today().day != 1: # 1st day of the month
            return
        
        for guild in self.bot.guilds:
            channel_id = read_json(guild.id, "periodic_announcement_channel_id")
            if channel_id is not None:
                channel = await self.bot.fetch_channel(channel_id)
                await channel.send(file=discord.File("first_of_the_month.mov"))

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=0, tzinfo=zoneinfo.ZoneInfo("US/Eastern"))) # 12:00 AM EST
    async def umineko_video_1(self):
        """Send periodic announcement messages at their appropriate times."""
        
        if datetime.date.today().month != 10 or datetime.date.today().day != 4: # October 4th
            return
        
        for guild in self.bot.guilds:
            channel_id = read_json(guild.id, "periodic_announcement_channel_id")
            if channel_id is not None:
                channel = await self.bot.fetch_channel(channel_id)
                await channel.send(file=discord.File("oct4day.mov"))

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=0, tzinfo=zoneinfo.ZoneInfo("US/Eastern"))) # 12:00 AM EST
    async def umineko_video_2(self):
        """Send periodic announcement messages at their appropriate times."""
        
        if datetime.date.today().month != 10 or datetime.date.today().day != 5: # October 5th
            return
        
        for guild in self.bot.guilds:
            channel_id = read_json(guild.id, "periodic_announcement_channel_id")
            if channel_id is not None:
                channel = await self.bot.fetch_channel(channel_id)
                await channel.send(file=discord.File("oct4end.mov"))
    
    @tasks.loop(time=datetime.time(hour=8, minute=0, second=0, tzinfo=zoneinfo.ZoneInfo("US/Eastern"))) # 8:00 AM EST
    async def umineko_video_3(self):
        """Send periodic announcement messages at their appropriate times."""
        
        if datetime.date.today().month != 10 or datetime.date.today().day != 5: # October 5th
            return
        
        for guild in self.bot.guilds:
            channel_id = read_json(guild.id, "periodic_announcement_channel_id")
            if channel_id is not None:
                channel = await self.bot.fetch_channel(channel_id)
                await channel.send(file=discord.File("oct5day.mov"))