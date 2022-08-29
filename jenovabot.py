import os
from dotenv import load_dotenv

import discord
from discord.ext import commands

from cogfiles.copypastas import Copypastas
from cogfiles.alerts import EventAlerts
from cogfiles.streampause import StreamPause
from cogfiles.reminders import Reminders
from cogfiles.announcements import Announcements


def main():
    load_dotenv()
    token = os.getenv("TOKEN")

    command_prefix = os.getenv("PREFIX")
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="!" if command_prefix is None else command_prefix, intents=intents)


    cogs = Copypastas(bot), EventAlerts(bot), StreamPause(bot), Reminders(bot), Announcements(bot)
    for cog in cogs:
        bot.add_cog(cog)

    bot.run(token)

if __name__ == "__main__":
    main()