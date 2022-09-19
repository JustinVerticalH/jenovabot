import datetime, pytz
from ioutils import read_sql, write_sql

import discord
from discord.ext import commands, tasks


class Announcements(commands.Cog, name="Periodic Announcements"):
    """Periodically send specific messages in certain channels at scheduled times."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        

    @commands.Cog.listener()
    async def on_ready(self):
        """Start the periodic announcements processing loop."""

        self.periodic_announcements.start()

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def announcements(self, context: commands.Context, channel: discord.TextChannel):
        """Set which channel to send periodic announcement messages."""
        
        write_sql("settings", context.guild.id, "periodic_announcement_channel_id", channel.id)
        await context.send(f"Periodic announcement channel is set to {channel.mention}")
    
    @announcements.error
    async def permissions_or_channel_fail(self, context: commands.Context, error: commands.errors.CommandError):
        if isinstance(error, commands.errors.MissingPermissions):
            await context.send("User needs Manage Server permission to use this command.")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await context.send("Channel not found. Try again.")

    @tasks.loop(seconds=12)
    async def periodic_announcements(self):
        """Send periodic announcement messages at their appropriate times."""
        
        now = datetime.datetime.now(pytz.timezone("US/Eastern"))
        for guild in self.bot.guilds:
            channel_id = read_sql("settings", guild.id, "periodic_announcement_channel_id")
            if channel_id is not None:
                channel = self.bot.get_channel(channel_id)
                if now.weekday() == 4 and now.hour == 17 and now.minute == 0 and now.second < 12: # Friday, 5:00 PM EST
                    await channel.send(file=discord.File("ninja_troll.png"))
                if now.day == 1 and now.hour == 0 and now.minute == 0 and now.second < 12: # 1st day of the month, 12:00 AM EST
                    await channel.send(file=discord.File("first_of_the_month.mov"))