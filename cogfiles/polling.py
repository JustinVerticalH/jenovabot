import random
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
    
    @commands.command(aliases=["8ball"])
    async def eightball(self, context: commands.Context, *, question: str):
        """Responds to the user's question with a random positive or negative answer."""
        positive_choices = ["Yes", "Yep", "Absolutely", "Definitely"]
        negative_choices = ["No", "Nope", "Absolutely not", "Definitely not"]
        response = random.choice([random.choice(positive_choices), random.choice(negative_choices)])
        await context.send(f"> {question} \n {response}")

    @commands.command()
    async def youonlyhaveoneshot(self, context: commands.Context):
        """If you return the sun, Niko may never return home; if you destroy the sun, this world will cease to be."""   
        lightbulb = "<:lightbulb:1022745556675731528>"
        nikopensive = "<:nikopensive:1022745573759127583>"
        
        choice_message = await context.send(f"What's the right thing to do?\n>>> {lightbulb} Return the sun\n{nikopensive} Return home")
        await choice_message.add_reaction(lightbulb)
        await choice_message.add_reaction(nikopensive)
