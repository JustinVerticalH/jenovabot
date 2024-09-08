import discord, os, random, tempfile, textwrap

from contextlib import contextmanager
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont


IMAGE_NAMES = ["akiha", "arcueid", "ciel", "hisui", "kohaku", "satsuki"]


class ImageEditing(commands.Cog, name="Image Editing"):
    """Place text on various image templates."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=[*IMAGE_NAMES, "kt", "typemoondaily"])
    async def kagetsutoya(self, context: commands.Context, *, text: str):
        """Generates an image in the style of the daily messages found in Kagetsu Tōya. 
        Image templates: akiha, arcueid, ciel, hisui, kohaku, satsuki.
        By default, this command picks a random image to use as the background, 
        but if the user runs this command using an image name instead, that image will be used as the background."""
        alias_name = context.invoked_with
        image_name = f"image_resources/{alias_name}.png" if alias_name in IMAGE_NAMES else None # An image name of None indicates a random template
        await ImageEditing.send_kagetsutoya_in_channel(context.channel, image_name, text)

    @staticmethod
    async def send_kagetsutoya_in_channel(channel: discord.TextChannel | discord.ForumChannel, template_path: str | None, text: str):
        """Add text to the provided image template and send the image. 
        This function uses the Sazanami Gothic font."""
        if template_path is None:
            templates = [template_name for template_name in os.listdir("image_resources") if template_name.find(".png") >= 0]
            template_path = (f"image_resources/{random.choice(templates)}")

        with Image.open(template_path) as image:
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
    """Manages resources for a temporary image file."""
    try:
        fp = tempfile.NamedTemporaryFile(suffix=".png", delete=False) 
        fp.close()
        yield fp
    finally:
        os.remove(fp.name)