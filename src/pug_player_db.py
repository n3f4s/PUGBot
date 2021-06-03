"""
Define class handling player database for the bot
"""

import discord
from typing import OrderedDict, Union, Optional
from btag import Btag
from bot import MyClient
from messages import PlayerJoined

class PUGPlayerStatus:
    """ Group info regarding a player status when they're in a VC"""
    def __init__(self, member: discord.Member,
                 channel: discord.VoiceChannel,
                 btags: OrderedDict[Btag, bool]):
        self.member = member
        self.channel: Union[discord.VoiceChannel, None] = channel
        self.btags = btags
        self.is_registered = False

    def add_btag(self, btag: Btag):
        if self.btags.get(btag):
            del self.btags[btag]
        self.btags[btag] = True

    def leave_channel(self):
        self.channel = None


class PUGPlayerDB:
    """Helper class facilitating management of list of PUG players"""
    def __init__(self, client: MyClient):
        self._client = client
        self._players: dict[int, PUGPlayerStatus] = {}

    def get(self, did: int) -> Optional[PUGPlayerStatus]:
        if did in self._players:
            return self._players[did]
        return None

    def is_registered(self, did: int) -> bool:
        player = self.get(did)
        if player:
            return player.is_registered
        return False

    def is_in_lobby(self, did: int) -> bool:
        player = self.get(did)
        if player:
            if player.channel:
                return player.is_registered
        return False

    async def start_registration(self, member: discord.Member,
                                 channel: discord.VoiceChannel,
                                 btags: OrderedDict[Btag, bool]):
        self._players[member.id] = PUGPlayerStatus(member, channel, btags)
        await self._client.send_registration_dm(member)

    async def add_btag(self, did: int, btag: Btag):
        player = self.get(did)
        assert(player)
        player.add_btag(btag)

    async def register(self, did: int,
                       channel: Optional[discord.VoiceChannel]=None):
        player = self.get(did)
        assert(player)
        if channel:
            player.channel = channel
        assert(player.channel)
        server_id = player.channel.guild.id
        lobby_name = self._client._get_pugs_lobby(player.channel).name
        await self._client.ref.put(PlayerJoined("{}".format(player.member.id),
                                                player.btags,
                                                server_id,
                                                lobby_name,
                                                nick=player.member.display_name))
        player.is_registered = True
