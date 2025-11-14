import discord
import re

from dataclasses import dataclass, field
from discord import app_commands
from discord.ext import commands
from ioutils import JsonSerializable, RandomColorEmbed, write_json, initialize_from_json


@dataclass(frozen=True, order=True)
class ReactionRole(JsonSerializable):
    """Data associated with a reaction role."""
    channel: discord.TextChannel = field(compare=False)
    message: discord.Message = field(compare=False)
    role: discord.Role = field()
    emoji: discord.PartialEmoji = field(compare=False)

    def to_json(self) -> dict[str, int | str]:
        """Convert the current ReactionRole object to a JSON string."""
        return {
            "message_id": self.message.id,
            "channel_id": self.channel.id,
            "role_id": self.role.id,
            "emoji": str(self.emoji)
        }

    @staticmethod
    async def from_json(bot: commands.Bot, json_obj: dict[str, int | str]):
        """Convert a JSON dictionary to a ReactionRole object."""
        channel = await bot.fetch_channel(json_obj["channel_id"])
        
        if channel is not None:
            message = await channel.fetch_message(json_obj["message_id"])
            role = channel.guild.get_role(json_obj["role_id"])
            emoji = discord.PartialEmoji.from_str(json_obj["emoji"])
            return ReactionRole(channel, message, role, emoji)

@app_commands.guild_only()
class ReactionRoles(commands.GroupCog, name="reactionrole"):
    """Manage ping roles through message reactions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reactionroles: dict[int, set[ReactionRole]] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize the list of reaction roles in memory."""
        await initialize_from_json(self.bot, ReactionRole, self.reactionroles, "reaction_roles")
    
    @app_commands.command()
    @app_commands.rename(emoji_str="emoji")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add(self, interaction: discord.Interaction, role: discord.Role, emoji_str: str, message_link: str | None):
        """Attaches a reaction role to a message. If no message is provided, the bot sends its own message.
        When a user reacts to the message with the given emoji, they will receive the role."""
        emoji = discord.PartialEmoji.from_str(emoji_str)

        if message_link is None:
            channel = interaction.channel
            message = await channel.send(f"React with {emoji_str} for the {role.mention} role!")
            message.activity = None
        else:
            regex_searches = re.search("(\d+)\/(\d+)$", message_link)
            try:
                channel_id = regex_searches.group(1)
                message_id = regex_searches.group(2)
                channel = await interaction.guild.fetch_channel(int(channel_id))
                message = await channel.fetch_message(int(message_id))
            except (discord.errors.HTTPException, AttributeError):
                return await interaction.response.send_message("Could not find the given message.", ephemeral=True)

        try:
            await message.add_reaction(emoji)
        except discord.errors.HTTPException as e:
            return await interaction.response.send_message("Could not use the given emoji. Make sure that this bot shares a server with the emoji.", ephemeral=True)

        new_reactionrole = ReactionRole(channel, message, role, emoji)

        # If there already exists a reaction role for this role, remove it and replace it with the new one
        old_reactionrole = next((reactionrole for reactionrole in self.reactionroles[interaction.guild.id] if reactionrole.role == new_reactionrole.role), None)
        self.reactionroles[interaction.guild.id].discard(old_reactionrole)
        self.reactionroles[interaction.guild.id].add(new_reactionrole)
        write_json(interaction.guild.id, "reaction_roles", value=[reactionrole.to_json() for reactionrole in self.reactionroles[interaction.guild.id]])

        embed = RandomColorEmbed(title="Reaction Role", description=f"React to this message with {emoji} to get the {role.mention} role: {message.jump_url}")
        if old_reactionrole is not None:
            embed.description += f"\nThis command replaced an existing reaction role for {role.mention} at {old_reactionrole.message.jump_url}"
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove(self, interaction: discord.Interaction, role: discord.Role):
        "Removes a reaction role message."
        old_reactionrole = next((reactionrole for reactionrole in self.reactionroles[interaction.guild.id] if reactionrole.role == role), None)
        if old_reactionrole is None:
            return await interaction.response.send_message("Could not find a reaction role for that role.", ephemeral=True)
        
        await old_reactionrole.message.remove_reaction(old_reactionrole.emoji, self.bot.user)
        self.reactionroles[interaction.guild.id].discard(old_reactionrole)
        write_json(interaction.guild.id, "reaction_roles", value=[reactionrole.to_json() for reactionrole in self.reactionroles[interaction.guild.id]])

        embed = RandomColorEmbed(title="Reaction Role Removed", description=f"\nThe reaction role for {role.mention} at {old_reactionrole.message.jump_url} has been removed.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    async def list(self, interaction: discord.Interaction):
        "Lists all reaction roles in this server."
        if interaction.guild.id not in self.reactionroles or len(self.reactionroles[interaction.guild.id]) == 0:
            return await interaction.response.send_message("There are no reaction roles in this server.", ephemeral=True)
        
        description = "\n".join(f"{reactionrole.role.mention} with {reactionrole.emoji} at {reactionrole.message.jump_url}" for reactionrole in sorted(self.reactionroles[interaction.guild.id], key=lambda rr: rr.role.name.lower()))
        embed = RandomColorEmbed(title="Reaction Roles", description=description)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @add.error
    @remove.error
    async def permissions_or_channel_fail(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handles errors for the given command (insufficient permissions, etc)."""
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You need the Manage Server permission to use this command.", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Called when a message has a reaction added. 
        This is called regardless of the state of the internal message cache, for example with old messages."""
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role = self.get_role(payload)

        if role is None:
            return
        if member.bot:
            return

        try:
            await member.add_roles(role)
        except discord.errors.Forbidden:
            await member.send(f"I do not have permission to assign you the **{role.name}** role in **{guild.name}**.\nMake sure that I have the Manage Roles permission and that my highest role is above the **{role.name}** role.")
            return

        await member.send(f"You now have the **{role.name}** role in **{guild.name}**.")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Called when a message has a reaction removed. 
        This is called regardless of the state of the internal message cache, for example with old messages."""
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role = self.get_role(payload)

        if role is None:
            return
        if member.bot:
            return

        try:
            await member.remove_roles(role)
        except discord.errors.Forbidden:
            await member.send(f"I do not have permission to remove the **{role.name}** role in **{guild.name}**.\nMake sure that I have the Manage Roles permission and that my highest role is above the **{role.name}** role.")
            return

        await member.send(f"You no longer have the **{role.name}** role in **{guild.name}**.")
    
    def get_role(self, payload: discord.RawReactionActionEvent) -> discord.Role | None:
        """Gets the role that should be given/removed to the user on a given reaction.
        Returns None if the reaction does not correspond to any reaction role."""
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member.bot or all(reactionrole.message.id != payload.message_id for reactionrole in self.reactionroles[payload.guild_id]):
            return None
        return next((reactionrole.role for reactionrole in self.reactionroles[payload.guild_id] if reactionrole.message.id == payload.message_id and reactionrole.emoji == payload.emoji), None)
