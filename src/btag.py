"""
Define a wrapper class around btag to make
it's manipulation easier
"""

class Btag:
    """Class representing a battle tag"""
    def __init__(self, string):
        split = string.split('#')
        self.name = split[0]
        self.discriminator = split[1]

    def to_string(self):
        """Full btag formatted"""
        return "{}#{}".format(self.name, self.discriminator)

    def for_api(self):
        """Return the btag formatted for the API"""
        return "{}-{}".format(self.name, self.discriminator)

    def __str__(self):
        return self.to_string()
        
    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if isinstance(other, Btag):
            return self.to_string() == other.to_string()
        else:
            return self.to_string() == other
