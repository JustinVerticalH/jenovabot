import random

import discord
from discord import app_commands
from discord.ext import commands


class Polling(commands.Cog, name="Polling"):
    """Post a question with options to vote on."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command()
    async def yesorno(self, interaction: discord.Interaction, question: str):
        """Ask a yes or no question."""
        await interaction.response.send_message(f"> {question} \nYes or no?")
        poll_message = await interaction.original_response()
        await poll_message.add_reaction("✅")
        await poll_message.add_reaction("❌")
    
    @app_commands.command(name="8ball")
    async def eightball(self, interaction: discord.Interaction, question: str):
        """Responds to the user's question with a random positive or negative answer."""
        positive_choices = ["Yes", "Yep", "Absolutely", "Definitely"]
        negative_choices = ["No", "Nope", "Absolutely not", "Definitely not"]
        response = random.choice([random.choice(positive_choices), random.choice(negative_choices)])
        await interaction.response.send_message(f"> {question} \n{response}")