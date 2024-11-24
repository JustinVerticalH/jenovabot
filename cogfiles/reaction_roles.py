import discord, json
from dataclasses import dataclass, field
from discord import app_commands
from discord.ext import commands
from ioutils import read_json, write_json


@dataclass(frozen=True, order=True)
class ReactionRole:
    """Data associated with a reaction role."""
    channel: discord.TextChannel = field(compare=False)
    message: discord.Message = field()
    role: discord.Role = field()
    emoji: str = field()

    def to_json(self) -> dict[str, int | str]:
        """Convert the current reminder object to a JSON string."""
        return {
            "message_id": self.message.id,
            "channel_id": self.channel.id,
            "role_id": self.role.id,
            "emoji": self.emoji
        }

    @staticmethod
    async def from_json(bot: commands.Bot, json_obj: dict[str, int | str]):
        """Convert a JSON dictionary to a Reminder object."""
        channel = await bot.fetch_channel(json_obj["channel_id"])
        
        if channel is not None:
            message = await channel.fetch_message(json_obj["message_id"])
            role = next(role for role in await channel.guild.fetch_roles() if role.id == int(json_obj["role_id"]))
            emoji = json_obj["emoji"]
            return ReactionRole(channel, message, role, emoji)


class ReactionRoles(commands.Cog, name="Reaction Roles"):
    """Manage ping roles through message reactions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reactionroles: dict[int, set[ReactionRole]] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            if read_json(guild.id, "reaction_roles") is None:
                write_json(guild.id, "reaction_roles", value={})
            try:
                self.reactionroles[guild.id] = {await ReactionRole.from_json(self.bot, json_str) for json_str in read_json(guild.id, "reaction_roles")}
            except json.JSONDecodeError as e:
                print(e)
    
    @app_commands.command()
    @app_commands.rename(emoji_str="emoji")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reactionrole(self, interaction: discord.Interaction, role: discord.Role, emoji_str: str):
        "Set up a reaction role message."
        #emoji = discord.PartialEmoji.from_str(emoji_str)
        emoji = emoji_str

        await interaction.response.defer()

        message = await interaction.followup.send(f"React here for the {role.name} role:\n> {emoji} {role.name}")
        await message.add_reaction(emoji)

        reactionrole = ReactionRole(interaction.channel, message, role, emoji)
        self.reactionroles[interaction.guild.id].add(reactionrole)
        write_json(interaction.guild.id, "reaction_roles", value=[reactionrole.to_json() for reactionrole in self.reactionroles[interaction.guild.id]])
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member.bot or all(reactionrole.message.id != payload.message_id for reactionrole in self.reactionroles[payload.guild_id]):
            return
        
        role = next(reactionrole.role for reactionrole in self.reactionroles[payload.guild_id] if reactionrole.emoji == str(payload.emoji))

        await member.add_roles(role)

        if member.dm_channel is None:
            await member.create_dm()
        await member.dm_channel.send(f"You now have the {role.name} role in {guild.name}.")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member.bot or all(reactionrole.message.id != payload.message_id for reactionrole in self.reactionroles[payload.guild_id]):
            return
        
        role = next(reactionrole.role for reactionrole in self.reactionroles[payload.guild_id] if reactionrole.emoji == str(payload.emoji))

        await member.remove_roles(role)

        if member.dm_channel is None:
            await member.create_dm()
        await member.dm_channel.send(f"You no longer have the {role.name} role in {guild.name}.")
    