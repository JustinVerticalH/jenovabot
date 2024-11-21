from ioutils import RandomColorEmbed

import discord
from discord import app_commands
from discord.ext import commands


class StreamPause(commands.Cog, name="Stream Pause"):
    """Set up a message to react to when taking a break during a stream."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.streampause_data: dict[str, discord.Message | discord.Member | set[discord.Member]] = None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Keep track of members entering or leaving a voice channel during a streampause, if there is one."""       
        if self.streampause_data is not None:
            voice_channel = before.channel if after.channel is None else after.channel if before.channel is None else None

            # Fetching the message again to get the most updated state of the message
            await self.streampause_data["message"].fetch()

            await self.attempt_to_finish_streampause(member, voice_channel)

    @app_commands.command()
    async def streampause(self, interaction: discord.Interaction):
        """Set up a streampause message for voice channel members to react to."""

        if interaction.user.voice is None:
            return await interaction.response.send_message("This command is only usable inside a voice channel.")

        if self.streampause_data is not None:
            await self.streampause_data["message"].delete()
            self.streampause_data = None

        embed = RandomColorEmbed(
            title = "Click the button when you're all set!"
        )
        view = discord.ui.View()
        view.add_item(ReturnButton(self))
        view.add_item(UnReturnButton(self))
        view.add_item(CancelButton(self))
        view.add_item(ExplanationButton())
        await interaction.response.send_message(embed=embed, view=view)

        message = await interaction.original_response()
        self.streampause_data = {
            "message": message,
            "author": interaction.user,
            "reacted_users": set()
        }
        
        try:
            await message.pin()
        except Exception:
            pass

        await self.update_message(message, interaction.user.voice.channel)

    async def attempt_to_finish_streampause(self, user: discord.Member, voice_channel: discord.VoiceChannel | None):
        """Attempt to end a streampause upon a change to either reactions or voice channel members."""
        if user.bot or voice_channel is None:
            return

        message = self.streampause_data["message"]
        await self.update_message(message, voice_channel)

        vc_members = StreamPause.get_non_bot_users(voice_channel)

        if self.streampause_data["reacted_users"] & vc_members == vc_members:
            original_author = self.streampause_data["author"]
            await message.channel.send(f"{original_author.mention} Everyone's here!")

            await message.delete()
            self.streampause_data = None

    async def update_message(self, message: discord.Message, voice_channel: discord.VoiceChannel | None):
        """Check the reacted status of each member in the voice channel and update the streampause message to reflect the status."""
        if voice_channel is None:
            return

        reacted_members = "**Back:**"
        not_reacted_members = "**Not Back:**"

        vc_members = StreamPause.get_non_bot_users(voice_channel)

        for member in vc_members:
            if member in self.streampause_data["reacted_users"]:
                reacted_members += f"\n{member.mention}"
            else:
                not_reacted_members += f"\n{member.mention}"

        embed = RandomColorEmbed(title=message.embeds[0].title, colour=message.embeds[0].colour, description=f"{reacted_members}\n\n{not_reacted_members}")
        await message.edit(embed=embed)

    @staticmethod
    def get_non_bot_users(voice_channel: discord.VoiceChannel) -> set[discord.Member]:
        return set(member for member in voice_channel.members if not member.bot)

class ReturnButton(discord.ui.Button):
    def __init__(self, streampause: StreamPause):
        super().__init__()
        self.streampause = streampause
        self.emoji = "👍"
        self.label = "I'm back!"

    async def callback(self, interaction: discord.Interaction):
        if interaction.user not in self.streampause.streampause_data["reacted_users"]:
            self.streampause.streampause_data["reacted_users"].add(interaction.user)
            await self.streampause.attempt_to_finish_streampause(interaction.user, interaction.user.voice.channel)
            await interaction.response.send_message("Welcome back!", ephemeral=True)
        else:
            await interaction.response.defer()

class UnReturnButton(discord.ui.Button):
    def __init__(self, streampause: StreamPause):
        super().__init__()
        self.streampause = streampause
        self.emoji = "👎"
        self.label = "I'm not back!"

    async def callback(self, interaction: discord.Interaction):
        if interaction.user in self.streampause.streampause_data["reacted_users"]:
            self.streampause.streampause_data["reacted_users"].discard(interaction.user)
            await self.streampause.attempt_to_finish_streampause(interaction.user, interaction.user.voice.channel)
            await interaction.response.send_message("Come back soon!", ephemeral=True)
        else:
            await interaction.response.defer()

class CancelButton(discord.ui.Button):
    def __init__(self, streampause: StreamPause):
        super().__init__()
        self.label = "Cancel"
        self.streampause = streampause
        self.style = discord.ButtonStyle.red

    async def callback(self, interaction: discord.Interaction):
        if interaction.user == self.streampause.streampause_data["author"]:
            await self.streampause.streampause_data["message"].delete()
            self.streampause.streampause_data = None
            await interaction.response.send_message("Streampause cancelled.")
        else:
            await interaction.response.defer()

class ExplanationButton(discord.ui.Button):
    def __init__(self):
        super().__init__()
        self.label = "What is this?"
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("This command is for when we want to take a break during a stream. " +
                                                "Take an AFK break, and when you come back, click the 👍 button. " +
                                                "When everyone has come back and clicked, the message will delete itself " +
                                                "and the person who used the command will be pinged.", ephemeral=True)        