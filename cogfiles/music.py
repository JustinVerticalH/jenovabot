import discord, os, wavelink

from ioutils import RandomColorEmbed
from discord.ext import commands

SKIPPING = object()
LAVALINK_HOST = os.getenv("LAVALINK_HOST")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT"))
LAVALINK_PASS = os.getenv("LAVALINK_PASS")

class Music(commands.Cog, name="Music"):
    """Play music in a voice channel."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.track_context: dict[str, commands.Context] = {}

        self.looping: dict[int, bool] = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Start the task for connecting to the Lavalink nodes."""

        self.looping = {guild.id: False for guild in self.bot.guilds}
        self.bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Connect to the Lavalink nodes."""
        
        await self.bot.wait_until_ready()
        await wavelink.NodePool.create_node(bot=self.bot, host=LAVALINK_HOST, port=LAVALINK_PORT, password=LAVALINK_PASS)

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
    async def on_wavelink_track_start(self, vc: wavelink.Player, track: wavelink.Track):
        """Display the currently playing track."""
        
        now_playing_embed = RandomColorEmbed(title="Now Playing", url=track.uri, description=f"{track.title} by {track.author}")
        if isinstance(track, wavelink.YouTubeTrack):
            now_playing_embed.set_thumbnail(url=track.thumbnail)

        context = self.track_context[track.id]
        await context.send(embed=now_playing_embed)
        del self.track_context[track.id]
    
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, vc: wavelink.Player, track: wavelink.Track, reason):
        """Play the next track in the queue once the current song ends, if there is one."""
        
        await vc.stop()
        if self.looping[vc.guild.id] and reason != SKIPPING:
            await vc.play(track)
            return
        if vc.queue.is_empty:
            return
        
        await vc.play(await vc.queue.get_wait())
    
    @commands.command(aliases=["q"])
    async def queue(self, context: commands.Context):
        """Show the current state of the queue."""

        if self.looping[context.guild.id]:
            return

        vc: wavelink.Player = context.voice_client
        if not vc:
            return
        
        queue_track_list = RandomColorEmbed(
            title="Queue",
            description='\n'.join([f"{i+1}. **{track.title}** by {track.author}" for i, track in enumerate(vc.queue)[:10]])
        )
        if len(vc.queue) > 10:
            queue_track_list.description += "\n..."
        await context.send(embed=queue_track_list)
    
    @commands.command()
    async def loop(self, context: commands.Context):
        self.looping[context.guild.id] = not self.looping[context.guild.id]
        await context.send(f"Loop is now {'enabled' if self.looping else 'disabled'}.")
    
    @commands.command(aliases=["p"])
    async def play(self, context: commands.Context, *, search: wavelink.YouTubeTrack):
        """Play or queue a track with the given search query."""

        #If not connected, connect to the voice channel.
        vc: wavelink.Player = context.voice_client or await context.author.voice.channel.connect(cls=wavelink.Player)
            
        self.track_context[search.id] = context
        if vc.is_playing() or vc.is_paused():
            await vc.queue.put_wait(search)
            await context.send(embed=RandomColorEmbed(title="Queued", url=search.uri, description=f"{search.title} by {search.author}").set_thumbnail(url=search.thumbnail))
        else:
            await vc.play(search)
        
    @commands.command(aliases=["np"])
    async def nowplaying(self, context: commands.Context):
        """Show the currently playing track, if there is one."""

        vc: wavelink.Player = context.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            track = vc.source
            
            now_playing_embed = RandomColorEmbed(title="Now Playing", url=track.uri, description=f"{track.title} by {track.author}")
            if isinstance(track, wavelink.YouTubeTrack):
                now_playing_embed.set_thumbnail(url=track.thumbnail)
            
            await context.send(embed=now_playing_embed)
        else:
            await context.send("No track is currently playing.")
    
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
            await self.on_wavelink_track_end(vc, vc.track, SKIPPING)
    
    @commands.command(aliases=["dc"])
    async def disconnect(self, context: commands.Context):
        """Disconnect the player from the current voice channel, if there is one."""
        
        vc: wavelink.Player = context.voice_client
        if vc:
            await vc.disconnect()