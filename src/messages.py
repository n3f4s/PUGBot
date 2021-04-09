"""Define messages between bot and backend"""

from typing import List
from btag import Btag

class PlayerJoined:
    """Data struct used for message passing"""
    def __init__(self, player: str, btags: List[Btag]):
        self.player = player
        self.btags = btags


class PlayerLeft:
    """Data struct used for message passing"""
    def __init__(self, player: str):
        self.player = player
