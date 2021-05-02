import os
import asyncio

import server
import bot


async def main():
    queue = asyncio.Queue()
    port = os.environ.get('SERVER_PORT', 63083)
    if os.environ.get('SERVER_ONLY'):
        await asyncio.gather(
            server.main(queue, port=port)
        )
    else:
        client = bot.MyClient(queue)
        await asyncio.gather(
            server.main(queue, port=port),
            client.start(os.environ['DISCORD_BOT_TOKEN'])
        )

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Received exit, exiting")
