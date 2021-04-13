"""
Contains the main functionnality of the bot
and what will be imported to run it
"""

import sys
import logging
from typing import Dict, List, Union
import asyncio

import discord

from guildconf import GuildConfig, LobbyVC
from btag import Btag

from messages import PlayerJoined, PlayerLeft

# TODO:
# 1- check that nothing is broken
# 3.3- test
# 3.4- handle player leaving
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
    """ Group info regarding a player status when they're in a VC"""
    def __init__(self, member: discord.Member,
                 lobby: discord.VoiceChannel,
                 btags: List[Btag]):
        self.member = member
        self.lobby: Union[discord.VoiceChannel, None] = lobby
        self.btags = btags
        self.is_registered = False


def _invert_lobby_lookup(config: Dict[int, GuildConfig]) -> Dict[int, Dict[int, int]]:
    res = {}
    for (gid, cfg) in config.items():
        tmp = {}
        for lobby in cfg.lobbies:
            tmp[lobby.team1] = lobby.lobby
            tmp[lobby.team2] = lobby.lobby
        res[gid] = tmp
    return res


class MyClient(discord.Client):
    """Set up and log bot in discord"""

    def __init__(self, ref: asyncio.Queue):
        super().__init__()
        self.logger = logging.getLogger("Bot")
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s')
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.ref = ref

    players: Dict[int, PUGPlayerStatus] = {}
    all_vc: Dict[int, List[int]] = {
        guild: [lobby for lobbyVC in cfg.lobbies
                for lobby in [lobbyVC.lobby, lobbyVC.team1, lobbyVC.team2]]
        for (guild, cfg) in CONFIG.items()
    }
    invert_lobby_lookup = _invert_lobby_lookup(CONFIG)

    async def _on_registration(self, player: discord.Member, tags: List[Btag],
                               lobby: discord.VoiceChannel):
        """
        Function handling a player joining a VC for the first time.
        Called either after joining a VC
        if the player is already registered in the DB
        or when they give their btag to the bot
        """
        self.logger.info("%s joined lobby %s with btags %s",
                         player.display_name,
                         lobby.name,
                         ", ".join([e.to_string() for e in tags]))
        await self.ref.put(PlayerJoined("{}".format(player.id), tags))

    async def _on_leaving_lobby(self, mem: discord.Member):
        """Called when disconnecting from any VC (team or lobby)"""
        self.logger.info("%s left a PUG lobby", mem.display_name)
        self.players[mem.id].lobby = None
        self.logger.debug("Notifying backend of %s departure", mem.display_name)
        await self.ref.put(PlayerLeft("{}".format(mem.id)))

    async def _on_joining_lobby(self, mem: discord.Member,
                                before: discord.VoiceState,
                                after: discord.VoiceState):
        """Called when connecting to a lobby VC (when not connected before)"""
        # FIXME: check if all the cases have been handled
        assert(after.channel)
        self.logger.info("%s joined the PUG lobby %s",
                         mem.display_name,
                         after.channel.name)
        await self._handle_joining_lobby(mem, before, after)

    async def _on_changing_lobby(self, mem: discord.Member,
                                 before: discord.VoiceState,
                                 after: discord.VoiceState):
        assert(before.channel)
        assert(after.channel)
        self.logger.info("%s moved from %s to %s",
                         mem.display_name,
                         before.channel.name,
                         after.channel.name)
        """Called when changing from a lobby to another"""
        pass

    async def _on_going_team_vc(self, mem: discord.Member,
                                before: discord.VoiceState,
                                after: discord.VoiceState):
        """Called when going from a lobby to a team VC"""
        assert(before.channel)
        assert(after.channel)
        self.logger.info("%s went from lobby %s to team VC %s",
                         mem.display_name,
                         before.channel.name,
                         after.channel.name)
        pass

    async def _on_back_lobby(self, mem: discord.Member,
                             before: discord.VoiceState,
                             after: discord.VoiceState):
        """Called when going from a team VC
        to the corresponding lobby"""
        assert(before.channel)
        assert(after.channel)
        self.logger.info("%s went from team VC %s to lobby %s",
                         mem.display_name,
                         before.channel.name,
                         after.channel.name)
        pass

    async def on_ready(self):
        """Execute when client is ready"""
        self.logger.info('Logged on as %s!', self.user)

    async def on_dm(self, message):
        """
        When receiving a DM:
        - If the player isn't in `players` then do nothing (the player isn't in
        any discord lobby)
        - Else:
           - Add the btag
           - If the player isn't registered the notify the backend
        """
        self.logger.debug('Got DM from %s', message.author.display_name)
        if message.author.id not in self.players:
            self.logger.debug('%s is not in any lobby',
                              message.author.display_name)
            await message.channel.send("You aren't in any lobby, join a lobby")
        else:
            player = self.players[message.author.id]
            self.logger.debug('Saving btag %s for %s',
                              message.content,
                              message.author.display_name)
            try:
                player.btags.append(Btag(message.content))
            except:
                await message.channel.send("Battle tag not understood, please resend it")
                return
            if not player.is_registered:
                self.logger.debug('Notifying backend of new player %s joining VC for the first time',
                                  message.author.display_name)
                player.is_registered = True
                await self._on_registration(player.member,
                                            player.btags,
                                            player.lobby)
            await message.channel.send("{} is registered with {}"
                                       .format(message.author.display_name,
                                               ", ".join([e.to_string() for e in self.players[message.author.id].btags])))

    async def on_message(self, message):
        """Execute when received message"""
        if isinstance(message.channel, discord.DMChannel) and not message.author.bot:
            await self.on_dm(message)

    def _come_from_team_vc(self, guild: int, before: int, after: int) -> bool:
        """Test if the player is moving from a team VC to the corresponding lobby VC"""
        for lobby in CONFIG[guild].lobbies:
            if lobby.lobby == after and before in (lobby.team1, lobby.team2):
                return True
        return False

    async def _send_registration_dm(self, mem: discord.Member,
                                    after: discord.VoiceChannel):
        self.players[mem.id] = PUGPlayerStatus(mem, after, [])
        self.logger.info('Registering %s for lobby %s',
                         mem.name,
                         after.name)
        dm_chan = await mem.create_dm()
        await dm_chan.send("Give me your battle tag:")

    # FIXME: don't assume that before and after guild are the same
    async def _handle_joining_lobby(self, mem: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        """
        Handle player joining a lobby
        - If come from team VC from same lobby, do nothing
        - If isn't in `players`, add the PUGPlayerStatus, send the DM
        - If has status and is_registered, change lobby and notify
        - If has status and not is_registered, re-send DM
        """
        assert(after.channel)
        assert(isinstance(before.channel, discord.VoiceChannel))
        assert(isinstance(after.channel, discord.VoiceChannel))
        before_id = before.channel
        after_id = after.channel.id
        guild_id = after.channel.guild.id
        self.logger.info("%s moved from %s to %s",
                         mem.display_name,
                         before.channel.name if before.channel else "No VC",
                         after.channel.name)
        if before_id and self._come_from_team_vc(guild_id,
                                                 before_id.id,
                                                 after_id):
            self.logger.debug("%s come from a team lobby", mem.display_name)
        elif mem.id not in self.players:
            self.logger.debug("Sending registration DM to %s",
                              mem.display_name)
            await self._send_registration_dm(mem, after.channel)
        else:
            if self.players[mem.id].is_registered:
                self.logger.info("Moving %s to %s",
                                 mem.display_name,
                                 after.channel.name)
                self.players[mem.id].lobby = after.channel
                await self._on_registration(mem, self.players[mem.id].btags,
                                            after.channel)

            else:
                self.logger.debug("Sending registration DM to %s",
                                  mem.display_name)
                self._send_registration_dm(mem, after.channel)


    def _is_lobby(self, channel: discord.VoiceChannel) -> bool:
        return (channel.id in [vc.lobby for vc
                                in CONFIG[channel.guild.id].lobbies])

    def _is_pugs(self, channel: discord.VoiceChannel) -> bool:
        return (channel.id in self.all_vc[channel.guild.id])

    def _is_joining_lobby(self, guild_id: str,
                          before: discord.VoiceState,
                          after: discord.VoiceState) -> bool:
        """Return true if the member is connecting for the first time in a VC
        or change VC from a VC unrelated to pugs"""
        assert(isinstance(before.channel, discord.VoiceChannel))
        assert(isinstance(after.channel, discord.VoiceChannel))
        gid = int(guild_id)
        vcs = self.all_vc[gid]
        is_lobby = self._is_lobby(after.channel)
        return (True if not before.channel and is_lobby
                else (before.channel.id not in vcs
                      and is_lobby))

    def _is_lobby_team_vc(self,
                          team: discord.VoiceChannel,
                          lobby: discord.VoiceChannel) -> bool:
        """Return true if team is one of the team VC corresponding to the lobby lobby"""
        return (team.id in self.invert_lobby_lookup[team.guild.id]
                and self.invert_lobby_lookup[team.guild.id][team.id] == lobby.id)

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

        # Type checking and making mypy happy
        if not isinstance(before.channel, (type(None), discord.VoiceChannel)):
            return
        if not isinstance(after.channel, (type(None), discord.VoiceChannel)):
            return
        assert(isinstance(after.channel, (type(None), discord.VoiceChannel)))
        assert(isinstance(before.channel, (type(None), discord.VoiceChannel)))


        if (not after.channel
            and (not before.channel
                 or not self._is_pugs(before.channel))):
            # We're not leaving a VC related to pugs
            return
        if (before.channel
            and after.channel
            and not self._is_pugs(before.channel)
            and not self._is_pugs(after.channel)):
            # We're moving from and to hannels unrelated to pugs
            return
        if (after.channel and not before.channel
            and not self._is_pugs(after.channel)):
            # We're joining a channel unrelated to pugs
            return

        if (after.channel
            and self._is_joining_lobby("{}".format(after.channel.guild.id),
                                       before,
                                       after)):
            # Joining a lobby for the first time
            await self._on_joining_lobby(mem, before, after)

        if (not (after.channel and self._is_pugs(after.channel))
            and (before.channel and self._is_pugs(before.channel))):
            # Leaving a pug voice channel
            await self._on_leaving_lobby(mem)
            return

        if (after.channel and before.channel
            and self._is_lobby_team_vc(before.channel, after.channel)):
            # Rejoining lobby from team channel
            await self._on_back_lobby(mem, before, after)
            return

        if (after.channel and before.channel
            and self._is_lobby_team_vc(after.channel, before.channel)):
            # Joining the team VC related to the lobby we were in
            await self._on_going_team_vc(mem, before, after)
            return

        if (after.channel and before.channel
            and before.channel in self.all_vc[before.channel.guild.id]
            and before.channel.id != after.channel.id
            and not self._is_lobby_team_vc(before.channel, after.channel)
            and not self._is_lobby_team_vc(after.channel, before.channel)):
            # Changing lobby
            await self._on_changing_lobby(mem, before, after)
            return
