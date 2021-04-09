import os
import asyncio

import server
import bot


async def main():
    queue = asyncio.Queue()
    client = bot.MyClient(queue)
    port = os.environ.get('SERVER_PORT', 63083)
    await asyncio.gather(
        server.main(queue, port=port),
        client.start(os.environ['DISCORD_BOT_TOKEN'])
    )

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Received exit, exiting")
