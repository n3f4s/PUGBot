""" Server """

import json
import time
import os
import pkgutil
import asyncio
import messages

from lobby import GameLobby
from typing import Dict

import jinja2
from quart import Quart
from quart import send_from_directory, Response, request, redirect


app = Quart(__name__)
lobby_ = GameLobby()
lobbies: Dict[ int, Dict[ str, GameLobby ] ] =  {}
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
    try:
        tpl = templateLoader.get_template(name)
        return tpl.render(**kwargs)
    except:
        return render_template_if_fail(name, **kwargs)


@app.route('/')
async def root():
    return redirect('/lobbies')


def get_lobby(server_id, lobby_name):
    serv = lobbies.get(server_id, None)
    if serv is None:
        return None
    else:
        return serv.get(lobby_name, None)
     
@app.route('/lobbies')
async def print_lobbies():

    res = ""
    for srv, lbs in lobbies.items():
        res += f"<br \> <h1>{srv}</h1>"
        for lb in lbs.keys():
            res += f"<li><a href='/{srv}/{lb}'>{lb}</a></li>"
            
    res += f"<br \><br \><br \>{lobbies}"
    return (res, 200)
     
@app.route('/<int:server_id>/<lobby_name>/', methods=['GET', 'POST'])
async def render_lobby(server_id, lobby_name):
    lobby = get_lobby(server_id, lobby_name)
    if lobby is None:
        return ("No lobby here :(", 404)
        
    return render_template('index.html', lobbyPlayers=lobby.lobbyPlayers)
    
    
@app.route('/<int:server_id>/<lobby_name>/lobbyupdates', methods=['GET'])
async def broadcastLobbyUpdates(server_id, lobby_name):

    lobby = get_lobby(server_id, lobby_name)
    if lobby is None:
        return ("No lobby here :(", 404)
        
    # Get a listener from the lobby
    def stream():
        listener = lobby.listenForUpdates()  # returns a queue.Queue
        while True:
            msg = listener.get()
            msg = json.dumps(msg)
            yield "data: {}\n\n".format(msg).encode('utf-8')
            
    response = Response(stream(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.timeout = None
    return response

    
@app.route('/<int:server_id>/<lobby_name>/lobbyupdates', methods=['POST'])
async def processLobbyUpdates(server_id, lobby_name):
    lobby = get_lobby(server_id, lobby_name)
    if lobby is None:
        return ("No lobby here :(", 404)
        
    tmp = await request.data
    msg = tmp.decode("utf-8")

    # Update lobby
    # TODO: make this not awful
    #       - check if function suceeded and send appropriate message
    msg = json.loads(msg)

    success = await lobby.processMessage(msg)
    if success:
        return ('', 200)
    else:
        return ('', 501)



@app.route('/favicon.ico')
async def favicon():
    return redirect('/assets/favicon.ico')


@app.route('/assets/<path:path>')
async def send_assets(path):
    try:
        return pkgutil.get_data(__name__, os.path.join("assets", path))
    except:
        # hack to get it to work without compilation
        return pkgutil.get_data(__name__, os.path.join("..", "assets", path))

        
async def read_queue(queue: asyncio.Queue):
    while True:
        message = await queue.get()
        if isinstance(message, messages.PlayerJoined):
            server_lobbies = lobbies.get(message.server_id, None)
            if server_lobbies is None:
                lobbies[message.server_id] = {}
                server_lobbies = lobbies[message.server_id]
            lobby = server_lobbies.get(message.lobby_name, None)
            if lobby is None:
                lobby = GameLobby()
                await lobby.lobbySetUp()
                lobbies[message.server_id][message.lobby_name] = lobby
            await lobby.playerJoin(message.player, list(message.btags.keys())[-1].to_string(), name=message.nick)
            
        if isinstance(message, messages.PlayerLeft):
           lobby = get_lobby(message.server_id, message.lobby_name)
           if server_lobbies is not None:
                lobby.playerLeave(message.player)
           

async def run(port, debug=False):
    await app.run_task(port=port, debug=debug)

async def main(queue: asyncio.Queue, port=8080, debug=False):
    lobbies[0] = {}
    lobbies[0]["test"] = lobby_
    await lobby_.lobbySetUp(debug=True)

    await asyncio.gather(
        run(port, debug=debug),
        read_queue(queue)
    )
