import discord, os, random, tempfile, textwrap

from contextlib import contextmanager
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

class ImageEditing(commands.Cog, name="Image Editing"):
    """Place text on various image templates."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(aliases=["kagetsu", "kt", "typemoondaily"], invoke_without_command=True)    
    async def kagetsutoya(self, context: commands.Context, *, text: str):
        templates = [x for x in os.listdir("image_resources") if x.find(".png") >= 0]
        template = (f"image_resources/{random.choice(templates)}")

        await ImageEditing.send_kagetsutoya(context, template, text)

    @kagetsutoya.group()
    async def akiha(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya(context, "image_resources/akiha.png", text)

    @kagetsutoya.group(aliases=["arc"])
    async def arcueid(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya(context, "image_resources/arcueid.png", text)
    
    @kagetsutoya.group()
    async def ciel(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya(context, "image_resources/ciel.png", text)
    
    @kagetsutoya.group()
    async def hisui(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya(context, "image_resources/hisui.png", text)
    
    @kagetsutoya.group()
    async def kohaku(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya(context, "image_resources/kohaku.png", text)

    @kagetsutoya.group()
    async def satsuki(self, context: commands.Context, *, text: str):
        await ImageEditing.send_kagetsutoya(context, "image_resources/satsuki.png", text)

    @staticmethod
    async def send_kagetsutoya(context: commands.Context, template_name: str, text: str):
        """Add text to the provided image template and send the image. This function uses the Sazanami Gothic font."""
        with Image.open(template_name) as image:
            draw = ImageDraw.Draw(image)
            draw.font = ImageFont.truetype("image_resources/sazanami-gothic.ttf", 28)
            
            # If the user doesn't provide line breaks, then format the text so that it 
            if "\n" not in text:
                text = textwrap.fill(text, width=44)
            draw.text((145, 120), text, fill=(255, 255, 255))
            
            with temp_png() as temp_file:
                image.save(temp_file.name)
                image_file = discord.File(temp_file.name, filename="kagetsu.png")
                await context.send(file=image_file)

@contextmanager
def temp_png():
    try:
        fp = tempfile.NamedTemporaryFile(suffix=".png", delete=False) 
        fp.close()
        yield fp
    finally:
        os.remove(fp.name)
