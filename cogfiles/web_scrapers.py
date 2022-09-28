import aiohttp, re
from bs4 import BeautifulSoup
from howlongtobeatpy import HowLongToBeat

import discord
from discord.ext import commands


class WebScrapers(commands.Cog, name="Web Scrapers"):
    """Grab data from various websites and send it."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=["hltb"])
    async def howlongtobeat(self, context: commands.Context, *, game_name: str):
        """Search HowLongToBeat with the given game name."""
        
        results_list = await HowLongToBeat().async_search(game_name)
        if results_list is not None and len(results_list) > 0:
            game = max(results_list, key=lambda element: element.similarity)
        
        game_data = discord.Embed(title=game.game_name, url=game.game_web_link)
        game_data.set_thumbnail(url=game.game_image_url)
        
        if game.main_story != 0:
            game_data.add_field(name="Main Story", value=f"{game.main_story} Hours", inline=False)
        if game.main_extra != 0:
            game_data.add_field(name="Main + Extra", value=f"{game.main_extra} Hours", inline=False)
        if game.completionist != 0:
            game_data.add_field(name="Completionist", value=f"{game.completionist} Hours", inline=False)

        await context.send(embed=game_data)
        
    
    @commands.command()
    async def heady(self, context: commands.Context, *, song_name: str):
        """Search HeadyVersion with the given song name."""

        async with aiohttp.ClientSession() as session:
            async with session.get("http://headyversion.com/search/") as response:
                token = response.cookies["csrftoken"].value
            async with session.post("http://headyversion.com/search/", data={"title": song_name, "csrfmiddlewaretoken": token}) as response:
                content = await response.read()
                soup = BeautifulSoup(content, "html.parser")

                if str(response.url) == "http://headyversion.com/search/":
                    table = soup.find("table")
                    if table is None:
                        await context.send(f"Could not find a song with that title.")
                        return
                    else:
                        songs = table.find_all("div", class_ = "big_link")
                        song_link = songs[0].find("a").get("href")
                        async with session.get(f"http://headyversion.com{song_link}") as response:
                            content = await response.read()
                            soup = BeautifulSoup(content, "html.parser")

                title = soup.find("title").string
                title = re.search(r"Grateful Dead best (.+) \| headyversion", title).group(1)
                title = f"HeadyVersion: {title}"
                    
                description = ""
                for show in list(soup.find_all("div", class_ = "row s2s_submission bottom_border"))[:5]:
                    votes = show.find("div", class_ = "score").string
                    votes = re.search(r"(\d+)", votes).group(1)
                    show_details = show.find("div", class_ = "show_details_info")
                    show_date = show_details.find("div", class_ = "show_date")
                    show_heady_link = f"""http://headyversion.com{show_details.find("a").get("href")}"""
                    show_archive_link = f"""http://headyversion.com{show.find("div", class_ = "show_links").find("a", target = "_blank").get("href")}"""

                    for stripped_show_date in show_date.stripped_strings:
                        field_name = f"**{stripped_show_date}** \n{votes} votes"
                        field_value = f"[HeadyVersion Link]({show_heady_link}) | [Archive.org Link]({show_archive_link})\n\n"
                        description += f"{field_name}\n {field_value}"

                embed = discord.Embed(title = title, url = response.url, description = description)
                embed.set_thumbnail(url="https://clipartspub.com/images/grateful-dead-clipart-template-5.png")
                await context.send(embed=embed)