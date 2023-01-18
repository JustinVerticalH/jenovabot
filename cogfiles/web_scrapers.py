import aiohttp, json, re

from bs4 import BeautifulSoup
from ioutils import RandomColorEmbed
from howlongtobeatpy import HowLongToBeat
from thefuzz import process

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
            # First, perform a GET request to get the CSRF token
            async with session.get("http://headyversion.com/search/") as response:
                token = response.cookies["csrftoken"].value
            # Then, perform a POST request with the title and CSRF token to search HeadyVersion
            async with session.post("http://headyversion.com/search/", data={"title": song_name, "csrfmiddlewaretoken": token}) as response:
                content = await response.read()
                soup = BeautifulSoup(content, "html.parser")

                if str(response.url) == "http://headyversion.com/search/":
                    table = soup.find("table")
                    # If table is None, we know that no results were found
                    if table is None:
                        await context.send("Could not find a song with that title.")
                        return
                    # If the HTML has a table, then Heady is listing multiple song choices, and we choose the first one
                    else:
                        songs = table.find_all("div", class_="big_link")
                        song_link = songs[0].find("a").get("href")
                        async with session.get(f"http://headyversion.com{song_link}") as response:
                            content = await response.read()
                            soup = BeautifulSoup(content, "html.parser")

                # This regex is how Heady lists its webpage titles. Extract the name of the song from this webpage title and add it to our embed title
                song_title = re.search(r"Grateful Dead best (.+) \| headyversion", soup.find("title").string).group(1)
                title = f"HeadyVersion: {song_title}"
                description = ""
                # Find the first 5 shows in Heady's list of show dates, and add each one to the description for the embed
                for show in list(soup.find_all("div", class_="row s2s_submission bottom_border"))[:5]:
                    votes = re.search(r"(\d+)", show.find("div", class_="score").string).group(1)
                    
                    # Extract all the details from the show, and retrieve the date, Heady link, and archive.org link from the details
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

    @commands.command()
    async def anilist(self, context: commands.Context, *, search: str):
        """Search AniList for an anime or manga with a title matching the provided search."""
        await WebScrapers.anilist_search(context, search, anime=True, manga=True)

    @commands.command()
    async def anime(self, context: commands.Context, *, search: str):
        """Search AniList for an anime with a title matching the provided search."""
        await WebScrapers.anilist_search(context, search, anime=True)
        
    @commands.command()
    async def manga(self, context: commands.Context, *, search: str):
        """Search AniList for a manga with a title matching the provided search."""
        await WebScrapers.anilist_search(context, search, manga=True)

    @staticmethod
    async def anilist_search(context: commands.Context, search: str, anime: bool=False, manga: bool=False):
        url = "https://graphql.anilist.co"
        # Here we define our query as a multi-line string
        type = "" if manga and anime else ", type: MANGA" if manga else ", type: ANIME"
        query = """
        query ($search: String) {
            Media (search: $search%s) {
                siteUrl
            }
        }""" % (type)

        # Define our query variables and values that will be used in the query request
        variables = {
            "search": search
        }

        # Make the API request
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"query": query, "variables": variables}) as response:
                response_text = await response.text()
                response_json = json.loads(response_text)
                response_url = response_json["data"]["Media"]["siteUrl"]
                await context.send(response_url)
    
    @commands.command()
    async def vndb(self, context: commands.Context, *, vn_name: str):
        vn_request_data = f"""{{
            "filters": ["search", "=", "{vn_name}"],
            "fields": "id, title, image.url, image.sexual, image.violence, description"
        }}"""

        async with aiohttp.ClientSession(headers={'Content-Type': 'application/json'}) as session:
            async with session.post("https://api.vndb.org/kana/vn", data=vn_request_data) as response:
                results = (await response.json())["results"]
            
            vn, _ = process.extractOne(vn_name, results, processor=lambda vn: vn if vn == vn_name else vn["title"])

        vn["description"] = re.sub(r"\[url=(.*)\](.*)\[\/url\]", r"[\2](\1)", vn["description"])
        if len(vn["description"]) > 4096:
            vn["description"] = vn["description"][:4093] + "..."

        vn_data = RandomColorEmbed(title=vn["title"], url=f"https://vndb.org/{vn['id']}", description=vn["description"])
        if vn["image"]["sexual"] < 2 and vn["image"]["violence"] < 2:
            vn_data.set_thumbnail(url=vn["image"]["url"])
        
        await context.send(embed=vn_data)