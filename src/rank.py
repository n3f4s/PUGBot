"""
Define helper class around SR
"""

from abc import ABC, abstractmethod

class Rank(ABC):
    @abstractmethod
    def icon_url(self):
        pass
    @abstractmethod
    def to_string(self):
        pass
    @abstractmethod
    def min_sr(self):
        pass
    @abstractmethod
    def max_sr(self):
        pass
