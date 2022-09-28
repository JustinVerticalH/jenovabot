import discord, json, os

from dotenv import load_dotenv
from discord.ext import commands


class Copypastas(commands.Cog, name="Message Copypastas"):
    """Send a copypasta whenever a key phrase is found in a message."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detect key phrases in messages."""

        if message.author == self.bot.user:
            return
        
        load_dotenv()
        copypastas_json = os.getenv("COPYPASTAS")
        copypastas = json.loads(copypastas_json)
        for phrase in copypastas:
            if phrase in message.content.lower():
                await message.channel.send(copypastas[phrase])