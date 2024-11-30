# JENOVA
JENOVABot, or just JENOVA, is a multi-purpose Discord bot built with various utility commands, co-written by Justin Levine and Noah Levitt.
## Features
### Copypastas
When someone types certain phrases, JENOVA will automatically respond with a specific copypasta. See the full list of copypastas [here](copypastas.json).
### Event alerts
Whenever an event is created, if the server has a role with the word "Ping" in its name, and the rest of the role's name is contained in the event name or description, then JENOVA will ping that role and send them information about the event. Additionally, JENOVA will send out another ping when the event's creator joins a voice channel within 30 minutes of the event start time.
# Periodic announcements
At certain dates and times, JENOVA will automatically post a certain file. See the full list of announcements [here](announcements.json). Additionally, JENOVA will post a daily message in the style of Kagetsu Tōya's daily messages. See the full list of daily messages [here](dailymessages.json).
### Streampause
The streampause command allows for a member to check if every member in a voice channel with them is currently present. If a user uses the streampause command while in a voice channel, JENOVA sends a message with a list of every member in the voice channel, as well as whether or not they have reacted to its message. Once everyone in the voice channel has reacted to the message, indicating that they are present, JENOVA deletes its message and notifies the person who used the command to let them know.
### Reminders
Users can set reminders for any amount of time in the future, with a message attached. Once that amount of time has passed, JENOVA will reply to the user with the message they asked to be reminded about. Other users can click a button to also be pinged when the reminder is sent.
### Music playing
Play, stop, pause, and skip audio from YouTube videos in voice channels.
### Web scraping
Retrieve Grateful Dead live show lists from [HeadyVersion](http://headyversion.com), video game deals from [IsThereAnyDeal](https://isthereanydeal.com), video game playtimes from [HowLongToBeat](https://howlongtobeat.com), anime/manga from [AniList](https://anilist.co), visual novels from [VNDB](https://vndb.org), and auctions from [eBay](https://ebay.com).
### Birthdays
Users can share their birthday. JENOVA will store the information and, at midnight EST on their birthday, send them a message wishing them a happy birthday. If the user includes an optional year, JENOVA will also calculate their age and include their age in the birthday message.
### Image editing
Generate an image in the style of Kagetsu Tōya's daily messages, by typing in a caption and choosing one of the background images.
### Reaction roles
Add a reaction role to an existing message. When someone reacts with a certain emoji, they will receive a certain role.