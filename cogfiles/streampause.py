from typing import Optional
from ioutils import RandomColorEmbed

import discord
from discord import app_commands
from discord.ext import commands


class ExplanationButton(discord.ui.Button):
    def __init__(self):
        super().__init__()
        self.label = "What is this?"
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("This command is for when we want to take a break during a stream. " +
                                                "Take an AFK break, and when you come back, react to the message with 👍. " +
                                                "When everyone has returned and reacted, the message will delete itself " +
                                                "and the person who used the command will be pinged.", ephemeral=True)


class CancelButton(discord.ui.Button):
    def __init__(self, streampause_data: dict):
        super().__init__()
        self.label = "Cancel"
        self.streampause_data = streampause_data

    async def callback(self, interaction: discord.Interaction):
        await self.streampause_data["message"].delete()
        self.streampause_data = None
        await interaction.response.send_message("Streampause cancelled.", ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user == self.streampause_data["author"]


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

    @app_commands.command()
    async def streampause(self, interaction: discord.Interaction):
        """Set up a streampause message for voice channel members to react to."""

        if interaction.user.voice is None:
            await interaction.response.send_message("This command is only usable inside a voice channel.")
            return

        if self.streampause_data is not None:
            await self.streampause_data["message"].delete()
            self.streampause_data = None

        embed = RandomColorEmbed(
            title = "React with 👍 when you're all set!"
        )
        view = discord.ui.View()
        view.add_item(ExplanationButton())
        view.add_item(CancelButton(self.streampause_data))
        await interaction.response.send_message(embed=embed, view=view)

        message = await interaction.original_response()
        self.streampause_data = {
            "message": message,
            "author": interaction.user
        }

        await message.add_reaction("👍")
        
        try:
            await message.pin()
        except Exception:
            pass

        await self.update_message(message, interaction.user.voice.channel)

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
        """Check the reacted status of each member in the voice channel and update the streampause message to reflect the status."""
        if voice_channel is None:
            return

        members = voice_channel.members

        reacted_list = []
        if message.reactions:
            reacted_list = [user async for user in message.reactions[0].users() if not user.bot]

        reacted_members = "**Reacted:**"
        not_reacted_members = "**Not Reacted:**"

        for member in members:
            if member in reacted_list:
                reacted_members += f"\n{member.mention}"
            else:
                not_reacted_members += f"\n{member.mention}"

        embed = RandomColorEmbed(title=message.embeds[0].title, colour=message.embeds[0].colour, description=f"{reacted_members}\n\n{not_reacted_members}")
        await message.edit(embed=embed)