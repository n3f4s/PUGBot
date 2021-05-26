"""
Wrapper around discord voice channel to add
PUG-related information
"""

from typing import Union, Dict, Optional
from dataclasses import dataclass
import discord
from guildconf import GuildConfig


@dataclass
class LobbyVC():
    """Represent a PUG lobby VC"""
    voice_chan: discord.VoiceChannel
    lobby_name: str


@dataclass
class TeamVC():
    """Represent a PUG team VC"""
    voice_chan: discord.VoiceChannel
    lobby_name: str


@dataclass
class OtherVC():
    """Represent either a VC that is neither a lobby or (pug) team VC
    or represent the absence of VC"""
    voice_chan: Optional[discord.VoiceChannel]


def make_vc_wrapper(config: Dict[str, GuildConfig],
                    vchan: Optional[discord.VoiceChannel]) -> Union[LobbyVC,
                                                                    TeamVC,
                                                                    OtherVC]:
    """Make a wrapper from "raw" discord VC"""
    if not vchan:
        return OtherVC(vchan)
    for guild in config.values():
        for name, lobby in guild.lobbies.items():
            if vchan.id == lobby.lobby:
                return LobbyVC(vchan, name)
            if vchan.id == lobby.team1:
                return TeamVC(vchan, name)
            if vchan.id == lobby.team2:
                return TeamVC(vchan, name)
    return OtherVC(vchan)


def is_same_lobby(vchan1: Union[LobbyVC, TeamVC, OtherVC],
                  vchan2: Union[LobbyVC, TeamVC, OtherVC]) -> bool:
    """Return true if both voice channel belong to the same PUG lobby"""
    if isinstance(vchan1, LobbyVC) or isinstance(vchan2, TeamVC):
        return vchan1.lobby_name == vchan2.lobby_name
    if isinstance(vchan1, TeamVC) or isinstance(vchan2, LobbyVC):
        return vchan1.lobby_name == vchan2.lobby_name
    if isinstance(vchan1, TeamVC) or isinstance(vchan2, TeamVC):
        return vchan1.lobby_name == vchan2.lobby_name
    return False
