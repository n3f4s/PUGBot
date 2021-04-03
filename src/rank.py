"""
Define helper class around SR
"""

from abc import ABC, abstractmethod

class Rank(ABC):
    @abstractmethod
    def icon_url():
        pass
    @abstractmethod
    def to_string():
        pass
    @abstractmethod
    def min_sr():
        pass
    @abstractmethod
    def max_sr():
        pass
