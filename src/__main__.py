import server
import bot
import os

client = bot.MyClient(server.lobby)
server.main()
client.run(os.environ['DISCORD_BOT_TOKEN'])
