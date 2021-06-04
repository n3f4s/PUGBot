"""Define messages between bot and backend"""

from typing import Optional
from collections import OrderedDict
from btag import Btag

#Could probably move this to ABC

class PlayerJoined:
    """Data struct used for message passing"""
    def __init__(self,
                 player: str,
                 btags: OrderedDict[Btag, bool],
                 server_id: int,
                 lobby_name: str,
                 nick: Optional[str] = None):
        self.player = player
        self.btags = btags
        self.server_id = server_id
        self.lobby_name = lobby_name
        self.nick = nick


class PlayerLeft:
    """Data struct used for message passing"""
    def __init__(self, player: str, server_id: int, lobby_name: str):
        self.player = player
        self.server_id = server_id
        self.lobby_name = lobby_name
