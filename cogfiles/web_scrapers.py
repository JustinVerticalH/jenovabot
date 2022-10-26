import aiohttp, re
from bs4 import BeautifulSoup
from ioutils import RandomColorEmbed
from howlongtobeatpy import HowLongToBeat

from discord.ext import commands


class WebScrapers(commands.Cog, name="Web Scrapers"):
    """Grab data from various websites and send it."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(aliases=["hltb"], invoke_without_command=True)
    async def howlongtobeat(self, context: commands.Context, *, game_name: str):
        """Search HowLongToBeat with the given game name and show completion time info."""
        
        game_list = await WebScrapers.hltb_search(game_name)
        if game_list is None:
            await context.send("Could not find a game with that title.")
            return
        
        game = game_list[0]

        game_data = RandomColorEmbed(title=game.game_name, url=game.game_web_link)
        game_data.set_thumbnail(url=game.game_image_url)
        
        if game.main_story != 0:
            game_data.add_field(name="Main Story", value=f"{game.main_story} Hours", inline=False)
        if game.main_extra != 0:
            game_data.add_field(name="Main + Extra", value=f"{game.main_extra} Hours", inline=False)
        if game.completionist != 0:
            game_data.add_field(name="Completionist", value=f"{game.completionist} Hours", inline=False)

        await context.send(embed=game_data)
        
    @howlongtobeat.command()
    async def search(self, context: commands.Context, *, game_name: str):
        """Search HowLongToBeat with the given game name and show at most the first 10 results."""

        game_list = await WebScrapers.hltb_search(game_name)
        if game_list is None:
            await context.send("Could not find a game with that title.")
            return
        
        game_list_data = RandomColorEmbed(
            title=f"HowLongToBeat Search: {game_name!r}",
            description='\n'.join([f"{i+1}. [{game.game_name}]({game.game_web_link})" for i, game in enumerate(game_list[:10])])
        )
        game_list_data.set_thumbnail(url="https://howlongtobeat.com/img/hltb_brand.png")

        await context.send(embed=game_list_data)

    @staticmethod
    async def hltb_search(game_name: str):
        results_list = await HowLongToBeat().async_search(game_name, similarity_case_sensitive=False)
        if results_list is None or len(results_list) == 0:
            return None
        
        return sorted(results_list, key=lambda element: element.similarity, reverse=True)

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
                        await context.send("Could not find a song with that title.")
                        return
                    else:
                        songs = table.find_all("div", class_ = "big_link")
                        song_link = songs[0].find("a").get("href")
                        async with session.get(f"http://headyversion.com{song_link}") as response:
                            content = await response.read()
                            soup = BeautifulSoup(content, "html.parser")

                title = "HeadyVersion: " + re.search(r"Grateful Dead best (.+) \| headyversion", soup.find("title").string).group(1)
                description = ""

                for show in list(soup.find_all("div", class_="row s2s_submission bottom_border"))[:5]:
                    votes = re.search(r"(\d+)", show.find("div", class_="score").string).group(1)
                    
                    show_details = show.find("div", class_="show_details_info")
                    show_date = show_details.find("div", class_="show_date")
                    show_heady_link = f"http://headyversion.com{show_details.find('a').get('href')}"
                    show_archive_link = f"http://headyversion.com{show.find('div', class_='show_links').find('a', target='_blank').get('href')}"

                    for stripped_show_date in show_date.stripped_strings:
                        field_name = f"**{stripped_show_date}** \n{votes} votes"
                        field_value = f"[HeadyVersion Link]({show_heady_link}) | [Archive.org Link]({show_archive_link})\n\n"
                        description += f"{field_name}\n {field_value}"

                embed = RandomColorEmbed(title=title, url=response.url, description=description)
                embed.set_thumbnail(url="https://clipartspub.com/images/grateful-dead-clipart-template-5.png")
                await context.send(embed=embed)