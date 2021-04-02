""" Server """

from queue import Queue
import json
import time
import os
import pkgutil

import jinja2
from flask import Flask
from flask import send_from_directory, Response, request


class MessageBus:
    def __init__(self):
        self._listeners = []

    # https://maxhalford.github.io/blog/flask-sse-no-deps/
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
            
        #For testing only!
        #elif msg_type == "player-leave":
        #    self.playerLeave(msg_data["targetID"])
        #    return True
            
        #For testing only!
        #elif msg_type == "player-join":
        #    self.playerJoin("FAKEUSER", "FAKEBNET")
        #    return True
            
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
            self._broadcast( {
                    "event": "player-join",
                    "data": { "playerData": playerData },
                } )
            print( {
                    "event": "player-join",
                    "data": { "playerData": playerData },
                } )
            return True
        else:
            return False
        
    def playerLeave(self, playerId):
        if self._removePlayer(playerId):
            self._broadcast( {
                    "event": "player-leave",
                    "data": { "targetID": playerId },
                } )
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
                "mostPlayed": [ "dva", "zarya", "winston" ]
            },
            "damage": {
                "sr": 2330, 
                "peakSr": 2495,
                "mostPlayed": [ "mccree", "ashe", "pharah" ]
            },
            "support": {
               "sr": None, 
                "peakSr": 3216,
                "mostPlayed": [ "lucio" ]
            },
        },
    }
    return profile
    
class EscapedFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict( variable_start_string='%%', variable_end_string='%%'))


def make_app():
    """ Generate the app object with the right options depending on how we execute the script"""
    if __name__ == "__main__":
        return EscapedFlask(__name__, template_folder = os.path.join("..", "templates"))
    else:
        return Flask(__name__)
app = make_app()

lobby = GameLobby()
templateLoader = jinja2.Environment(
    loader = jinja2.FileSystemLoader('templates'),
    autoescape = jinja2.select_autoescape(['html', 'xml']),
    variable_start_string='%%',
    variable_end_string='%%'
)


def render_template(name, **kwargs):
    """ Look for template either in file or archive depending on how we execute the script """
    if __name__ == "__main__":
        from flask import render_template
        return render_template(name, **kwargs)
    else:
        tpl = templateLoader.get_template(name)
        return tpl.render(**kwargs)


@app.route('/')
def root():
    #message_queue.put_nowait("event: new-client\ndata: {}\n\n")
    return render_template('index.html', lobbyPlayers=lobby.lobbyPlayers)
    
@app.route('/lobbyupdates', methods = ['GET'])
def boradcastLobbyUpdates():
    def stream():
        listener = lobby.listenForUpdates()  # returns a queue.Queue
        while True:
            msg = listener.get()
            yield "data: {}\n\n".format(msg)
    return Response(stream(), mimetype="text/event-stream")
    
@app.route('/lobbyupdates', methods = ['POST'])
def processLobbyUpdates():
    msg = request.data.decode("utf-8")
    
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
def favicon():
    return send_from_directory(os.path.join("..", "assets"),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/assets/<path:path>')
def send_assets(path):
    if __name__ == "__main__":
        return send_from_directory(os.path.join("..", "assets"), path)
    else:
        return pkgutil.get_data(__name__, os.path.join("assets", path))



    
# Test stuff for testing
@app.route('/sse-test')
def ssetestpage():
    return render_template('sse_test.html')
    
counter = 0
@app.route('/sse-testevents')
def ssetestevents():
    def eventStream():
        time.sleep(3)
        while True:
            global counter
            time.sleep(0.1)
            counter += 1
            yield "data: {}\n\n".format(counter)
    return Response(eventStream(), mimetype="text/event-stream")


def main():
    """Entry point for the pyz archive"""
    app.run(threaded=True)


if __name__ == "__main__":
    main()
