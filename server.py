from flask import Flask
from flask import send_from_directory, render_template, Response, request
import json
import time
import os

from queue import Queue

# https://maxhalford.github.io/blog/flask-sse-no-deps/
class MessageBus:
    def __init__(self):
        self.listeners = []

    def listen(self):
        q = Queue(maxsize=10)
        self.listeners.append(q)
        return q

    def broadcast(self, msg):
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except:
                del self.listeners[i]
                
# To get different escape characters
class EscapedFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict( variable_start_string='%%', variable_end_string='%%'))
app = EscapedFlask(__name__)
           

lobbyPlayers = [
    {
        "id": "0",
        "title": "player A",
        "group": "waiting",
        "profileData": {
            "tag": "A.tag",
            "overview": {
                "tank": {
                    "sr": 2586, 
                    "peakSr": 2856,
                    "mostPlayed": [ "dva", "zarya", "winston" ]
                },
                "damage": {
                    "sr": 2500, 
                    "peakSr": 2900,
                    "mostPlayed": [ "mcree", "ashe", "pharah" ]
                },
                "support": {
                   "sr": None, 
                    "peakSr": None,
                    "mostPlayed": [ "lucio" ]
                },
            }
        }
    },
    {
        "id": "1",
        "title": "player B",
        "group": "waiting",
        "profileData": {
            "tag": "B.tag",
            "overview": {
                "tank": {
                    "sr": 2586, 
                    "peakSr": 2856,
                    "mostPlayed": [ "dva", "zarya", "winston" ]
                },
                "damage": {
                    "sr": 2500, 
                    "peakSr": 2900,
                    "mostPlayed": [ "mcree", "ashe", "pharah" ]
                },
                "support": {
                   "sr": None, 
                    "peakSr": None,
                    "mostPlayed": [ "lucio" ]
                },
            }
        }
    },
    {
        "id": "2",
        "title": "player C",
        "group": "waiting",
        "profileData": {
            "tag": "C.tag",
            "overview": {
                "tank": {
                    "sr": 2586, 
                    "peakSr": 2856,
                    "mostPlayed": [ "dva", "zarya", "winston" ]
                },
                "damage": {
                    "sr": 2500, 
                    "peakSr": 2900,
                    "mostPlayed": [ "mcree", "ashe", "pharah" ]
                },
                "support": {
                   "sr": None, 
                    "peakSr": None,
                    "mostPlayed": [ "lucio" ]
                },
            }
        }
    }
]
           
@app.route('/')
def root():
    #message_queue.put_nowait("event: new-client\ndata: {}\n\n")
    return render_template('index.html', lobbyPlayers=lobbyPlayers)
    
lobbyUpdates = MessageBus()
    
@app.route('/lobbyupdates', methods = ['GET'])
def boradcastLobbyUpdates():
    def stream():
        listener = lobbyUpdates.listen()  # returns a queue.Queue
        while True:
            msg = listener.get()
            yield "data: {}\n\n".format(msg)
    return Response(stream(), mimetype="text/event-stream")
    
@app.route('/lobbyupdates', methods = ['POST'])
def processLobbyUpdates():
    msg = request.data.decode("utf-8")
    
    # Update lobby
    # TODO: make this not awful
    msg_json = json.loads(msg)
    msg_type = msg_json["event"]
    msg_data = msg_json["data"]
    print(msg_data)
    if msg_type == "move-player":
        movePlayer(msg_data["sourceID"], msg_data["targetGroup"])
    elif msg_type == "swap-player":
        swapPlayer(msg_data["sourceID"], msg_data["targetID"])
    
    lobbyUpdates.broadcast(msg=msg)
    return ('', 200)
    
def findPlayer(playerId):
    for player in lobbyPlayers:
        if player['id'] == playerId:
            return player
    else:
        return None

# This is kind of ewww...
def movePlayer(playerId, targetGroup):
    findPlayer(playerId)['group'] = targetGroup
    
def swapPlayer(playerId, targetId):
    player1 = findPlayer(playerId)
    player2 = findPlayer(targetId)
    player1group = player1['group']
    player1['group'] = player2['group']
    player2['group'] = player1group
        
        
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
                               
@app.route('/media/<path:path>')
def send_js(path):
    return send_from_directory('media', path)


    
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
    
    
if __name__ == "__main__":
    app.debug = True
    app.run(threaded=True)