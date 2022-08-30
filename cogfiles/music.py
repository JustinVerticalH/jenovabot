import discord, os, wavelink
from discord.ext import commands

class Music(commands.Cog, name="Music"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        # Connect to our Lavalink nodes.
        await self.bot.wait_until_ready()
        await wavelink.NodePool.create_node(bot=self.bot, host="lavalink.hatry4.xyz", port=10424, password="youshallpasslol")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        """Event fired when a node has finished connecting."""
        print(f'Node: <{node.identifier}> is ready!')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        print("Listener in music.py")
        """A listener for keeping track of members entering or leaving a voice channel during a streampause, if there is one."""
        if member == self.bot.user and after.channel is None:
            await wavelink.NodePool.get_node().get_player(member.guild).disconnect()

    @commands.command()
    async def play(self, context: commands.Context, *, search: wavelink.YouTubeTrack):
        """Play a song with the given search query."""

        #If not connected, connect to our voice channel.
        if not context.voice_client:
            vc: wavelink.Player = await context.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc = context.voice_client

        await vc.play(search)
    
    #@commands.command()
    #async def stop(self, context: commands.Context):

