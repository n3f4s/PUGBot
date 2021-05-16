
import sys
import logging
import os
import json
from guildconf import GuildConfig, LobbyVC

def default_logger(name, level):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

class MyEncoder(json.JSONEncoder):
        def default(self, o):
            return o.__dict__

def save_config(config):
    root = os.environ.get('DATABASE_ROOT', ".")
    filename = os.path.join(root, "config.json")
    with open(filename, "w") as cfgfile:
        cfgfile.write(MyEncoder().encode(config))
def load_config():
    root = os.environ.get('DATABASE_ROOT', ".")
    filename = os.path.join(root, "config.json")
    if not os.path.exists(filename):
        return {}
    with open(filename) as cfgfile:
        json_v = json.loads(cfgfile.read())
        config = {}
        for k, v in json_v.items():
            lobbies = [LobbyVC(l['name'], l['lobby'], l['team1'], l['team2'])
                       for l in v['lobbies']]
            prefix = v['prefix']
            id_ = v['guild_id']
            config[int(k)] = GuildConfig(id_, lobbies, prefix)
        return config
