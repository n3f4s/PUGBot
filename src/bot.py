"""
Contains the main functionnality of the bot
and what will be imported to run it
"""

import sys
import logging
from typing import Dict, List, Set, Union, Tuple, Callable, Awaitable, Optional
from collections import OrderedDict

import urllib.request
import json

import asyncio

import discord

from guildconf import GuildConfig, LobbyVC
from btag import Btag

from messages import PlayerJoined, PlayerLeft
import helper
import pug_vc

# TODO:
# 3- test
# 4- Handle changing lobbies
# 5- fault resistance
# 6- Persistence
# 7- Config depending on server
# 8- Actual DB


def _invert_lobby_lookup(config: Dict[int, GuildConfig]) -> Dict[int, Dict[int, int]]:
    res = {}
    for (gid, cfg) in config.items():
        tmp = {}
        for lobby in cfg.lobbies.values():
            tmp[lobby.team1] = lobby.lobby
            tmp[lobby.team2] = lobby.lobby
        res[gid] = tmp
    return res


def _parse_command(message: discord.Message, content: str) -> Tuple[str, List[str]]:
    args = content.split()
    return (args[0], args[1:])


def _make_btag(btag: str) -> Optional[Btag]:
    try:
        return Btag(btag)
    except:
        return None


class MyClient(discord.Client):
    """Set up and log bot in discord"""

    def __init__(self, ref: asyncio.Queue):
        from cmd_config import CmdConfigBot, CmdConfigPrint
        from commands import Command
        from voice_channel_manager import VoiceChannelManager
        from pug_player_db import PUGPlayerDB
        super().__init__()
        self._vc_mgr = VoiceChannelManager(self)
        self.logger = logging.getLogger("Bot")
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s')
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.ref = ref
        self.config = helper.load_config()
        self.commands: Dict[str, Command] = {
            CmdConfigBot.name(): CmdConfigBot(self),
            CmdConfigPrint.name(): CmdConfigPrint(self)
        }
        self.reaction_callbacks: Dict[int,
                                      Callable[[discord.Reaction,
                                                Union[discord.Member,
                                                      discord.User]],
                                               Awaitable[bool]]] = {}

        self.players = PUGPlayerDB(self)

    @property
    def all_vc(self):
        """Return a list of all PUG related voice channels"""
        return {
            guild: [lobby for lobbyVC in cfg.lobbies.values()
                    for lobby in [lobbyVC.lobby, lobbyVC.team1, lobbyVC.team2]]
            for (guild, cfg) in self.config.items()
        }

    @property
    def invert_lobby_lookup(self):
        """Return a mapping of lobby corresponding to a team VC"""
        return _invert_lobby_lookup(self.config)

    async def on_ready(self):
        """Execute when client is ready"""
        self.logger.info('Logged on as %s!', self.user)
        for guild in self.guilds:
            if guild.id not in self.config:
                self.logger.debug('Guild %s has no config, generating default', guild.name)
                self.logger.debug('config keys: %s', ", ".join(self.config.keys()))
                self.logger.debug('guild id: %s', guild.id)
                self.config[guild.id] = GuildConfig(guild.id, {}, "%")
        helper.save_config(self.config)


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
        player = self.players.get(message.author.id)
        btag = _make_btag(message.content)
        if not player:
            self.logger.debug('%s is not in any lobby',
                              message.author.display_name)
            await message.channel.send("You aren't in any lobby, join a lobby")
        elif not btag:
            await message.channel.send("Battle tag not understood, please resend it")
        elif not await self._check_btag_exists(btag):
            await message.channel.send("Could not get player data, are you sure you input battle tag correctly (with correct capitalisation)? (e.g. PlayerName#1235)")
        elif not player.is_registered:
            await self.players.register(message.author.id)
            auth = message.author.display_name
            tags = [e.to_string() for e
                    in self.players.get(message.author.id).btags]
            mess = "{} is registered with {}".format(auth, ", ".join(tags))
            await message.channel.send(mess)
        else:
            self.logger.debug('Player %s already registered in the backend',
                              message.author.display_name)

    async def _on_command(self, message: discord.Message):
        content = message.content[1:]
        command, args = _parse_command(message, content)
        if command == "help":
            await message.channel.send("Command list: {}".format(
                ", ".join(self.commands.keys())))
        elif command in self.commands:
            await self.commands[command].execute(message, args)
        else:
            await message.channel.send("Command {} not found".format(command))

    async def on_message(self, message):
        """Execute when received message"""
        if message.author.bot:
            return
        if isinstance(message.channel, discord.DMChannel):
            await self.on_dm(message)
        if isinstance(message.channel, discord.TextChannel):
            guild = message.guild.id
            if message.content[0] == self.config[guild].prefix:
                await self._on_command(message)

    async def on_reaction_add(self, reaction: discord.Reaction,
                              user: Union[discord.Member, discord.User]):
        """Triggered when adding reaction on message"""
        if user.bot:
            return
        if reaction.message.id not in self.reaction_callbacks:
            return
        if await self.reaction_callbacks[reaction.message.id](reaction, user):
            del self.reaction_callbacks[reaction.message.id]

    def _come_from_team_vc(self, guild: int, before: int, after: int) -> bool:
        """Test if the player is moving from
        a team VC to the corresponding lobby VC"""
        for lobby in self.config[guild].lobbies.values():
            if lobby.lobby == after and before in (lobby.team1, lobby.team2):
                return True
        return False

    async def send_registration_dm(self, mem: discord.Member):
        """Send a DM to a player to ask for their btag"""
        dm_chan = await mem.create_dm()
        await dm_chan.send("Give me your battle tag:")

    async def _handle_joining_lobby(self, mem: discord.Member,
                                    before: pug_vc.Other,
                                    after: pug_vc.Lobby):
        """
        Handle player joining a lobby
        - If come from team VC from same lobby, do nothing
        - If isn't in `players`, add the PUGPlayerStatus, send the DM
        - If has status and is_registered, change lobby and notify
        - If has status and not is_registered, re-send DM
        """
        before_id = before.voice_chan
        self.logger.info("%s moved from %s to %s",
                         mem.display_name,
                         before_id.name if before_id else "No VC",
                         after.voice_chan.name)
        if not self.players.is_registered(mem.id):
            await self.players.start_registration(mem, after.voice_chan,
                                                  OrderedDict())
        else:
            await self.players.register(mem.id, after.voice_chan)

    def _get_pugs_lobby(self, channel: discord.VoiceChannel):
        """Gets PUGs lobby of discord channel"""
        for lobby in self.config[channel.guild.id].lobbies.values():
            if channel.id in [lobby.lobby, lobby.team1, lobby.team2]:
                return lobby
        return None

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
        assert isinstance(after.channel, (type(None), discord.VoiceChannel))
        assert isinstance(before.channel, (type(None), discord.VoiceChannel))

        before_wrap = pug_vc.make_vc_wrapper(self.config, before.channel)
        after_wrap = pug_vc.make_vc_wrapper(self.config, after.channel)

        if (isinstance(after_wrap, pug_vc.Other)
            and isinstance(before_wrap, pug_vc.Other)):
            # We're moving between VC unrelated to PUGS
            return

        if (isinstance(after_wrap, pug_vc.Lobby)
            and isinstance(before_wrap, pug_vc.Other)):
            # Joining a lobby for the first time
            await self._vc_mgr.on_joining_lobby(mem, before_wrap, after_wrap)

        elif (isinstance(before_wrap, (pug_vc.Lobby, pug_vc.Team))
            and isinstance(after_wrap, pug_vc.Other)):
            # Leaving a pug voice channel
            await self._vc_mgr.on_leaving_lobby(mem, before_wrap)

        elif (isinstance(before_wrap, pug_vc.Team)
            and isinstance(after_wrap, pug_vc.Lobby)
            and pug_vc.is_same_lobby(before_wrap, after_wrap)):
            # Rejoining lobby from team channel
            await self._vc_mgr.on_back_lobby(mem, before_wrap, after_wrap)

        elif (isinstance(before_wrap, pug_vc.Lobby)
            and isinstance(after_wrap, pug_vc.Team)
            and pug_vc.is_same_lobby(before_wrap, after_wrap)):
            # Joining the team VC related to the lobby we were in
            await self._vc_mgr.on_going_team_vc(mem, before_wrap, after_wrap)

        elif (isinstance(before_wrap, (pug_vc.Lobby, pug_vc.Team))
            and isinstance(after_wrap, (pug_vc.Lobby, pug_vc.Team))):
            # Changing lobby
            await self._vc_mgr.on_changing_lobby(mem, before_wrap, after_wrap)

    async def on_guild_join(self, guild):
        """Triggered when adding the bot to a guild"""
        self.config[guild.id] = GuildConfig(guild.id, {}, "%")

    async def _check_btag_exists(self, btag: Btag):
        # https://playoverwatch.com/en-us/career/pc/{}/
        #TODO: Proper header
        _hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
                'Accept-Encoding': 'none',
                'Accept-Language': 'en-US,en;q=0.8',
                'Connection': 'keep-alive' }
        try:
            query = "https://ow-api.com/v1/stats/pc/EU/{}/profile".format(btag.for_api())
            request = urllib.request.Request(query, None, _hdr)
            response = urllib.request.urlopen(request)
            response = response.read()
        except urllib.error.HTTPError:
            return False
        data = json.loads(response.decode('utf-8'))
        return 'name' in data.keys()
