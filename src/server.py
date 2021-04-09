""" Server """

from queue import Queue
import json
import time
import os
import pkgutil
import asyncio
import messages

from btag import Btag
from careerstats import CareerDatabase

import jinja2
from quart import Quart
from quart import send_from_directory, Response, request


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
        self.lobbyPlayers = [
            {   # Feeniks is high rank
                "id": "dummy.0",
                "title": "Feeniks",
                "group": "waiting",
                "selectedRoles": ["tank", "support"],
                "profileData": getOverwatchProfile("Feeniks#21541"),
            },
            {   # Joshi has placed on all roles
                "id": "dummy.1",
                "title": "SuperJoshi94",
                "group": "waiting",
                "selectedRoles": ["damage"],
                "profileData": getOverwatchProfile("SuperJoshi94#2645"),
            },
            {   # Lio has placed on all roles but no public profile
                "id": "dummy.2",
                "title": "LioKioNio",
                "group": "waiting",
                "selectedRoles": ["tank"],
                "profileData": getOverwatchProfile("LioKioNio#2969"),
            },
        ]
        

    def processMessage(self, msg):
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
            update = { "profileData": getOverwatchProfile(player["profileData"]["tag"], force_update=True ) }
            print(update)
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
        msg = json.dumps(msg)
        self.messageBus.broadcast(msg)

    def playerJoin(self, playerId, bnetId):
        playerId = str(playerId) # kinda a hack to ensure all types are the same
        
        #Check if player already in lobby:
        if self._findPlayer(playerId):
            self.playerLeave(playerId) #just remove for now
        
        # Create new lobby player
        playerData = {
            "id": playerId,
            "title": playerId,
            "group": "waiting",
            "selectedRoles": ["tank", "damage", "support"],
            "profileData": getOverwatchProfile(bnetId)
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
                "mostPlayed": ["dva", "zarya", "winston"]
            },
            "damage": {
                "sr": 2330,
                "peakSr": 2495,
                "mostPlayed": ["mccree", "ashe", "pharah"]
            },
            "support": {
               "sr": None,
                "peakSr": 3216,
                "mostPlayed": ["lucio"]
            },
        },
    }
    return profile

careerDatabase = CareerDatabase()
def getOverwatchProfile(btag, force_update=False):
    return careerDatabase.getStats(Btag(btag), force_update).__getFormattedHack__()



def make_app():
    """ Generate the app object with the right options depending on how we execute the script"""
    if __name__ == "__main__":
        class EscapedQuart(Quart):
            jinja_options = Quart.jinja_options.copy()
            jinja_options.update(dict( variable_start_string='%%', variable_end_string='%%'))
            
        return EscapedQuart(__name__, template_folder = os.path.join("..", "templates"))
    else:
        return Quart(__name__)


app = make_app()
lobby = GameLobby()
templateLoader = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'),
    autoescape=jinja2.select_autoescape(['html', 'xml']),
    variable_start_string='%%',
    variable_end_string='%%'
)


def load_template(name):
    data = pkgutil.get_data(__name__, os.path.join('templates', name))
    return data


def render_template_if_fail(name, **kwargs):
    data = load_template(name).decode()
    tpl = templateLoader.from_string(data)
    return tpl.render(**kwargs)


def render_template(name, **kwargs):
    """ Look for template either in file or archive depending on how we execute the script """
    if __name__ == "__main__":
        from quart import render_template
        return render_template(name, **kwargs)
    else:
        try:
            tpl = templateLoader.get_template(name)
            return tpl.render(**kwargs)
        except:
            return render_template_if_fail(name, **kwargs)


@app.route('/')
async def root():
    return render_template('index.html', lobbyPlayers=lobby.lobbyPlayers)


@app.route('/lobbyupdates', methods=['GET'])
async def broadcastLobbyUpdates():

    def stream():
        listener = lobby.listenForUpdates()  # returns a queue.Queue
        while True:
            msg = listener.get()
            yield "data: {}\n\n".format(msg).encode('utf-8')
            
    response = Response(stream(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache';
    response.headers['X-Accel-Buffering'] = 'no';
    return response

@app.route('/lobbyupdates', methods=['POST'])
async def processLobbyUpdates():
    tmp = await request.data
    msg = tmp.decode("utf-8")

    # Update lobby
    # TODO: make this not awful
    #       - check if function suceeded and send appropriate message
    msg = json.loads(msg)

    success = lobby.processMessage(msg)
    if success:
        return ('', 200)
    else:
        return ('', 501)


@app.route('/favicon.ico')
async def favicon():
    return await send_from_directory(os.path.join("..", "assets"),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/assets/<path:path>')
async def send_assets(path):
    if __name__ == "__main__":
        return await send_from_directory(os.path.join("assets"), path)
    else:
        try:
            return pkgutil.get_data(__name__, os.path.join("assets", path))
        except:
            # hack to get igit at to work without compilation
            return pkgutil.get_data(__name__, os.path.join("..", "assets", path))


async def read_queue(queue: asyncio.Queue):
    while True:
        message = await queue.get()
        if isinstance(message, messages.PlayerJoined):
            lobby.playerJoin(message.player, message.btags[0].to_string())
        if isinstance(message, messages.PlayerLeft):
            lobby.playerLeave(message.player)


async def run(port):
    await app.run_task(port=port)


async def main(queue: asyncio.Queue, port=8080):
    await asyncio.gather(
        run(port),
        read_queue(queue)
    )


if __name__ == "__main__":
    app.run(debug=True)
