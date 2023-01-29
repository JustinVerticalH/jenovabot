"""
This example cog demonstrates basic usage of Lavalink.py, using the DefaultPlayer.
As this example primarily showcases usage in conjunction with discord.py, you will need to make
modifications as necessary for use with another Discord library.
Usage of this cog requires Python 3.6 or higher due to the use of f-strings.
Compatibility with Python 3.5 should be possible if f-strings are removed.
"""
import os, re

import discord
import lavalink

from datetime import timedelta
from discord.ext import commands

from ioutils import RandomColorEmbed

url_rx = re.compile(r"https?://(?:www\.)?.+")

LAVALINK_HOST = os.getenv("LAVALINK_HOST")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT"))
LAVALINK_PASS = os.getenv("LAVALINK_PASS")

class LavalinkVoiceClient(discord.VoiceClient):
    """
    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, bot: commands.Bot, channel: discord.abc.Connectable):
        self.client = bot
        self.channel = channel
        # ensure a client already exists
        if hasattr(self.client, "lavalink"):
            self.lavalink = self.client.lavalink
        else:
            self.client.lavalink = lavalink.Client(bot.user.id)
            self.client.lavalink.add_node(LAVALINK_HOST, LAVALINK_PORT, LAVALINK_PASS, "us")
            self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to voice_update_handler
        lavalink_data = {
            "t": "VOICE_SERVER_UPDATE",
            "d": data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        # the data needs to be transformed before being handed down to voice_update_handler
        lavalink_data = {
            "t": "VOICE_STATE_UPDATE",
            "d": data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        """Connect the bot to the voice channel and create a player_manager if it doesn"t exist yet."""

        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        """Handles the disconnect. Cleans up running player and leaves the voice client."""
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        self.cleanup()


class Music(commands.Cog, name="Music"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not hasattr(self.bot, "lavalink"):  # This ensures the client isn"t overwritten during cog reloads.
            self.bot.lavalink = lavalink.Client(self.bot.user.id)
            self.bot.lavalink.add_node(LAVALINK_HOST, LAVALINK_PORT, LAVALINK_PASS, "us")  # Host, Port, Password, Region

        self.bot.lavalink.add_event_hooks(self)
        

    def cog_unload(self):
        """ Cog unload handler. This removes any event hooks that were registered. """

        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, context: commands.Context):
        """ Command before-invoke handler. """

        guild_check = context.guild is not None
        #  This is essentially the same as `@commands.guild_only()`
        #  except it saves us repeating ourselves (and also a few lines).

        if guild_check:
            await self.ensure_voice(context)
            #  Ensure that the bot and command author share a mutual voice channel.

        return guild_check

    async def cog_command_error(self, context: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            await context.send(error.original)
            # The above handles errors thrown in this cog and shows them to the user.
            # This shouldn"t be a problem as the only errors thrown in this cog are from `ensure_voice`
            # which contain a reason string, such as "Join a voice channel" etc. You can modify the above
            # if you want to do things differently.

    async def ensure_voice(self, context):
        """This check ensures that the bot and command author are in the same voice channel."""

        player = self.bot.lavalink.player_manager.create(context.guild.id)
        # Create returns a player if one exists, otherwise creates.
        # This line is important because it ensures that a player always exists for a guild.

        # Most people might consider this a waste of resources for guilds that aren't playing, but this is
        # the easiest and simplest way of ensuring players are created.

        # These are commands that require the bot to join a voice channel (i.e. initiating playback).
        # Commands such as volume/skip etc don"t require the bot to be in a voice channel so don"t need listing here.
        should_connect = context.command.name in ("play",)

        if not context.author.voice or not context.author.voice.channel:
            # Our cog_command_error handler catches this and sends it to the voice channel.
            # Exceptions allow us to "short-circuit" command invocation via checks so the execution state of the command goes no further.
            raise commands.CommandInvokeError("Join a voice channel first.")

        v_client = context.voice_client
        if not v_client:
            if not should_connect:
                raise commands.CommandInvokeError("Not connected.")

            permissions = context.author.voice.channel.permissions_for(context.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise commands.CommandInvokeError("I need the `CONNECT` and `SPEAK` permissions.")

            player.store("channel", context.channel.id)
            await context.author.voice.channel.connect(cls=LavalinkVoiceClient)
        else:
            if v_client.channel.id != context.author.voice.channel.id:
                raise commands.CommandInvokeError("You need to be in my voice channel.")

    @lavalink.listener(lavalink.events.QueueEndEvent)
    async def on_queue_end(self, event: lavalink.events.QueueEndEvent):
        # When this track_hook receives a "QueueEndEvent" from lavalink.py, it indicates that there are no tracks left in the player"s queue.
        # To save on resources, we can tell the bot to disconnect from the voice channel.
        await self.cleanup(event.player)

    @lavalink.listener(lavalink.events.TrackStartEvent)
    async def on_track_start(self, event: lavalink.events.TrackStartEvent):
        """Send an embed with information about the starting track."""

        # If the current track is looping, don't send a message every time the looping track plays again.
        if event.player.loop == event.player.LOOP_SINGLE:
            return

        text_channel_id = event.player.fetch("channel")
        text_channel = await self.bot.fetch_channel(text_channel_id)

        embed = RandomColorEmbed(title="Track Started", description=f"[{event.track.title}]({event.track.uri})")

        video_thumbnail = f"https://img.youtube.com/vi/{event.track.identifier}/hqdefault.jpg"
        embed.set_thumbnail(url=video_thumbnail)

        await text_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Disconnect the current voice client if the bot disconnects from a voice channel."""
        
        if member == self.bot.user and before.channel is not None and after.channel is None:
            await self.cleanup(self.bot.lavalink.player_manager.get(before.channel.guild.id))

    @commands.command(aliases=["p"])
    async def play(self, context: commands.Context, *, query: str):
        """Searches and plays a song from a given query."""

        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(context.guild.id)
        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip("<>")

        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        # SoundCloud searching is possible by prefixing "scsearch:" instead.
        if not url_rx.match(query):
            query = f"ytsearch:{query}"

        # Get the results for the query from Lavalink.
        results = await player.node.get_tracks(query)

        # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
        # Alternatively, results.tracks could be an empty array if the query yielded no tracks.
        if not results or not results.tracks:
            return await context.send("Nothing found!")

        embed = RandomColorEmbed()

        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL)
        #   PLAYLIST_LOADED - direct URL to playlist)
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
        if results.load_type == "PLAYLIST_LOADED":
            tracks = results.tracks

            for track in tracks:
                # Add all of the tracks from the playlist to the queue.
                player.add(requester=context.author.id, track=track)

            embed.title = "Playlist Queued"
            embed.description = f"[{results.playlist_info.name}]({tracks[0].uri}) - {len(tracks)} tracks"

            video_thumbnail = f"https://img.youtube.com/vi/{tracks[0].identifier}/hqdefault.jpg"
            embed.set_thumbnail(url=video_thumbnail)

            await context.send(embed=embed)

        else:
            track = results.tracks[0]
            player.add(requester=context.author.id, track=track)

            if player.is_playing:
                # If the queue is currently empty, don't send a message about adding the track to the queue.
                # The on_track_start() listener will send a message about the song playing.

                embed.title = "Track Queued"
                embed.description = f"[{track.title}]({track.uri})"

                video_thumbnail = f"https://img.youtube.com/vi/{track.identifier}/hqdefault.jpg"
                embed.set_thumbnail(url=video_thumbnail)

                await context.send(embed=embed)

        # We don"t want to call .play() if the player is playing as that will effectively skip the current track.
        if not player.is_playing:
            await player.play()

    @commands.command(aliases=["dc"])
    async def disconnect(self, context: commands.Context):
        """Disconnects the player from the voice channel and clears its queue."""
        player = self.bot.lavalink.player_manager.get(context.guild.id)

        if not context.voice_client:
            # We can't disconnect, if we"re not connected.
            return await context.send("Not connected.")

        if not context.author.voice or (player.is_connected and context.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot may not disconnect the bot.
            return await context.send("You're not in my voice channel!")
        
        await self.cleanup(player)

    async def cleanup(self, player: lavalink.BasePlayer):
        guild = self.bot.get_guild(player.guild_id)
        voice_client = guild.voice_client

        # Clear the queue to ensure old tracks don't start playing when someone else queues something.
        player.queue.clear()
        # Stop the current track so Lavalink consumes less resources.
        await player.stop()
        # Disconnect from the voice channel.
        if voice_client is not None:
            await voice_client.disconnect(force=True)

    @commands.command(aliases=["s"])
    async def skip(self, context: commands.Context):
        """Skips the currently playing track. If there is another track in the queue, plays that next track."""

        player = self.bot.lavalink.player_manager.get(context.guild.id)

        if player.current is None:
            return await context.send("No track currently playing.")

        await player.skip()

    @commands.command(aliases=["q"])
    async def queue(self, context: commands.Context):
        """Lists the queue of tracks to play."""

        player = self.bot.lavalink.player_manager.get(context.guild.id)

        if player.current is None:
            return await context.send("No tracks currently queued.")

        track_list = [player.current, *player.queue]
        track_names = "\n".join([f"{i+1}. [{track.title}]({track.uri})" for i, track in enumerate(track_list)])

        embed = RandomColorEmbed(title="Queue", description=track_names)
        await context.send(embed=embed)

    @commands.command()
    async def pause(self, context: commands.Context):
        """Pauses the currently playing track, if any."""        

        player = self.bot.lavalink.player_manager.get(context.guild.id)

        if player.current is None:
            return await context.send("No track currently playing.")

        await player.set_pause(not player.paused)
        embed = RandomColorEmbed(title="Now Paused" if player.paused else "Now Resuming")
        await context.send(embed=embed)

    @commands.command()
    async def stop(self, context: commands.Context):
        
        player = self.bot.lavalink.player_manager.get(context.guild.id)

        if player.current is None:
            return await context.send("No track currently playing.")

        await player.stop()
        embed = RandomColorEmbed(title="Stopping")
        await context.send(embed=embed)

    @commands.command()
    async def volume(self, context: commands.Context, volume: int):
        """Sets the volume of the player between 0% and 1000%."""

        if not context.author.guild_permissions.manage_guild:
            volume = min(volume, 100)

        player = self.bot.lavalink.player_manager.get(context.guild.id)

        await player.set_volume(volume)
        embed = RandomColorEmbed(title=f"Volume: {volume}%")
        await context.send(embed=embed)

    @commands.command(aliases=["np"])
    async def nowplaying(self, context: commands.Context):
        """Displays the progress of the currently playing track."""

        player = self.bot.lavalink.player_manager.get(context.guild.id)
        track = player.current

        position = timedelta(seconds=player.position // 1000)
        duration = timedelta(seconds=track.duration // 1000)

        formatted_position = f"Progress: {position}/{duration}"        
        description = f"[{track.title}]({track.uri})\n{formatted_position}"

        embed = RandomColorEmbed(title="Currently Playing", description=description)
        await context.send(embed=embed)

    @commands.command()
    async def loop(self, context: commands.Context):
        """Toggles whether or not the current track is looping."""
        
        player = self.bot.lavalink.player_manager.get(context.guild.id)

        player.set_loop(player.LOOP_SINGLE if player.loop == player.LOOP_NONE else player.LOOP_NONE)
        embed = RandomColorEmbed(title=f"Looping {'On' if player.loop == player.LOOP_SINGLE else 'Off'}")
        await context.send(embed=embed)