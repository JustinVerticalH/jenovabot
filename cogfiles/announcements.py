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
        """Starti the periodic announcements processing loop."""

        self.periodic_announcements.start()

    @commands.command()
    async def announcements(self, context: commands.Context, argument: str):
        """Set which channel to send periodic announcement messages."""
        
        if context.author.guild_permissions.manage_guild:
            for channel in context.guild.channels:
                if argument in [channel.name, channel.mention]:
                    write_sql("test_settings", context.guild.id, "periodic_announcement_channel_id", channel.id)
                    await context.send(f"Periodic announcement channel is set to {channel.mention}")
                    return
            await context.send("Channel not found. Try again.")
            return
        await context.send("User needs Manage Server permission to use this command.")
        return

    @tasks.loop(minutes=0.2)
    async def periodic_announcements(self):
        """Send periodic announcement messages at their appropriate times."""
        
        now = datetime.datetime.now(pytz.timezone("US/Eastern"))
        for guild in self.bot.guilds:
            channel_id = read_sql("test_settings", guild.id, "periodic_announcement_channel_id")
            if channel_id is not None:
                channel = self.bot.get_channel(channel_id)
                if now.weekday() == 4 and now.hour == 17 and now.minute == 0 and now.second < 12: # Friday, 5:00 PM EST
                    await channel.send(file=discord.File("ninja_troll.png"))
                if now.day == 1 and now.hour == 0 and now.minute == 0 and now.second < 12: # 1st day of the month, 12:00 AM EST
                    await channel.send(file=discord.File("first_of_the_month.mov"))