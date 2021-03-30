"""
Contains the main functionnality of the bot
and what will be imported to run it
"""

import discord
import logging
import requests
from typing import Dict, List
from guildconf import GuildConfig, LobbyVC
from btag import Btag

# TODO:
# 1- setup the service file in chocolytech with the appropriate auth
# 2- split code in files
# 3- have a basic that handle:
#   - someone joining pugs for the first time
#   - someone join pugs not for the first time
# 4- github actions & secrets -> CI for testing and linting

CONFIG = {
    823930184067579954: GuildConfig(823930184067579954,
                                    [LobbyVC("Test",
                                             823930184067579958,
                                             823930252526485606,
                                             823930252526485606)],
                                    "%")
 }

players: Dict[int, List[Btag]] = {}


class MyClient(discord.Client):
    """Set up and log bot in discord"""

    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)

    async def on_ready(self):
        """Execute when client is ready"""
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        """Execute when received message"""
        if isinstance(message.channel, discord.DMChannel) and not message.author.bot:
            if message.author.id not in players:
                players[message.author.id] = []
            players[message.author.id].append(Btag(message.content))
            await message.channel.send("{} is registered with {}"
                                       .format(message.author.display_name,
                                               ", ".join([e.to_string() for e in players[message.author.id] ])))

    async def on_voice_state_update(self, mem: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        """Callback for when someone change their VC state"""
        # FIXME:
        # 1. If someone join, mark them as "logged in"
        # 2. If someone join the wrong lobby first then join the right lobby, still ask the btag
        # 3. If someone isn't registered, mark them as needed to be registered then do the registration from DM
        # 4. If someone is registered, call the function to notify the server
        if not before.channel and after.channel and mem.id not in players:
            is_lobby_vc = after.channel.id in [vc.lobby for vc in CONFIG[after.channel.guild.id].lobbies]
            if is_lobby_vc:
                dm_chan = await mem.create_dm()
                await dm_chan.send("Give me your battle tag:")
                print("Registering {} for lobby {}"
                      .format(mem.name, after.channel.name))


client = MyClient()
client.run('TOKEN')
