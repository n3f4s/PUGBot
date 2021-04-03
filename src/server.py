""" Server """

from queue import Queue
import json
import time
import os
import pkgutil
import asyncio
import bot

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
            {
                "id": "discord.0",
                "title": "player A",
                "group": "waiting",
                "profileData": getOverwatchProfile("bnet.0"),
            },
            {
                "id": "discord.1",
                "title": "player B",
                "group": "waiting",
                "profileData": getOverwatchProfile("bnet.1"),
            },
            {
                "id": "discord.2",
                "title": "player C",
                "group": "waiting",
                "profileData": getOverwatchProfile("bnet.2"),
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

        return False

    def listenForUpdates(self):
        return self.messageBus.listen()

    def _broadcast(self, msg):
        msg = json.dumps(msg)
        self.messageBus.broadcast(msg)

    def playerJoin(self, playerId, bnetId):
        playerData = {
            "id": playerId,
            "title": playerId,
            "group": "waiting",
            "profileData": getOverwatchProfile(bnetId)
        }
        if self._addPlayer(playerData):
            self._broadcast({
                    "event": "player-join",
                    "data": {"playerData": playerData},
                } )
            print({
                    "event": "player-join",
                    "data": {"playerData": playerData},
                })
            return True
        else:
            return False

    def playerLeave(self, playerId):
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


def getOverwatchProfile(bnetId):
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


class EscapedFlask(Quart):
    jinja_options = Quart.jinja_options.copy()
    jinja_options.update(dict( variable_start_string='%%', variable_end_string='%%'))


def make_app():
    """ Generate the app object with the right options depending on how we execute the script"""
    if __name__ == "__main__":
        return EscapedFlask(__name__, template_folder = os.path.join("..", "templates"))
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
        from flask import render_template
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
async def boradcastLobbyUpdates():
    def stream():
       listener = lobby.listenForUpdates()  # returns a queue.Queue
       while True:
           msg = listener.get()
           yield "data: {}\n\n".format(msg)
    response = Response(stream(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache';
    response.headers['X-Accel-Buffering'] = 'no';
    return response
   
@app.route('/lobbyupdates', methods=['POST'])
async def processLobbyUpdates():
    msg = await request.data.decode("utf-8")

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
        return await send_from_directory(os.path.join("..", "assets"), path)
    else:
        return pkgutil.get_data(__name__, os.path.join("assets", path))


# Test stuff for testing
@app.route('/sse-test')
async def ssetestpage():
    return render_template('sse_test.html')


counter = 0


@app.route('/sse-testevents')
async def ssetestevents():
    def eventStream():
        time.sleep(3)
        while True:
            global counter
            time.sleep(0.1)
            counter += 1
            yield "data: {}\n\n".format(counter)
    return Response(eventStream(), mimetype="text/event-stream")


async def read_queue(queue: asyncio.Queue):
    while True:
        message = await queue.get()
        if isinstance(message, bot.PlayerJoined):
            lobby.playerJoin(message.player, message.btags[0].to_string())


async def run():
    await app.run_task(port=63083)


async def main(queue: asyncio.Queue):
    await asyncio.gather(
        run(),
        read_queue(queue)
    )


if __name__ == "__main__":
    async.run(main())
