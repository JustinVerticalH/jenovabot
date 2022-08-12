from typing import Optional
import discord
from discord.ext import commands
import asyncio
import json
import os
import re
import datetime
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

streampause_data: dict[discord.Message, discord.Member] = None

def read(file_name: str, key: str) -> any:
    with open(file_name, "r+") as file:
        file_json = json.load(file)
    return file_json.get(key, None)

def write(file_name: str, key: str, value: any):
    with open(file_name, "r+") as file:
        file_json = json.load(file)
        file_json[key] = value
        file.seek(0)
        json.dump(file_json, file, indent=2)
        file.truncate()

@bot.event
async def on_ready():
    reminders_list = map(tuple, read("reminders.json", "reminders"))
    reminders = set(reminders_list if reminders_list != None else [])
    for reminder in reminders:
        await process_reminder(*reminder)

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return
    if "elden ring" in message.content.lower():
        await message.channel.send("Shut the fuck up you maggot. You clearly don't understand what makes a great video game. Elden Ring is a beautifully crafted masterpiece with a rich-open, beautiful graphics, fantastical gameplay, a great narrative, great quest design and it gives a ton of freedom and an actual challenge. Meanwhile all the other games that came out this year are overrated, mediocre games with boring, generic and repetitive gameplay, boring and uninteresting narratives and keep telling you what to do every 5 seconds. You and the people that support these kinds of doghit games are everything that is wrong this the gaming industry. These companies give you garbage and you guys eat it up and ask for more. Elden Ring is literally the only game that deserves to be called a true video game. Everything else is a joke and a scam. So fuck you, fuck all the people that pay for it, and fuck these companies that keep pumping these shitty mediocre kiddy games. I hope all of you fuckers die. Elden Ring and FromSoftware deserve all the praise and much more. They are single-handedly carrying the entire gaming industry with their state of the art games.")
    await bot.process_commands(message)

@bot.event
async def on_scheduled_event_create(event: discord.ScheduledEvent):
    for role in event.guild.roles:
        if role.name.replace(" Ping", "") in event.name:
            channel = await event.guild.fetch_channel(read("settings.json", "scheduled_event_alert_channel_id"))
            start_time = int(event.start_time.timestamp())
            await channel.send(f"{event.name} is set for <t:{start_time}>! {role.mention}")

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.Member):
    global streampause_data
    if streampause_data is not None:
        await attempt_to_finish_streampause(reaction, user, user.voice.channel if user.voice else None)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    global streampause_data
    if streampause_data is not None:
        voice_channel = before.channel if after.channel is None else after.channel if before.channel is None else None
        reaction = next(reaction for reaction in streampause_data["message"].reactions if reaction.emoji == "👍")

        await attempt_to_finish_streampause(reaction, member, voice_channel)

async def attempt_to_finish_streampause(reaction: discord.Reaction, user: discord.Member, voice_channel: Optional[discord.VoiceChannel]):
    global streampause_data
    if user.bot or reaction.message != streampause_data["message"] or reaction.emoji != "👍" or voice_channel is None:
        return

    reacted_members = set(await reaction.users().flatten())
    vc_members = set(voice_channel.members)

    if reacted_members & vc_members == vc_members:
        original_author = streampause_data["author"]
        ping_message = await reaction.message.channel.send(f"{original_author.mention} Everyone's here!")

        await reaction.message.delete()
        await ping_message.delete(delay=5.0)

        streampause_data = None

@bot.command()
async def alerts(context: commands.Context, argument: str):
    if context.message.author.guild_permissions.manage_guild:
        for channel in context.guild.channels:
            if argument in [channel.name, channel.mention]:
                write("settings.json", "scheduled_event_alert_channel_id", channel.id)
                await context.send(f"Event alert channel is set to {channel.mention}")
                return
        await context.send("Channel not found. Try again.")
        return
    await context.send("User needs Manage Server permission to use this command.")
    return
    

@bot.command()
async def streampause(context: commands.Context):
    await context.message.delete(delay=2.0)
    if context.author.voice is None:
        message = await context.send("This command is only usable inside a voice channel.")
        await message.delete(delay=5.0)
        return

    message = await context.send("React with 👍 when you're all set!")

    global streampause_data
    streampause_data = {
        "message": message,
        "author": context.author
    }

    await message.add_reaction("👍")

@bot.command()
async def remindme(context: commands.Context, time: str, message: str):
    # Determine the amount of time based on the time inputted
    timer_parameters = re.search("(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time).groups()
    num_days, num_hours, num_minutes, num_seconds = tuple(map(lambda t: int(0 if t == None else t), timer_parameters))
    await context.message.add_reaction("👍")

    date_time = datetime.datetime.now() + datetime.timedelta(days = num_days, hours = num_hours, minutes = num_minutes, seconds = num_seconds)
    timestamp = int(round(date_time.timestamp()))
    await process_reminder(context.message.author.id, context.message.channel.id, timestamp, message)

@bot.command()
async def process_reminder(author_id: int, channel_id: int, timestamp: int, message: str):
    # Add the new reminder to the list of reminders and write the updated list into settings.json
    reminders_list = map(tuple, read("reminders.json", "reminders"))
    reminders = set(reminders_list if reminders_list != None else [])
    
    reminders.add(tuple((author_id, channel_id, timestamp, message)))
    write("reminders.json", "reminders", list(reminders))

    # Wait until the correct time, send a message to remind the user, and remove the reminder from the list
    sleep_time = timestamp - int(round(datetime.datetime.now().timestamp()))
    if sleep_time > 0:
        await asyncio.sleep(sleep_time)
    channel = await bot.fetch_channel(channel_id)
    author = await bot.fetch_user(author_id)
    await channel.send(f"{author.mention} {message}")

    reminders.remove(tuple((author_id, channel_id, timestamp, message)))
    write("reminders.json", "reminders", list(reminders))

@bot.command()
async def test(context: commands.Context):
    await context.send("Testing!")

bot.run(token)