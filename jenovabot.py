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
<<<<<<< HEAD
from cogfiles.web_scrapers import WebScrapers
=======
from cogfiles.polling import Polling
>>>>>>> 0510289e2c65c3d14fa1b292ef6219feaaeddf8b


def main():
    load_dotenv()
    token = os.getenv("TOKEN")
    stream_name = os.getenv("CURRENT_STREAM_NAME")
    command_prefix = os.getenv("PREFIX", default="!")
    
    activity = discord.Game(name=stream_name)
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix=command_prefix, activity=activity, intents=intents, enable_debug_events=True)

<<<<<<< HEAD
    cogs = Copypastas(bot), EventAlerts(bot), StreamPause(bot), Reminders(bot), Announcements(bot), Music(bot), WebScrapers(bot)
=======
    cogs = Copypastas(bot), EventAlerts(bot), StreamPause(bot), Reminders(bot), Announcements(bot), Music(bot), Polling(bot)
>>>>>>> 0510289e2c65c3d14fa1b292ef6219feaaeddf8b
    for cog in cogs:
        asyncio.run(bot.add_cog(cog))

    bot.run(token)

if __name__ == "__main__":
    main()