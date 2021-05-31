from typing import Union
from bot import MyClient
import discord
import pug_vc
from messages import PlayerLeft


class VoiceChannelManager():
    """Class handling what happens when someone join/leave voice a voice channel"""
    def __init__(self, client: MyClient):
        self._client = client

    async def on_leaving_lobby(self, mem: discord.Member, lobby: Union[pug_vc.Team, pug_vc.Lobby]):
        """Called when disconnecting from any VC (team or lobby)"""
        player = self._client.players.get(mem.id)
        if player:
            self._client.logger.info("%s left a PUG lobby", mem.display_name)
            player.lobby = None
            self._client.logger.debug("Notifying backend of %s departure",
                                      mem.display_name)

            server_id = lobby.voice_chan.guild.id
            lobby_name = self._client._get_pugs_lobby(lobby.voice_chan).name
            await self._client.ref.put(PlayerLeft("{}".format(mem.id),
                                                  server_id, lobby_name))

    async def on_joining_lobby(self, mem: discord.Member,
                               before: pug_vc.Other,
                               after: pug_vc.Lobby):
        """Called when connecting to a lobby VC (when not connected before)"""
        # FIXME: check if all the cases have been handled
        self._client.logger.info("%s joined the PUG lobby %s",
                                 mem.display_name,
                                 after.voice_chan.name)
        await self._client._handle_joining_lobby(mem, before, after)

    async def on_changing_lobby(self, mem: discord.Member,
                                before: Union[pug_vc.Lobby, pug_vc.Team],
                                after: Union[pug_vc.Lobby, pug_vc.Team]):
        """Called when changing from a lobby to another"""
        self._client.logger.info("%s moved from %s to %s",
                                 mem.display_name,
                                 before.voice_chan.name,
                                 after.voice_chan.name)
        self._client.logger.critical("Moving between lobbies not implemented")

    async def on_back_lobby(self, mem: discord.Member,
                            before: pug_vc.Team,
                            after: pug_vc.Lobby):
        """Called when going from a team VC
        to the corresponding lobby"""
        self._client.logger.info("%s went from team VC %s to lobby %s",
                                 mem.display_name,
                                 before.voice_chan.name,
                                 after.voice_chan.name)
        self._client.logger.critical("team -> lobby not implemented")

    async def on_going_team_vc(self, mem: discord.Member,
                               before: pug_vc.Lobby,
                               after: pug_vc.Team):
        """Called when going from a lobby to a team VC"""
        self._client.logger.info("%s went from lobby %s to team VC %s",
                                 mem.display_name,
                                 before.voice_chan.name,
                                 after.voice_chan.name)
        self._client.logger.critical("lobby -> team not implemented")
