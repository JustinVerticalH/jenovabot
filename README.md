# JENOVA
JENOVABot, or just JENOVA, is a multi-purpose Discord bot built with various utility commands, co-written by Justin Levine and Noah Levitt.
## Features
### Reminders
Users can set reminders for any amount of time in the future, with a message attached to the reminder. Once that amount of time has passed, JENOVA will reply to the user with the message they asked to be reminded about. Other users can react with a :+1: emoji to also be pinged when the reminder is sent.
### Music playing commands
Play, stop, pause, and skip audio from YouTube videos in voice channels. Soundcloud and Spotify support coming soon.
### Streampause
The streampause command allows for a member to check if every member in a voice channel with them is currently present. If a user uses the streampause command while in a voice channel, JENOVA sends a message with a list of every member in the voice channel, as well as whether or not they have reacted to its message. Once everyone in the voice channel has reacted to the message, indicating that they are present, JENOVA deletes its message and notifies the person who used the command to let them know.
### Event alerts
Whenever an event is created, if the server has a role with the word "Ping" in its name, and the rest of the role's name is contained in the event name, then JENOVA will notify that role and send them information about the event. Additionally, JENOVA will send out another notification when the event's creator joins a voice channel within 30 minutes of the event start time.
### Web scraping
Retrieve Grateful Dead live show lists from http://headyversion.com, video game playtimes from https://howlongtobeat.com/, and TV show information from https://anilist.co.
### Birthdays
Users can share their birthday. JENOVA will store the information and, at midnight EST on their birthday, send them a message wishing them a happy birthday. If the user includes an optional year, JENOVA will also calculate their age and include their age in the birthday message.