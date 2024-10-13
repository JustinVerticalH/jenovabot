import aiohttp, json, os, re, textwrap

from bs4 import BeautifulSoup
from dateutil import parser
from ioutils import RandomColorEmbed
from howlongtobeatpy import HowLongToBeat
from thefuzz import process

from discord.ext import commands
from discord.utils import format_dt


ITAD_API_KEY = os.getenv("ITAD_API_KEY")
STEAMGRIDDB_API_KEY = os.getenv("STEAMGRIDDB_API_KEY")
EBAY_APP_NAME = os.getenv("EBAY_APP_NAME")


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
        """Search HowLongToBeat with the given game name. Returns the full list of results, sorted by similarity to the given name."""
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
        """Query AniList's API with the given search term and the given categories (anime and/or manga)."""
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
    
    @commands.command(aliases=["vn"])
    async def vndb(self, context: commands.Context, *, vn_name: str):
        """Search VNDB for a visual novel matching the provided search."""
        vn_request_data = f"""{{
            "filters": ["search", "=", "{vn_name}"],
            "fields": "id, title, image.url, image.sexual, image.violence, length_minutes, description, developers.name"
        }}"""

        async with aiohttp.ClientSession(headers={'Content-Type': 'application/json'}) as session:
            async with session.post("https://api.vndb.org/kana/vn", data=vn_request_data) as response:
                results = (await response.json())["results"]
            
        vn, _ = process.extractOne(vn_name, results, processor=lambda vn: vn if vn == vn_name else vn["title"])

        vn["description"] = re.sub(r"\[url=(.*)\](.*)\[\/url\]", r"[\2](\1)", vn["description"])
        vn["description"] = re.sub(r"\[i\]|\[/i\]", r"*", vn["description"]) # Changes italics markers to match Discord's formatting
        vn["description"] = re.sub(r"\[spoiler\]|\[\/spoiler\]", r"\|\|", vn["description"]) # Changes spoiler markers to match Discord's formatting
        vn["description"] = textwrap.shorten(vn["description"], width=350, placeholder="...")

        developers = ", ".join(developer["name"] for developer in vn["developers"])
        length_hours = "Unknown" if vn["length_minutes"] is None else f"{float(vn['length_minutes'] / 60):.2f} hours"
        description = f"**Developed by: {developers}**\n**Average completion time: {length_hours}**\n\n{vn['description']}"
        vn_data = RandomColorEmbed(title=vn["title"], url=f"https://vndb.org/{vn['id']}", description=description)
        if vn["image"]["sexual"] < 2 and vn["image"]["violence"] < 2:
            vn_data.set_thumbnail(url=vn["image"]["url"])
        
        await context.send(embed=vn_data)

    @commands.command(aliases=["itad", "sale"])
    async def isthereanydeal(self, context: commands.Context, *, search: str):
        """Search IsThereAnyDeal for a game matching the provided search.
        This command retrives the first 5 results of a search on ITAD. 
        For each result, prints the name of the game, the sale percent and new price, and the store with that price."""
        async with aiohttp.ClientSession() as session:
            api = f"https://api.isthereanydeal.com/games/search/v1?key={ITAD_API_KEY}&title={search}"
            async with session.get(api) as response:

                content = await response.read()
                content = json.loads(content)

                if response.status != 200 or len(content) == 0:
                    content = None

        if content is None:
            return await context.send("Could not find a game with that title.")

        description = ""

        valid_games = 0
        for i in range(len(content)):
            game_id = content[i]["id"]
            game_title = content[i]["title"]
            
            request_data = f"""{json.dumps([game_id])}"""
            api = f"https://api.isthereanydeal.com/games/prices/v3?key={ITAD_API_KEY}"
            async with aiohttp.ClientSession() as session:
                async with session.post(api, data=request_data) as response:
                    price_content = await response.read()
                    price_content = json.loads(price_content)

            # Some entries in the list of results are not being sold on any stores.
            # Trying to find the price of these games results in an IndexError.
            # To avoid displaying these entries, skip over them if an IndexError occurs.
            # Once 5 valid entries have been found and added to the description, we are done.
            try:
                game_deals = price_content[0]["deals"][0]
                price_cut = game_deals["cut"]
                price_new = f"{float(game_deals['price']['amount']):.2f}"
                store_name = game_deals["shop"]["name"]
                game_url = game_deals["url"]
                    
                description += f"**[{game_title}]({game_url})**\n**${price_new}** ({price_cut}% Off)\n{store_name}\n\n"

                valid_games += 1
                if valid_games >= 5:
                    break

            except IndexError:
                continue

        embed = RandomColorEmbed(title="Is There Any Deal?", description=description)
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1005720333053075486/1066597183173959761/YWJzOi8vZGlzdC9pY29ucy9pc3RoZXJlYW55ZGVhbF8xNjU2MDgucG5n.png")
        await context.send(embed=embed)

    @commands.command()
    async def ebay(self, context: commands.Context, *, search: str):
        """Search eBay for listings matching the provided search.
        This command retrives the first 5 results of a search on eBay."""
        async with aiohttp.ClientSession() as session:
            api = "https://svcs.ebay.com/services/search/FindingService/v1" \
            f"?OPERATION-NAME=findItemsByKeywords&SECURITY-APPNAME={EBAY_APP_NAME}" \
            f"&REST-PAYLOAD&RESPONSE-DATA-FORMAT=JSON&keywords={search}"
            async with session.get(api) as response:
                content = await response.read()
                content = json.loads(content)

        search_result = content["findItemsByKeywordsResponse"][0]["searchResult"][0]
        if (search_result["@count"] == "0"):
            return await context.send("Could not find any search results.")
                
        url = content["findItemsByKeywordsResponse"][0]["itemSearchURL"][0]
        embed = RandomColorEmbed(title="eBay", url=url)
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/4/48/EBay_logo.png/800px-EBay_logo.png")

        description = ""
        # Iterate through the first 5 results, and extract information about each. 
        for result in content["findItemsByKeywordsResponse"][0]["searchResult"][0]["item"][:5]:
            title = result["title"][0]
            url = result["viewItemURL"][0]
            price = f"{float(result['sellingStatus'][0]['convertedCurrentPrice'][0]['__value__']):.2f}"
                    
            # Each listing is an auction and/or fixed price. Display the correct price.
            listing_type = result["listingInfo"][0]["listingType"][0]
            if listing_type == "Auction":
                price_info = f"Current Bid: ${price}"
            elif listing_type == "FixedPrice":
                price_info = f"Buy It Now: ${price}"
            elif listing_type == "AuctionWithBIN":
                buy_now_price = f"{float(result['listingInfo'][0]['convertedBuyItNowPrice'][0]['__value__']):.2f}"
                price_info = f"Current Bid: ${price}\nBuy It Now: ${buy_now_price}"
            else:
                price_info = f"${price}"

            end_time = parser.parse(result["listingInfo"][0]["endTime"][0])
            end_time = format_dt(end_time, style='R')

            description += f"**[{title}]({url})**\n{price_info}\nEnds {end_time}\n\n"

        embed.description = description

        await context.send(embed=embed)