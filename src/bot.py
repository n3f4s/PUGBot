"""
Contains the main functionnality of the bot
and what will be imported to run it
"""

import os, sys
import logging
from typing import Dict, List
import discord
from guildconf import GuildConfig, LobbyVC
from btag import Btag

# TODO:
# 2- setup the service file in chocolytech with the appropriate auth
# 2.5- github actions & secrets -> CI for testing and linting
# 3- logging
# 3.4- test
# 3.5- fault resistance
# 4- Persistence
# 5- integrate with backend
# 6- Actual DB

CONFIG = {
    823930184067579954: GuildConfig(823930184067579954,
                                    [LobbyVC("Test",
                                             823930184067579958,
                                             823930252526485606,
                                             823930252526485606)],
                                    "%")
 }


class PUGPlayerStatus:
    def __init__(self, member: discord.Member,
                 lobby: discord.VoiceChannel,
                 btags: List[Btag]):
        self.member = member
        self.lobby = lobby
        self.btags = btags
        self.is_registered = False


def player_joined(player: discord.Member, tags: List[Btag], lobby: discord.VoiceChannel):
    pass


class MyClient(discord.Client):
    """Set up and log bot in discord"""

    logger = logging.getLogger("Bot")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s]:  %(message)s')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    players: Dict[int, PUGPlayerStatus] = {}

    async def on_ready(self):
        """Execute when client is ready"""
        self.logger.info('Logged on as %s!', self.user)

    async def on_dm(self, message):
        """
        When receiving a DM:
        - If the player isn't in `players` then do nothing (the player isn't in any discord lobby)
        - Else:
           - Add the btag
           - If the player isn't registered the notify the backend
        """
        self.logger.debug('Got DM from %s', message.author.display_name)
        if message.author.id not in self.players:
            self.logger.debug('%s is not in any lobby', message.author.display_name)
            await message.channel.send("You are not in any lobby, join a lobby")
        else:
            player = self.players[message.author.id]
            self.logger.debug('Saving btag %s for %s',
                              message.content,
                              message.author.display_name)
            player.btags.append(Btag(message.content))
            if not player.is_registered:
                self.logger.debug('Notifying backend of new player %s joining VC for the first time',
                                  message.author.display_name)
                player.is_registered = True
                player_joined(player.member, player.btags, player.lobby)
            await message.channel.send("{} is registered with {}"
                                       .format(message.author.display_name,
                                               ", ".join([e.to_string() for e in self.players[message.author.id].btags])))

    async def on_message(self, message):
        """Execute when received message"""
        if isinstance(message.channel, discord.DMChannel) and not message.author.bot:
            self.on_dm(message)

    def _come_from_team_vc(self, guild: int, before: int, after: int) -> bool:
        """Test if the player is moving from a team VC to the corresponding lobby VC"""
        for lobby in CONFIG[guild].lobbies:
            if lobby.lobby == after and before in (lobby.team1, lobby.team2):
                return True
        return False

    async def _send_registration_dm(self, mem: discord.Member, after: discord.VoiceChannel):
        self.players[mem.id] = PUGPlayerStatus(mem, after, [])
        self.logger.info('Registering %s for lobby %s', mem.name, after.name)
        dm_chan = await mem.create_dm()
        await dm_chan.send("Give me your battle tag:")

    # FIXME: don't assume that before and after guild are the same
    def _handle_joining_lobby(self, mem: discord.Member,
                              before: discord.VoiceState,
                              after: discord.VoiceState):
        """
        Handle player joining a lobby
        - If come from team VC from same lobby, do nothing
        - If isn't in `players`, add the PUGPlayerStatus, send the DM
        - If has status and is_registered, change lobby and notify
        - If has status and not is_registered, re-send DM
        """
        before_id = before.channel.id
        after_id = after.channel.id
        guild_id = before.channel.guild.id
        if self._come_from_team_vc(guild_id, before_id, after_id):
            pass
        elif mem.id not in self.players:
            self._send_registration_dm(mem, after)
        else:
            if self.players[mem.id].is_registered:
                self.players[mem.id].lobby = after.channel
                player_joined(mem, self.players[mem.id].btags, after.channel)
            else:
                self._send_registration_dm(mem, after)

    def _handle_leaving_lobby(self, mem: discord.Member,
                              before: discord.VoiceState,
                              after: discord.VoiceState):
        """
        Handle player leaving a lobby: set the lobby to None
        """
        self.players[mem.id].lobby = None

    # FIXME:
    # 1. If someone join, mark them as "logged in"
    # 2. If someone join the wrong lobby first then join the right lobby, still ask the btag
    # 3. If someone isn't registered, mark them as needed to be registered then do the registration from DM
    # 4. If someone is registered, call the function to notify the server
    async def on_voice_state_update(self, mem: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        """
        Callback for when someone change their VC state
        if someone join a lobby voice channel then call _handle_joining_lobby
        """
        if after.channel:
            is_lobby_vc = after.channel.id in [vc.lobby for vc in CONFIG[after.channel.guild.id].lobbies]
            if is_lobby_vc:
                self._handle_joining_lobby(mem, before, after)
        elif before.channel:
            is_lobby_vc = before.channel.id in [vc.lobby for vc in CONFIG[after.channel.guild.id].lobbies]
            if is_lobby_vc:
                self._handle_leaving_lobby(mem, before, after)


client = MyClient()
client.run(os.environ['DISCORD_BOT_TOKEN'])
