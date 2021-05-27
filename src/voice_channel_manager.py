from bot import MyClient
import discord
import pug_vc
from messages import PlayerLeft


class VoiceChannelManager():
    """Class handling what happens when someone join/leave voice a voice channel"""
    def __init__(self, client: MyClient):
        self._client = client

    # FIXME: type better
    async def _on_leaving_lobby(self, mem: discord.Member, lobby: discord.VoiceChannel):
        """Called when disconnecting from any VC (team or lobby)"""
        if mem.id in self._client.players:
            self._client.logger.info("%s left a PUG lobby", mem.display_name)
            self._client.players[mem.id].lobby = None
            self._client.logger.debug("Notifying backend of %s departure", mem.display_name)

            server_id = lobby.guild.id
            lobby_name = self._client._get_pugs_lobby(lobby).name
            await self._client.ref.put(PlayerLeft("{}".format(mem.id), server_id, lobby_name))

    async def _on_joining_lobby(self, mem: discord.Member,
                                before: pug_vc.Other,
                                after: pug_vc.Lobby):
        """Called when connecting to a lobby VC (when not connected before)"""
        # FIXME: check if all the cases have been handled
        self._client.logger.info("%s joined the PUG lobby %s",
                                 mem.display_name,
                                 after.voice_chan.name)
        await self._client._handle_joining_lobby(mem, before, after)

    # FIXME: type better
    async def _on_changing_lobby(self, mem: discord.Member,
                                 before: discord.VoiceState,
                                 after: discord.VoiceState):
        """Called when changing from a lobby to another"""
        assert before.channel
        assert after.channel
        self._client.logger.info("%s moved from %s to %s",
                                 mem.display_name,
                                 before.channel.name,
                                 after.channel.name)
        pass

    # FIXME: type better
    async def _on_back_lobby(self, mem: discord.Member,
                             before: discord.VoiceState,
                             after: discord.VoiceState):
        """Called when going from a team VC
        to the corresponding lobby"""
        assert before.channel
        assert after.channel
        self._client.logger.info("%s went from team VC %s to lobby %s",
                                 mem.display_name,
                                 before.channel.name,
                                 after.channel.name)
        pass

    # FIXME: type better
    async def _on_going_team_vc(self, mem: discord.Member,
                                before: discord.VoiceState,
                                after: discord.VoiceState):
        """Called when going from a lobby to a team VC"""
        assert before.channel
        assert after.channel
        self._client.logger.info("%s went from lobby %s to team VC %s",
                                 mem.display_name,
                                 before.channel.name,
                                 after.channel.name)
        pass
