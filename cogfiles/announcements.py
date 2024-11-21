import datetime, holidays, json, random, zoneinfo
from dataclasses import dataclass
from ioutils import read_json, write_json
from cogfiles.image_editing import ImageEditing

import discord
from discord import app_commands
from discord.ext import commands, tasks


ANNOUNCEMENT_FILES_FOLDER = "announcements"


@dataclass
class AnnouncementConfig:
    """Contains parameters for a looping announcement, including the date/time to send the message and the contents of the message."""
    time: datetime.time
    month: int | None
    day: int | None
    weekday: int | None
    holiday: str | None
    message: str | None
    filename: str | None

    def __init__(self, date: dict[str, int], message: str | None, filename: str | None):
        """Initializes the announcement config, given the necessary arguments."""
        self.time = datetime.time(hour=date["hour"], minute=date["minute"], second=date["second"], tzinfo=zoneinfo.ZoneInfo("US/Eastern"))

        self.month = date.get("month")
        self.day = date.get("day")
        
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.weekday = {day: num for num, day in enumerate(weekdays)}.get(date.get("weekday"))

        self.holiday = date.get("holiday")

        self.message = message
        self.filename = filename
    
    def date_matches(self, date: datetime.date):
        """Determines if a given date matches this date."""
        if self.month is not None and self.month != date.month:
            return False
            
        if self.day is not None and self.day != date.day:
            return False
        
        if self.weekday is not None and self.weekday != date.weekday():
            return False
        
        if self.holiday is not None and self.holiday != holidays.country_holidays("US").get(date):
            return False
        
        return True

class Announcements(commands.Cog, name="Periodic Announcements"):
    """Periodically send specific messages in certain channels at scheduled times."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Start the periodic announcements processing loops."""
        with open("announcements.json", "r", encoding="utf8") as file:
            configs = map(lambda config: AnnouncementConfig(config["date"], config.get("message"), config.get("filename")), json.load(file))

        for config in configs:
            if config.message is not None or config.filename is not None:
                self.create_announcement_loop(config).start()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initializes the class on server join."""
        await self.on_ready()

    @app_commands.command()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def announcementchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set which channel to send periodic announcement messages."""
        write_json(interaction.guild.id, "periodic_announcement_channel_id", value=channel.id)
        await interaction.response.send_message(f"Periodic announcement channel is set to {channel.mention}", ephemeral=True)

    @app_commands.command()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def dailymessagechannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set which channel to send daily messages."""
        write_json(interaction.guild.id, "daily_message_channel_id", value=channel.id)
        await interaction.response.send_message(f"Daily message channel is set to {channel.mention}", ephemeral=True)

    @announcementchannel.error
    @dailymessagechannel.error
    async def permissions_or_channel_fail(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handles errors for the given command (insufficient permissions, etc)."""
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You need the Manage Server permission to use this command.", ephemeral=True)
        elif isinstance(error, commands.errors.ChannelNotFound):
            await interaction.response.send_message("Channel not found. Try again.", ephemeral=True)

    def create_announcement_loop(self, config: AnnouncementConfig):
        """Creates a task loop that runs and sends a message at the times given by the config."""
        @tasks.loop(time=config.time)
        async def announcement_loop():
            """Loops at the given times, sending a message with the config's file each time."""
            if not config.date_matches(datetime.datetime.today().date()):
                return
            
            for guild in self.bot.guilds:
                channel_id = read_json(guild.id, "periodic_announcement_channel_id")
                if channel_id is not None:
                    channel = await self.bot.fetch_channel(channel_id)
                    file_path = f"{ANNOUNCEMENT_FILES_FOLDER}/{config.filename}"
                    await channel.send(config.message, file=discord.File(file_path))
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
                file = await ImageEditing.create_kagetsu_toya_file(channel, None, message+item)
                await channel.send(file=file)