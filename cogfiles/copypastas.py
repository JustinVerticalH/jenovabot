from ioutils import read_json

import discord
from discord.ext import commands


class Copypastas(commands.Cog, name="Message Copypastas"):
    """A Cog to handle sending a copypasta whenever a key phrase is found in a message."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """A listener for detecting key phrases in messages."""

        if message.author == self.bot.user:
            return
        copypastas = read_json("copypastas.json")
        for phrase in copypastas:
            if phrase in message.content.lower():
                await message.channel.send(copypastas[phrase])