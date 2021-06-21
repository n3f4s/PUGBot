"""
Define class handling player database for the bot
"""

import discord
import os
import json
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

    def to_json(self):
        tags = [t.full() for t in self.btags.keys()]
        mem = self.member.id
        channel = self.channel.id if self.channel else None
        return json.dumps({
            "btag": tags,
            "guild": self.member.guild.id,
            "member": mem,
            "channel": channel,
            "is_registered": self.is_registered
        })


class PUGPlayerDB:
    """Helper class facilitating management of list of PUG players"""
    def __init__(self, client: MyClient):
        self._save_path = os.environ.get('DATABASE_ROOT', ".") + "/pugplayerdb.json"
        self._client = client
        self._players: dict[int, PUGPlayerStatus] = {}

    @classmethod
    async def make(cls, client: MyClient):
        res = PUGPlayerDB(client)
        res._load()
        return res

    def get(self, did: int) -> Optional[PUGPlayerStatus]:
        if did in self._players:
            return self._players[did]
        return None

    def _save(self):
        with open(self._save_path, "w") as file:
            players = json.dumps({(d, p.to_json()) for (d, p) in self._players})
            file.write(players)

    async def _load(self):
        with open(self._save_path, "r") as file:
            content = json.loads(file)
            for id, status in content:
                guild = await self._client.fetch_guild(status["guild"])
                mem = await guild.fetch_member(status["member"])
                vc = None
                if status["channel"]:
                    for chan in guild.voice_channels:
                        if chan.id == status["channel"]:
                            vc = chan
                tags = {(Btag(tag), True) for tag in status["btag"]}
                player = PUGPlayerStatus(mem, vc, tags)
                player.is_registered = status["is_registered"]

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
        self._save()

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
        await self._client.send_link_dm(player.member,
                                        player.channel,
                                        lobby_name)
        self._save()
