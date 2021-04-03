import os
import asyncio

import server
import bot


async def main():
    queue = asyncio.Queue()
    client = bot.MyClient(queue)
    await asyncio.gather(
        server.main(queue),
        client.start(os.environ['DISCORD_BOT_TOKEN'])
    )

asyncio.run(main())
