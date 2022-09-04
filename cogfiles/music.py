import discord, wavelink
from discord.ext import commands

class Music(commands.Cog, name="Music"):
    """A Cog to handle playing music in a voice channel."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Start the task for connecting to the Lavalink nodes."""

        self.bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Connect to the Lavalink nodes."""
        await self.bot.wait_until_ready()
        await wavelink.NodePool.create_node(bot=self.bot, host="lavalink.hatry4.xyz", port=10424, password="youshallpasslol")

    # @commands.Cog.listener()
    # async def on_wavelink_node_ready(self, node: wavelink.Node):
    #     """Event fired when a node has finished connecting."""
    #     print(f'Node: <{node.identifier}> is ready!')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Disconnect the current voice client if the bot disconnects from a voice channel."""
        
        if member == self.bot.user and before.channel is not None and after.channel is None:
            vc = wavelink.NodePool.get_node().get_player(member.guild)
            if vc:
                await vc.disconnect()

    @commands.command(aliases=["p"])
    async def play(self, context: commands.Context, *, search: wavelink.YouTubeTrack):
        """Play a song with the given search query."""

        #If not connected, connect to our voice channel.
        vc: wavelink.Player = context.voice_client
        if not context.voice_client:
            vc = await context.author.voice.channel.connect(cls=wavelink.Player)
            
        await context.send(embed=discord.Embed().add_field(name="Now Playing", value=search))
        await vc.play(search)
    
    @commands.command()
    async def stop(self, context: commands.Context):
        """Stop the currently playing song, if there is one."""
        
        vc: wavelink.Player = context.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            await vc.stop()
    
    @commands.command()
    async def pause(self, context: commands.Context):
        """Pause the currently playing song, if there is one."""
        
        vc: wavelink.Player = context.voice_client
        if vc and vc.is_playing():
            await vc.pause()
    
    @commands.command()
    async def resume(self, context: commands.Context):
        """Resume the currently paused song, if there is one."""
        
        vc: wavelink.Player = context.voice_client
        if vc and vc.is_paused():
            await vc.resume()
    
    @commands.command(aliases=["dc", "fuckoff"])
    async def disconnect(self, context: commands.Context):
        """Disconnect the player from the current voice channel, if there is one."""
        
        vc: wavelink.Player = context.voice_client
        if vc:
            await vc.disconnect()
