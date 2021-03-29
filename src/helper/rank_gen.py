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
    def icon_url:
        return "{}"
    def name:
        return "{}"
    def min_sr:
        return {}
    def max_sr:
        return {}""".format(name, entry["icon"], name, entry["min"], entry["max"], ))
