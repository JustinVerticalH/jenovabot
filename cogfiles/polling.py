import discord
from discord.ext import commands

class Polling(commands.Cog, name="Polling"):
    """Post a question with options to vote on."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command()
    async def yesorno(self, context: commands.Context):
        """Ask a yes or no question."""
        
        poll_message = await context.send("Yes or No?")
        await poll_message.add_reaction("✅")
        await poll_message.add_reaction("❌")