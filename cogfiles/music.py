import os, types

import discord
import wavelink

from datetime import timedelta
from discord.ext import commands

from ioutils import RandomColorEmbed

# Lavalink server version must be at or above version 4.0.5
# We can get Lavalink servers from https://lavalink.darrennathanael.com/NoSSL/lavalink-without-ssl/
LAVALINK_HOST = f"http://{os.getenv('LAVALINK_HOST')}:{os.getenv('LAVALINK_PORT')}"
LAVALINK_PASS = os.getenv("LAVALINK_PASS")

async def setup_hook(self):
    print(f"Lavalink Host: {LAVALINK_HOST}")
    
    nodes = [wavelink.Node(uri=LAVALINK_HOST, client=self, password=LAVALINK_PASS)]
    # cache_capacity is EXPERIMENTAL. Turn it off by passing None
    print(await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=None))

commands.Bot.setup_hook = setup_hook


class Music(commands.Cog, name="Music"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.node: wavelink.Node

        self.skipping_manually = False
    
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print("Node ready!")
        self.node = payload.node

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):        
        """Send an embed with information about the starting track."""

        # If the current track is looping, don't send a message every time the looping track plays again.
        if payload.player.queue.mode == wavelink.QueueMode.loop and not self.skipping_manually:
            return

        embed = RandomColorEmbed(title="Track Started", description=await self.format_track(payload.track))
        video_thumbnail = f"https://img.youtube.com/vi/{payload.player.current.identifier}/hqdefault.jpg"
        embed.set_thumbnail(url=video_thumbnail)

        channel = await self.bot.fetch_channel(payload.track.extras.channel_id)
        await channel.send(embed=embed)

        if self.skipping_manually:
            self.skipping_manually = False

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        if not payload.player or "manual_stop" in dict(payload.original.extras):
            return

        if payload.player.queue.is_empty and (self.skipping_manually or payload.player.queue.mode == wavelink.QueueMode.normal):
            # To save on resources, we can tell the bot to disconnect from the voice channel.
            channel = await self.bot.fetch_channel(payload.track.extras.channel_id)
            await self.cleanup(payload.player)
            
            if self.skipping_manually:
                self.skipping_manually = False

            embed = RandomColorEmbed(title="Queue Finished")
            return await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Disconnect the current voice client if the bot disconnects from a voice channel.
        Additionally, if all non-bot users disconnect from the voice channel the bot is in, disconnect the bot."""
        
        if after.channel is None:
            if (member == self.bot.user and before.channel is not None) or all(m.bot or m == member for m in before.channel.members):
                await self.cleanup(self.node.get_player(before.channel.guild))

    @discord.app_commands.command()
    async def play(self, interaction: discord.Interaction, query: str):
        """Searches and plays a song from a given query."""

        # Get the player for this guild from cache.
        player = self.node.get_player(interaction.guild.id)
        if player is None:
            player = wavelink.Player(client=self.bot, channel=interaction.user.voice.channel, nodes=[self.node])
            player.autoplay = wavelink.AutoPlayMode.partial
            await interaction.user.voice.channel.connect(cls=player, reconnect=True)

        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip("<>")

        # Get the results for the query from Lavalink.
        tracks: wavelink.Search = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)

        # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
        # Alternatively, results.tracks could be an empty array if the query yielded no tracks.
        if not tracks:
            return await interaction.response.send_message("Nothing found!")

        embed = RandomColorEmbed()
        channel_info = {"channel_id": interaction.channel.id, "requester_id": interaction.user.id}

        if isinstance(tracks, wavelink.Playlist):    
            # tracks is a playlist...            

            tracks.extras = channel_info
            await player.queue.put_wait(tracks)

            embed.title = "Playlist Queued"
            embed.description = await self.format_playlist(tracks, query)

            video_thumbnail = f"https://img.youtube.com/vi/{tracks.tracks[0].identifier}/hqdefault.jpg"
            embed.set_thumbnail(url=video_thumbnail)

            await interaction.response.send_message(embed=embed)
        else:
            track: wavelink.Playable = tracks[0]
            
            track.extras = channel_info
            await player.queue.put_wait(track)

            embed.title = "Track Queued"
            embed.description = await self.format_track(track)

            video_thumbnail = f"https://img.youtube.com/vi/{track.identifier}/hqdefault.jpg"
            embed.set_thumbnail(url=video_thumbnail)

            await interaction.response.send_message(embed=embed)
        
        if not player.playing:
            await player.play(player.queue.get(), paused=False)

    @discord.app_commands.command()
    async def disconnect(self, interaction: discord.Interaction):
        """Disconnects the player from the voice channel and clears its queue."""

        player = self.node.get_player(interaction.guild.id)

        if not interaction.guild.voice_client:
            # We can't disconnect, if we're not connected.
            return await interaction.response.send_message("Not connected.")

        if not interaction.user.voice or (player.connected and interaction.user.voice.channel.id != int(player.channel.id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot may not disconnect the bot.
            return await interaction.response.send_message("You're not in my voice channel!")
        
        await self.cleanup(player)

    async def cleanup(self, player: wavelink.Player):
        
        if player:
            # Clear the queue to ensure old tracks don't start playing when someone else queues something.
            player.queue.reset()
            # Stop the current track so Lavalink consumes less resources.
            await player.skip()
            # Reset the looping status of the player.
            player.queue.mode = wavelink.QueueMode.normal
            # Disconnect from the voice channel.
            voice_client = player.channel.guild.voice_client
            if voice_client is not None:
                await voice_client.disconnect(force=True)

    @discord.app_commands.command()
    async def skip(self, interaction: discord.Interaction):
        """Skips the currently playing track. If there is another track in the queue, plays that next track."""

        player = self.node.get_player(interaction.guild.id)

        if player is None:
            return await interaction.response.send_message("No player in voice channel.")

        if player.current is None:
            return await interaction.response.send_message("No track currently playing.")

        self.skipping_manually = True
        await player.skip()

    @discord.app_commands.command()
    async def queue(self, interaction: discord.Interaction):
        """Lists the queue of tracks to play."""

        player = self.node.get_player(interaction.guild.id)

        if player is None:
            return await interaction.response.send_message("No player in voice channel.")

        if player.current is None:
            return await interaction.response.send_message("No tracks currently queued.")

        track_list = [player.current, *player.queue]
        track_names = "\n".join([f"{i+1}. {await self.format_track(track)}{' **(Now playing)**' if i == 0 else ''}" for i, track in enumerate(track_list[:10])])

        # Only print the first 10 tracks in the queue, to avoid a long message
        if len(track_list) > 10:
            track_names += f"\n\nPlus {len(track_list)-10} more..."

        if len(track_names) > 4096:
            track_names = track_names[:4093] + "..."

        embed = RandomColorEmbed(title="Queue", description=track_names)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command()
    async def pause(self, interaction: discord.Interaction):
        """Pauses the currently playing track, if any."""        

        player = self.node.get_player(interaction.guild.id)

        if player is None:
            return await interaction.response.send_message("No player in voice channel.")

        if player.current is None:
            return await interaction.response.send_message("No track currently playing.")

        await player.pause(not player.paused)
        embed = RandomColorEmbed(title="Now Paused" if player.paused else "Now Resuming")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command()
    async def stop(self, interaction: discord.Interaction):
        """Stops the player and clears the queue without disconnecting the bot from the voice channel."""

        player = self.node.get_player(interaction.guild.id)

        if player is None:
            return await interaction.response.send_message("No player in voice channel.")
        
        if player.current is None:
            return await interaction.response.send_message("No track currently playing.")

        player.queue.reset()
        player.current.extras = {**dict(player.current.extras), "manual_stop": True}
        
        await player.stop()
        
        embed = RandomColorEmbed(title="Stopping")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command()
    async def remove(self, interaction: discord.Interaction, track_number: int):
        """Removes the track at a given position from the queue."""

        player = self.node.get_player(interaction.guild.id)

        if track_number < 1:
            return await interaction.response.send_message("Invalid track number. Track number must be at least 1.")
        elif track_number > len(player.queue) + 1:
            return await interaction.response.send_message("Invalid track number. Track number cannot be more than the number of tracks in the queue.")
        elif track_number == 1:
            await player.skip()
        else:
            track = player.queue[track_number-2]
            embed = RandomColorEmbed(title="Track Removed", description=await self.format_track(track))
            video_thumbnail = f"https://img.youtube.com/vi/{track.identifier}/hqdefault.jpg"
            embed.set_thumbnail(url=video_thumbnail)
        
            await interaction.response.send_message(embed=embed)
            del player.queue[track_number-2]

    @discord.app_commands.command()
    async def volume(self, interaction: discord.Interaction, volume: int):
        """Sets the volume of the player between 0% and 1000%."""

        player = self.node.get_player(interaction.guild.id)

        if player is None:
            return await interaction.response.send_message("No player in voice channel.")

        if not interaction.user.guild_permissions.manage_guild:
            volume = min(volume, 100)

        await player.set_volume(volume)
        embed = RandomColorEmbed(title=f"Volume: {volume}%")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command()
    async def nowplaying(self, interaction: discord.Interaction):
        """Displays the progress of the currently playing track."""

        player = self.node.get_player(interaction.guild.id)

        if player is None:
            return await interaction.response.send_message("No player in voice channel.")

        track = player.current
        if not track:
            return await interaction.response.send_message("No track is currently playing.")

        position = timedelta(seconds=player.position // 1000)
        duration = timedelta(seconds=track.length // 1000)

        formatted_position = f"Progress: {position}/{duration}"        
        description = f"{await self.format_track(track)}\n{formatted_position}"

        embed = RandomColorEmbed(title="Currently Playing", description=description)
        video_thumbnail = f"https://img.youtube.com/vi/{track.identifier}/hqdefault.jpg"
        embed.set_thumbnail(url=video_thumbnail)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command()
    async def loop(self, interaction: discord.Interaction):
        """Toggles whether or not the current track is looping."""
        
        player = self.node.get_player(interaction.guild.id)

        if player is None:
            return await interaction.response.send_message("No player in voice channel.")

        player.queue.mode = wavelink.QueueMode.loop if player.queue.mode == wavelink.QueueMode.normal else wavelink.QueueMode.normal
        embed = RandomColorEmbed(title=f"Looping {'On' if player.queue.mode == wavelink.QueueMode.loop else 'Off'}")
        await interaction.response.send_message(embed=embed)

    async def format_track(self, track: wavelink.Playable):
        return f"**[{track.title}]({track.uri})**\nRequested by {(await self.bot.fetch_user(track.extras.requester_id)).mention}"
    
    async def format_playlist(self, playlist: wavelink.Playlist, playlist_url: str):
        return f"**[{playlist.name}]({playlist_url})** - {len(playlist.tracks)} tracks\nRequested by {(await self.bot.fetch_user(playlist[0].extras.requester_id)).mention}"
        # playlist.url defaults to None, so we have to pass in the playlist_url from play()