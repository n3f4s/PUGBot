""" Server """

import json
import time
import os
import pkgutil
import asyncio
import messages

from lobby import GameLobby

import jinja2
from quart import Quart
from quart import send_from_directory, Response, request, redirect


app = Quart(__name__)
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

@app.route('/lobbyupdates', methods=['POST'])
async def processLobbyUpdates():
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
            await lobby.playerJoin(message.player, list(message.btags.keys())[-1].to_string(), name=message.nick)
        if isinstance(message, messages.PlayerLeft):
            lobby.playerLeave(message.player)

async def run(port, debug=False):
    await app.run_task(port=port, debug=debug)

async def main(queue: asyncio.Queue, port=8080, debug=False):
    await lobby.lobbySetUp()
    await asyncio.gather(
        run(port, debug=debug),
        read_queue(queue)
    )
