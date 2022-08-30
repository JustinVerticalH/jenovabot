from typing import Optional

import discord
from discord.ext import commands


class StreamPause(commands.Cog, name="Stream Pause"):
    """A Cog to handle setting up a message to react to when taking a break during a stream."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.streampause_data: dict[str, discord.Message | discord.Member] = None
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        """A listener for keeping track of reactions added to a streampause message, if there is one."""

        if self.streampause_data is not None:
            await self.attempt_to_finish_streampause(reaction, user, user.voice.channel if user.voice else None)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """A listener for keeping track of members entering or leaving a voice channel during a streampause, if there is one."""
        
        if self.streampause_data is not None:
            voice_channel = before.channel if after.channel is None else after.channel if before.channel is None else None
            reaction = discord.utils.get(self.streampause_data["message"].reactions, emoji="👍")

            await self.attempt_to_finish_streampause(reaction, member, voice_channel)

    @commands.command()
    async def streampause(self, context: commands.Context):
        """A command for setting up a streampause message for voice channel members to react to."""
        
        if context.author.voice is None:
            await context.send("This command is only usable inside a voice channel.")
            return

        message = await context.send("React with 👍 when you're all set!")

        self.streampause_data = {
            "message": message,
            "author": context.author
        }

        await message.add_reaction("👍")

    async def attempt_to_finish_streampause(self, reaction: discord.Reaction, user: discord.Member, voice_channel: Optional[discord.VoiceChannel]):
        """A helper method for attempting to end a streampause upon a change to either reactions or voice channel members."""
        
        if user == self.bot or reaction.message != self.streampause_data["message"] or reaction.emoji != "👍" or voice_channel is None:
            return

        reacted_members = set(await reaction.users().flatten())
        vc_members = set(voice_channel.members)

        if reacted_members & vc_members == vc_members:
            original_author = self.streampause_data["author"]
            await reaction.message.channel.send(f"{original_author.mention} Everyone's here!")

            await reaction.message.delete()
            self.streampause_data = None