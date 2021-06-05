from btag import Btag
from datetime import datetime
import json
import os
import os.path
import urllib.request
import zipfile


"""
Wrapper for stats to enable easy formatting
"""

class CareerProfile:
    _heroes = {
        "tank": ["dva", "orisa", "reinhardt", "roadhog", "sigma", "winston", "wreckingball", "zarya"  ],
        "damage": ["ashe", "doomfist", "echo", "genji", "hanzo", "junkrat", "mcree", "mei", "pharah", "reaper",
                   "soldier76", "sombra", "symmetra", "tracer", "widowmaker" ],
        "support": ["ana", "baptiste", "brigitte", "lucio", "moira", "mercy", "zenyatta" ]
    }
    def __init__(self, tag, data):
        self._tag = tag
        self._data = data

    def __getFormattedHack__(self):
        d = self._data
        profile = {
            "tag": self._tag.to_string(),
            "overview": { }
        }
        
        if not d:
            d = {}
        
        mostPlayed = { "tank": [], "damage": [], "support": [] }
        stats = d.get("competitiveStats", {}).get("topHeroes", {})
        if stats:
            for hero, hdata in stats.items():
                h = { "hero": hero, "timePlayed": hdata["timePlayed"]}
                for r in self._heroes.keys():
                    if hero in self._heroes[r]: mostPlayed[r].append(h)
        
        for r in self._heroes.keys():
            profile["overview"][r] = {
                "sr": None, 
                "peakSr": None,
                "mostPlayed": sorted(mostPlayed.get(r,[]), key=lambda x: x["timePlayed"])
            }
            
        ratings = d.get('ratings')
        if ratings:
            for rating in ratings:
                r = rating["role"]
                profile["overview"][r]["sr"] = rating["level"]
                profile["overview"][r]["peakSr"] = rating["level"]
            
        return profile
        
"""
Class for managing player database
"""

class CareerDatabase:

    _apiquery = "https://ow-api.com/v1/stats/pc/EU/{}/complete"
    #_apiquery = "https://ow-api.com/v1/stats/pc/EU/{}/profile"
    _databaseroot = "players"
    _dummyquery = False
    
    #TODO: Proper header
    _hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive' }
    
    def __init__(self):
        self._databaseroot = os.environ.get('DATABASE_ROOT', self._databaseroot)
        
    async def getStats(self, btag, force_update=False):
        if self._tagInDatabase(btag) and not force_update:
            stats = await self._getFromDataBase(btag)
        else:
            stats = await self._queryApi(btag)
            await self._saveToDataBase(btag, stats)
            
        stats = CareerProfile(btag, stats)
        return stats
        
    async def _queryApi(self, btag):
        if self._dummyquery:
            return { "dummyquery": "dummyval3"}
        else:
            try:
                query = self._apiquery.format(btag.for_api())
                request = urllib.request.Request(query, None, self._hdr)
                response = urllib.request.urlopen(request).read()
            except urllib.error.HTTPError:
                return None
            data = json.loads(response.decode('utf-8'))
            return data
        
    def _update(self, btag):
        " Query api-server for updated stats "
        pass
        
    def _tagInDatabase(self, btag):
        return os.path.exists(os.path.join(self._databaseroot, btag.to_string()))
        
    async def _getFromDataBase(self, btag):
        playerdir = os.path.join(self._databaseroot, btag.to_string())
        files = sorted(os.listdir(playerdir))
        with open(os.path.join(playerdir, files[-1]), 'r') as file:
            data = json.load(file)
        return data
        
    async def _saveToDataBase(self, btag, data):
        playerdir = os.path.join(self._databaseroot, btag.to_string())
        full_path = os.path.abspath(playerdir)
        if not os.path.exists(playerdir):
            os.makedirs(playerdir)
            
        fname = datetime.now().strftime("%d-%m-%Y_%H%M%S") + ".json"
        with open(os.path.join(playerdir, fname), 'x') as file:
            file.write(json.dumps(data))
        return True
        
if __name__ == "__main__":
    db = CareerDatabase()
    print(db.getStats(Btag("flasheart#21119")))
