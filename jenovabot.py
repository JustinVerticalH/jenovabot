import asyncio
import os
from dotenv import load_dotenv

import discord
from discord.ext import commands

from cogfiles.copypastas import Copypastas
from cogfiles.alerts import EventAlerts
from cogfiles.streampause import StreamPause
from cogfiles.reminders import Reminders
from cogfiles.announcements import Announcements
from cogfiles.music import Music


def main():
    load_dotenv()
    token = os.getenv("TOKEN")
    stream_name = os.getenv("CURRENT_STREAM_NAME")
    command_prefix = os.getenv("PREFIX")
    
    activity = discord.Game(name=stream_name)
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="!" if command_prefix is None else command_prefix, activity=activity, intents=intents, enable_debug_events=True)

    cogs = Copypastas(bot), EventAlerts(bot), StreamPause(bot), Reminders(bot), Announcements(bot), Music(bot)
    for cog in cogs:
        asyncio.run(bot.add_cog(cog))

    bot.run(token)

if __name__ == "__main__":
    main()