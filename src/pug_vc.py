"""
Wrapper around discord voice channel to add
PUG-related information
"""

from typing import Union, Dict, Optional
from dataclasses import dataclass
import discord
from guildconf import GuildConfig


@dataclass
class Lobby():
    """Represent a PUG lobby VC"""
    voice_chan: discord.VoiceChannel
    lobby_name: str


@dataclass
class Team():
    """Represent a PUG team VC"""
    voice_chan: discord.VoiceChannel
    lobby_name: str


@dataclass
class Other():
    """Represent either a VC that is neither a lobby or (pug) team VC
    or represent the absence of VC"""
    voice_chan: Optional[discord.VoiceChannel]


def make_vc_wrapper(config: Dict[str, GuildConfig],
                    vchan: Optional[discord.VoiceChannel]) -> Union[Lobby,
                                                                    Team,
                                                                    Other]:
    """Make a wrapper from "raw" discord VC"""
    if not vchan:
        return Other(vchan)
    for guild in config.values():
        for name, lobby in guild.lobbies.items():
            if vchan.id == lobby.lobby:
                return Lobby(vchan, name)
            if vchan.id == lobby.team1:
                return Team(vchan, name)
            if vchan.id == lobby.team2:
                return Team(vchan, name)
    return Other(vchan)


def is_same_lobby(vchan1: Union[Lobby, Team, Other],
                  vchan2: Union[Lobby, Team, Other]) -> bool:
    """Return true if both voice channel belong to the same PUG lobby"""
    if isinstance(vchan1, Lobby) and isinstance(vchan2, Team):
        return vchan1.lobby_name == vchan2.lobby_name
    if isinstance(vchan1, Team) and isinstance(vchan2, Lobby):
        return vchan1.lobby_name == vchan2.lobby_name
    if isinstance(vchan1, Team) and isinstance(vchan2, Team):
        return vchan1.lobby_name == vchan2.lobby_name
    return False
