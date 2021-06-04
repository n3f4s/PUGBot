""" Represent the config for a discord server (VC, ...) """
from typing import List, Dict


class LobbyVC:
    def __init__(self, name: str, lobby: int, team1: int, team2: int):
        self.name = name
        self.lobby = lobby
        self.team1 = team1
        self.team2 = team2


class GuildConfig:
    def __init__(self, guild: int, lobbies: Dict[str, LobbyVC], prefix: str):
        self.guild_id = guild
        self.lobbies = lobbies
        self.prefix = prefix
