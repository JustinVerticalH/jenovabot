from typing import Optional
from ioutils import RandomColorEmbed

import discord
from discord.ext import commands


class StreamPause(commands.Cog, name="Stream Pause"):
    """Set up a message to react to when taking a break during a stream."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.streampause_data: dict[str, discord.Message | discord.Member] = None
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        """Keep track of reactions added to a streampause message, if there is one."""

        if self.streampause_data is not None:
            await self.attempt_to_finish_streampause(reaction, user, user.voice.channel if user.voice else None)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.Member):
        """Keep track of reactions added to a streampause message, if there is one."""

        if self.streampause_data is not None:
            await self.attempt_to_finish_streampause(reaction, user, user.voice.channel if user.voice else None)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Keep track of members entering or leaving a voice channel during a streampause, if there is one."""
        
        if self.streampause_data is not None:
            voice_channel = before.channel if after.channel is None else after.channel if before.channel is None else None

            # Fetching the message again to get the most updated state of the message
            message = await self.streampause_data["message"].fetch()
            reaction = discord.utils.get(message.reactions, emoji="👍")

            await self.attempt_to_finish_streampause(reaction, member, voice_channel)

    @commands.command()
    async def streampause(self, context: commands.Context):
        """Set up a streampause message for voice channel members to react to."""
        
        if context.author.voice is None:
            await context.send("This command is only usable inside a voice channel.")
            return

        embed = RandomColorEmbed(
            title = "React with 👍 when you're all set!"
        )
        message = await context.send(embed=embed)


        self.streampause_data = {
            "message": message,
            "author": context.author
        }

        await message.add_reaction("👍")
        await message.pin()
        await self.update_message(message, context.author.voice.channel)

    async def attempt_to_finish_streampause(self, reaction: discord.Reaction, user: discord.Member, voice_channel: Optional[discord.VoiceChannel]):
        """Attempt to end a streampause upon a change to either reactions or voice channel members."""
        
        if user.bot or reaction.message != self.streampause_data["message"] or reaction.emoji != "👍" or voice_channel is None:
            return

        await self.update_message(reaction.message, voice_channel)

        reacted_members = {user async for user in reaction.users()}
        vc_members = set(voice_channel.members)

        if reacted_members & vc_members == vc_members:
            original_author = self.streampause_data["author"]
            await reaction.message.channel.send(f"{original_author.mention} Everyone's here!")

            await reaction.message.delete()
            self.streampause_data = None

    async def update_message(self, message: discord.Message, voice_channel: Optional[discord.VoiceChannel]):
        if voice_channel is not None:
            members = voice_channel.members

            reacted_list = []
            if message.reactions:
                reacted_list = [user async for user in message.reactions[0].users()]

            reacted_members = "**Reacted:**"
            not_reacted_members = "**Not Reacted:**"

            for member in members:
                if not member.bot:
                    if member in reacted_list:
                        reacted_members += f"\n{member.name}"
                    else:
                        not_reacted_members += f"\n{member.name}"
        
            embed = RandomColorEmbed(title=message.embeds[0].title, colour=message.embeds[0].colour, description=f"{reacted_members}\n\n{not_reacted_members}")
            await message.edit(embed=embed)