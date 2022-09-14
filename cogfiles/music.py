import discord, wavelink
from discord.ext import commands

class Music(commands.Cog, name="Music"):
    """Play music in a voice channel."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.track_context: dict[str, commands.Context] = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Start the task for connecting to the Lavalink nodes."""

        self.bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Connect to the Lavalink nodes."""
        
        await self.bot.wait_until_ready()
        await wavelink.NodePool.create_node(bot=self.bot, host="lavalink.oops.wtf", port=2000, password="www.freelavalink.ga")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        """Event fired when a node has finished connecting."""
        
        print(f'Node: <{node.identifier}> is ready!')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Disconnect the current voice client if the bot disconnects from a voice channel."""
        
        if member == self.bot.user and before.channel is not None and after.channel is None:
            vc = wavelink.NodePool.get_node().get_player(member.guild)
            if vc:
                await vc.disconnect()

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, vc: wavelink.Player, track: wavelink.YouTubeTrack):
        """Display the currently playing track."""
        
        context = self.track_context[track.id]
        await context.send(embed=discord.Embed(title="Now Playing", url=vc.source.uri, description=f"{vc.source.title} by {vc.source.author}"))
        del self.track_context[track.id]
    
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, vc: wavelink.Player, track: wavelink.YouTubeTrack, reason):
        """Play the next track in the queue once the current song ends, if there is one."""
        
        await vc.stop()
        if vc.queue.is_empty:
            return
        
        await vc.play(await vc.queue.get_wait())
    
    @commands.command(aliases=["p"])
    async def play(self, context: commands.Context, *, search: wavelink.YouTubeTrack):
        """Play or queue a track with the given search query."""

        #If not connected, connect to the voice channel.
        vc: wavelink.Player = context.voice_client
        if not context.voice_client:
            vc = await context.author.voice.channel.connect(cls=wavelink.Player)
            
        self.track_context[search.id] = context
        if vc.is_playing() or vc.is_paused():
            await vc.queue.put_wait(search)
            await context.send(embed=discord.Embed(title="Queued", url=search.uri, description=f"{search.title} by {search.author}"))
        else:
            await vc.play(search)
        
    
    @commands.command()
    async def stop(self, context: commands.Context):
        """Stop the currently playing track, if there is one."""
        
        vc: wavelink.Player = context.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            await vc.stop()
    
    @commands.command()
    async def pause(self, context: commands.Context):
        """Pause the currently playing track, if there is one."""
        
        vc: wavelink.Player = context.voice_client
        if vc and vc.is_playing():
            await vc.pause()
    
    @commands.command()
    async def resume(self, context: commands.Context):
        """Resume the currently paused track, if there is one."""
        
        vc: wavelink.Player = context.voice_client
        if vc and vc.is_paused():
            await vc.resume()
    
    @commands.command()
    async def skip(self, context: commands.Context):
        """Skips the current track, if there is one."""
        
        vc: wavelink.Player = context.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            await self.on_wavelink_track_end(vc, vc.track, None)
    
    @commands.command(aliases=["dc", "fuckoff"])
    async def disconnect(self, context: commands.Context):
        """Disconnect the player from the current voice channel, if there is one."""
        
        vc: wavelink.Player = context.voice_client
        if vc:
            await vc.disconnect()