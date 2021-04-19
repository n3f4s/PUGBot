"""Define messages between bot and backend"""

from typing import Optional
from collections import OrderedDict
from btag import Btag

class PlayerJoined:
    """Data struct used for message passing"""
    def __init__(self, player: str, btags: OrderedDict[Btag, bool], nick: Optional[str] = None):
        self.player = player
        self.btags = btags
        self.nick = nick


class PlayerLeft:
    """Data struct used for message passing"""
    def __init__(self, player: str):
        self.player = player
