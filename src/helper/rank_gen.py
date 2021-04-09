"""
Tool generating ranks classes from JSON file
"""

import json
import sys

filename = sys.argv[1]
dir = sys.argv[2]

with open(filename) as json_file:
    data = json.load(json_file)
    for entry in data:
        name = entry["name"]
        with open("{}/{}.py".format(dir, name.lower()), "w") as target:
            target.write("""# Auto Generated file
class {}:
    def icon_url(self):
        return "{}"
    def name(self):
        return "{}"
    def min_sr(self):
        return {}
    def max_sr(self):
        return {}""".format(name, entry["icon"], name, entry["min"], entry["max"], ))
