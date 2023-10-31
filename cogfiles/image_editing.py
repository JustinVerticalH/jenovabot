import discord, os, random, sys, tempfile, textwrap

from contextlib import contextmanager
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

class ImageEditing(commands.Cog, name="Image Editing"):
    """Place text on various image templates."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(aliases=["kagetsu", "kt", "typemoondaily"], invoke_without_command=True)    
    async def kagetsutoya(self, context: commands.Context, *, text: str):
        """Generates an image in the style of the daily messages found in Kagetsu Tōya."""
        # A template value of None indicates a random template
        await ImageEditing.send_kagetsutoya_in_channel(context.channel, None, text)

    @kagetsutoya.group()
    async def akiha(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya_in_channel(context.channel, "image_resources/akiha.png", text)

    @kagetsutoya.group(aliases=["arc"])
    async def arcueid(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya_in_channel(context.channel, "image_resources/arcueid.png", text)
    
    @kagetsutoya.group()
    async def ciel(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya_in_channel(context.channel, "image_resources/ciel.png", text)
    
    @kagetsutoya.group()
    async def hisui(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya_in_channel(context.channel, "image_resources/hisui.png", text)
    
    @kagetsutoya.group()
    async def kohaku(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya_in_channel(context.channel, "image_resources/kohaku.png", text)

    @kagetsutoya.group()
    async def satsuki(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya_in_channel(context.channel, "image_resources/satsuki.png", text)

    @staticmethod
    async def send_kagetsutoya_in_channel(channel: discord.TextChannel | discord.ForumChannel, template_name: str, text: str):
        """Add text to the provided image template and send the image. This function uses the Sazanami Gothic font."""
            
        if template_name is None:
            templates = [x for x in os.listdir("image_resources") if x.find(".png") >= 0]
            template_name = (f"image_resources/{random.choice(templates)}")

        with Image.open(template_name) as image:
            draw = ImageDraw.Draw(image)
            draw.font = ImageFont.truetype("image_resources/sazanami-gothic.ttf", 28)
            
            # If the user doesn't provide line breaks, then format the text so that it breaks lines naturally
            if "\n" not in text:
                text = textwrap.fill(text, width=44)
            # Draw a layer of black text first to simulate a shadow
            draw.text((148, 123), text, fill=(0, 0, 0))
            draw.text((146, 121), text, fill=(255, 255, 255))
            
            with temp_png() as temp_file:
                image.save(temp_file.name)
                image_file = discord.File(temp_file.name, filename="image.png")
                await channel.send(file=image_file)

@contextmanager
def temp_png():
    try:
        fp = tempfile.NamedTemporaryFile(suffix=".png", delete=False) 
        fp.close()
        yield fp
    finally:
        os.remove(fp.name)