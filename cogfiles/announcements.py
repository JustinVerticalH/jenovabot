import datetime, json, random, zoneinfo
from dataclasses import dataclass, field
from ioutils import read_json, write_json
from cogfiles.image_editing import ImageEditing

import discord
from discord.ext import commands, tasks

@dataclass
class AnnouncementConfig:
    time: datetime.time
    month: int | None
    day: int | None
    weekday: int | None
    message: str | None
    file: discord.File | None

    def __init__(self, date: dict[str, int], message: str | None, filename: str | None):
        self.time = datetime.time(hour=date["hour"], minute=date["minute"], second=date["second"], tzinfo=zoneinfo.ZoneInfo("US/Eastern"))
        
        self.month = date.get("month")
        self.day = date.get("day")
        
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.weekday = {day: num for num, day in enumerate(weekdays)}.get(date.get("weekday"))

        self.message = message
        self.file = None if filename is None else discord.File(filename)
    
    def date_matches(self, date: datetime.datetime):
        if self.month is not None and self.month != date.month:
            return False
            
        if self.day is not None and self.day != date.day:
            return False
        
        if self.weekday is not None and self.weekday != date.weekday():
            return False
        
        return True

class Announcements(commands.Cog, name="Periodic Announcements"):
    """Periodically send specific messages in certain channels at scheduled times."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def initialize(self):
        """Start the periodic announcements processing loops."""

        with open("announcements.json", "r", encoding="utf8") as file:
            configs = map(lambda config: AnnouncementConfig(config["date"], config.get("message"), config.get("filename")), json.load(file))

        for config in configs:
            if config.message is not None or config.file is not None:
                self.create_announcement_loop(config).start()

        self.daily_message.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.initialize()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.initialize()

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def announcementchannel(self, context: commands.Context, channel: discord.TextChannel):
        """Set which channel to send periodic announcement messages."""
        
        write_json(context.guild.id, "periodic_announcement_channel_id", value=channel.id)
        await context.send(f"Periodic announcement channel is set to {channel.mention}")

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def dailymessagechannel(self, context: commands.Context, channel: discord.TextChannel):
        """Set which channel to send daily messages."""

        write_json(context.guild.id, "daily_message_channel_id", value=channel.id)
        await context.send(f"Daily message channel is set to {channel.mention}")

    @announcementchannel.error
    @dailymessagechannel.error
    async def permissions_or_channel_fail(self, context: commands.Context, error: commands.errors.CommandError):
        if isinstance(error, commands.errors.MissingPermissions):
            await context.send("User needs Manage Server permission to use this command.")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await context.send("Channel not found. Try again.")

    def create_announcement_loop(self, config: AnnouncementConfig):
        @tasks.loop(time=config.time)
        async def announcement_loop():
            if not config.date_matches(datetime.datetime.today()):
                return
            
            for guild in self.bot.guilds:
                channel_id = read_json(guild.id, "periodic_announcement_channel_id")
                if channel_id is not None:
                    channel = await self.bot.fetch_channel(channel_id)
                    await channel.send(config.message, file=config.file)
        return announcement_loop
    
    @tasks.loop(time=datetime.time(hour=0, minute=0, second=0, tzinfo=zoneinfo.ZoneInfo("US/Eastern"))) # 12:00 AM EST
    async def daily_message(self):
        """Generate a random quote from the list of daily messages and send it with a random Kagetsu Tōya template."""

        for guild in self.bot.guilds:
            channel_id = read_json(guild.id, "daily_message_channel_id")
            if channel_id is not None:
                channel = await self.bot.fetch_channel(channel_id)

                # Randomly choose the text for the image
                with open("dailymessages.json", "r", encoding="utf8") as file:
                    headers = json.load(file)            
                message = random.choice(list(headers.keys()))
                item = random.choice(headers[message])
                await ImageEditing.send_kagetsutoya_in_channel(channel, None, message+item)