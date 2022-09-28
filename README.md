# JENOVA
JENOVABot, or just JENOVA, is a multi-purpose Discord bot built primarily for one specific server, co-written by Justin Levine and Noah Levitt.
## Features

JENOVA's features include:
- Music playing commands: Play, stop, pause, and skip music in voice channels.
- Streampause: If a member uses the streampause command while in a voice channel, JENOVA sends a message. Once everyone in the voice channel has reacted to the message, indicating that they are present, JENOVA pings the member who sent the command to let them know.
- Event alerts: Whenever an event is created, if the server has a role with the word "Ping" in its name, and the rest of the role's name is contained in the event name, then JENOVA will ping that role. Additionally, JENOVA will send out another ping when the event's creator joins a voice channel within 30 minutes of the event start time.
- Reminders: Users can set reminders for any amount of time in the future, with a message attached to the reminder. Once that amount of time has passed, JENOVA will reply to the user with the message they asked to be reminded about. Other users can react with a :+1: emoji to also be pinged when the reminder is sent.
