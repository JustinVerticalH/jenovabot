import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

def read(key: str) -> any:
    with open("values.json", "r+") as values_file:
        values = json.load(values_file)
    return values.get(key, None)

def write(key: str, value: any):
    with open("values.json", "r+") as values_file:
        values = json.load(values_file)
        values[key] = value
        values_file.seek(0)
        json.dump(values, values_file, indent=2)
        values_file.truncate()


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
        if role.name.replace("Ping", "") in event.name:
            channel = await event.guild.fetch_channel(read("scheduled_event_alert_channel_id"))
            start_time = int(event.start_time.timestamp())
            await channel.send(f"{event.name} is set for <t:{start_time}>! {role.mention}")

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.Member):
    if not user.bot and reaction.message.id == read("streampause_message_id"):
        if reaction.count == len(user.voice.channel.members) + 1:
            original_author = await user.guild.fetch_member(read("streampause_author_id"))
            await reaction.message.channel.send(f"{original_author.mention} Everyone's here!")

            write("streampause_message_id", None)
            write("streampause_author_id", None)

@bot.command()
async def alerts(context: commands.Context, argument: str):
    for channel in context.guild.channels:
        if argument in [channel.name, channel.mention]:
            write("scheduled_event_alert_channel_id", channel.id)
            await context.send(f"Event alert channel is set to {channel.mention}")
            return
    await context.send("Channel not found. Try again.")

@bot.command()
async def streampause(context: commands.Context):
    message = await context.send("React with 👍 when you're all set!")
    await message.add_reaction("👍")
    write("streampause_message_id", message.id)
    write("streampause_author_id", context.author.id)

@bot.command()
async def test(context: commands.Context):
    await context.send("Testing!")

bot.run(token)