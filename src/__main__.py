import server
import bot
import os

import pykka


class BackendActor(pykka.ThreadingActor):
    def __init__(self):
        print("Starting backend actor")
        super().__init__()

    def on_start(self):
        self.lobby = server.lobby
        server.main()

    def on_receive(self, message):
        if isinstance(message, bot.PlayerJoined):
            self.lobby.playerJoin(message.player, message.btags[0].to_string())
        if isinstance(message, str):
            print(message)

backend = BackendActor.start()
client = bot.MyClient(backend)
client.run(os.environ['DISCORD_BOT_TOKEN'])
# bot = BotActor.start(backend)
# backend.tell("Youpi")
# bot.tell("Youpi")
