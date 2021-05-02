import asyncio

from queue import Queue

from btag import Btag
from careerstats import CareerDatabase


class MessageBus:
    """ https://maxhalford.github.io/blog/flask-sse-no-deps/"""

    def __init__(self):
        self._listeners = []

    def listen(self):
        q = Queue(maxsize=10)
        self._listeners.append(q)
        return q

    def broadcast(self, msg):
        for i in reversed(range(len(self._listeners))):
            try:
                self._listeners[i].put_nowait(msg)
            except:
                del self._listeners[i]


class GameLobby:
    def __init__(self):
        self.messageBus = MessageBus()
        self.lobbyPlayers = None
        
    async def lobbySetUp(self):    
        self.lobbyPlayers = [
                {   # Feeniks is high rank
                    "id": "dummy.0",
                    "title": "Feeniks",
                    "group": "waiting",
                    "selectedRoles": ["tank", "support"],
                    "profileData": await getOverwatchProfile("Feeniks#21541"),
                },
                {   # Joshi has placed on all roles
                    "id": "dummy.1",
                    "title": "SuperJoshi94",
                    "group": "waiting",
                    "selectedRoles": ["damage"],
                    "profileData": await getOverwatchProfile("SuperJoshi94#2645"),
                },
                {   # Lio has placed on all roles but no public profile
                    "id": "dummy.2",
                    "title": "LioKioNio",
                    "group": "waiting",
                    "selectedRoles": ["tank"],
                    "profileData": await getOverwatchProfile("LioKioNio#2969"),
                },
            ]

    async def processMessage(self, msg):
        msg_type = msg["event"]
        msg_data = msg["data"]

        # Can use a switch here
        if msg_type == "move-player":
            self._movePlayer(msg_data["sourceID"], msg_data["targetGroup"])
            self._broadcast(msg)
            return True

        elif msg_type == "swap-player":
            self._swapPlayer(msg_data["sourceID"], msg_data["targetID"])
            self._broadcast(msg)
            return True
            
        elif msg_type == "update-player":
            self._updatePlayerData(msg_data["playerID"], msg_data["updateData"])
            self._broadcast(msg)
            return True
            
        elif msg_type == "refresh-player":
            # Do it manually for now
            
            player = self._findPlayer(msg_data["playerID"])
            update = { "profileData": await getOverwatchProfile(player["profileData"]["tag"], force_update=True ) }

            self._updatePlayerData(msg_data["playerID"], update)
            self._broadcast({
                    "event": "update-player",
                    "data": { "playerID": player["id"], "updateData": update },
                })
            return True

        return False

    def listenForUpdates(self):
        return self.messageBus.listen()

    def _broadcast(self, msg):
        self.messageBus.broadcast(msg)

    async def playerJoin(self, playerId, bnetId: Btag, name=None):
        playerId = str(playerId) # kinda a hack to ensure all types are the same
        
        #Check if player already in lobby:
        if self._findPlayer(playerId):
            self.playerLeave(playerId) #just remove for now
        
        # Create new lobby player
        playerData = {
            "id": playerId,
            "title": (name if name else playerId),
            "group": "waiting",
            "selectedRoles": ["tank", "damage", "support"],
            "profileData": await getOverwatchProfile(bnetId),
        }
        if self._addPlayer(playerData):
            self._broadcast({
                    "event": "player-join",
                    "data": {"playerData": playerData},
                } )
            return True
        else:
            return False

    def playerLeave(self, playerId):
        playerId = str(playerId) # kinda a hack to ensure all types are the same
        
        if self._removePlayer(playerId):
            self._broadcast({
                    "event": "player-leave",
                    "data": {"targetID": playerId },
                })
            return True
        else:
            return False

    def _findPlayer(self, playerId, index=False):
        for i, player in enumerate(self.lobbyPlayers):
            if player['id'] == playerId:
                return i if index else player
        else:
            return None

    # TODO add a true/false return for these functions

    def _movePlayer(self, playerId, targetGroup):
        self._findPlayer(playerId)['group'] = targetGroup

    def _swapPlayer(self, playerId, targetId):
        player1 = self._findPlayer(playerId)
        player2 = self._findPlayer(targetId)
        player1group = player1['group']
        player1['group'] = player2['group']
        player2['group'] = player1group
        
    def _updatePlayerData(self, playerId, playerData):
        ind = self._findPlayer(playerId, True)
        if not ind is None:
            self.lobbyPlayers[ind].update(playerData)
            return True
        return False
        
    def _updatePlayerValue(self, playerId, key, value):
        player = self._findPlayer(playerId)
        if not player is None:
            curr_item = player
            ks = key.split(".")
            for k in ks[:-1]:
                itm = curr_item.get(k)
                if not itm is None:
                    curr_item = itm
                else:
                    curr_item[k] = {}
                    curr_item = curr_item[k]
            itm[ks[-1]] = value
            return True
        return False
           
    def _addPlayer(self, playerData):
        if self._findPlayer(self, playerData["id"]) is None:
            #TODO: Sanitise playerData
            self.lobbyPlayers.append(playerData)
            return True
        else:
            return False

    def _removePlayer(self, playerId):
        ind = self._findPlayer(playerId, True)
        if ind is None:
            return False
        else:
            _ = self.lobbyPlayers.pop(ind)
            return True

def _getOverwatchProfile(bnetId):
    profile = {
        "tag": bnetId,
        "overview": {
            "tank": {
                "sr": 2586,
                "peakSr": 2856,
                "mostPlayed": [ {"hero": "dva"}, {"hero": "zarya"}, {"hero": "winston"}]
            },
            "damage": {
                "sr": 2330,
                "peakSr": 2495,
                "mostPlayed": [{"hero": "mccree"}, {"hero": "ashe"}, {"hero": "pharah"}]
            },
            "support": {
                "sr": None,
                "peakSr": 3216,
                "mostPlayed": [{"hero": "lucio"}]
            },
        },
    }
    return profile

careerDatabase = CareerDatabase()
async def getOverwatchProfile(btag: Btag, force_update=False):
    stats = await careerDatabase.getStats(Btag(btag), force_update)
    return stats.__getFormattedHack__()
