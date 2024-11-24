import discord
from discord import app_commands
from discord.ext import commands

class ReactionRoles(commands.Cog, name="Reaction Roles"):
    """Manage ping roles through message reactions."""
    
    

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reactionroles: dict[discord.Message, discord.Role] = {}
    
    @app_commands.command()
    @app_commands.rename(emoji_str="emoji")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reactionrole(self, interaction: discord.Interaction, role: discord.Role, emoji_str: str):
        "Set up a reaction role message."
        emoji = discord.PartialEmoji.from_str(emoji_str)

        await interaction.response.defer()

        message = await interaction.followup.send(f"React here for the {role.name} role:\n> {emoji} {role.name}")
        await message.add_reaction(emoji)

        self.reactionroles[message] = role
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        if user.bot or reaction.message not in self.reactionroles:
            return
        
        role = self.reactionroles[reaction.message]

        await user.add_roles(role)

        if user.dm_channel is None:
            await user.create_dm()
        await user.dm_channel.send(f"You now have the {role.name} role.")
    
    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.Member):
        if user.bot or reaction.message not in self.reactionroles:
            return
        
        role = self.reactionroles[reaction.message]
        
        await user.remove_roles(role)
        
        if user.dm_channel is None:
            await user.create_dm()
        await user.dm_channel.send(f"You no longer have the {role.name} role.")