import discord, json

from discord.ext import commands


class Copypastas(commands.Cog, name="Message Copypastas"):
    """Send a copypasta whenever a key phrase is found in a message."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        with open("copypastas.json", "r") as file:
            self.copypastas = json.load(file)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detect key phrases in messages."""
        # The bot shouldn't respond to its own copypastas
        if message.author == self.bot.user:
            return
        for phrase in self.copypastas:
            if phrase in message.content.lower():
                await message.channel.send(self.copypastas[phrase])