import discord
from discord.ext import commands
import json
import os
import datetime
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix = "!", intents = intents)

with open("values.json", "r+") as values_file:
    values = json.load(values_file)

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return
    if "elden ring" in message.content.lower():
        await message.channel.send("Shut the fuck up you maggot. You clearly don't understand what makes a great video game. Elden Ring is a beautifully crafted masterpiece with a rich-open, beautiful graphics, fantastical gameplay, a great narrative, great quest design and it gives a ton of freedom and an actual challenge. Meanwhile all the other games that came out this year are overrated, mediocre games with boring, generic and repetitive gameplay, boring and uninteresting narratives and keep telling you what to do every 5 seconds. You and the people that support these kinds of doghit games are everything that is wrong this the gaming industry. These companies give you garbage and you guys eat it up and ask for more. Elden Ring is literally the only game that deserves to be called a true video game. Everything else is a joke and a scam. So fuck you, fuck all the people that pay for it, and fuck these companies that keep pumping these shitty mediocre kiddy games. I hope all of you fuckers die. Elden Ring and FromSoftware deserve all the praise and much more. They are single-handedly carrying the entire gaming industry with their state of the art games.")
    await bot.process_commands(message)

# Not working correctly yet. Fix this
@bot.event
async def on_scheduled_event_create(event: discord.ScheduledEvent):
    for role in event.guild.roles:
        if role.name.replace("Ping", "") in event.name:
            channel = await event.guild.fetch_channel(values["scheduled_event_alert_channel"])
            start_time = int(event.start_time.timestamp())
            await channel.send(f"{event.name} is set for <t:{start_time}>! {role.mention}")

# Test this. Does the channel preference persist after the bot stops running?
@bot.command()
async def alerts(ctx, arg: str):
    for channel in ctx.guild.channels:
        if channel.name == arg or channel.mention == arg:
            values["scheduled_event_alert_channel"] = channel.id
            values_file.seek(0)
            json.dump(values, values_file, indent = 2)
            values_file.truncate()
            await ctx.send(f"Event alert channel is set to {channel.mention}")
            return
    await ctx.send("Channel not found. Try again.")

@bot.command()
async def test(ctx):
    await ctx.send("Testing!")

bot.run(token)