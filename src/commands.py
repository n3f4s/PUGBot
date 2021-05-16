from abc import ABC, abstractmethod
from typing import List

from bot import MyClient

import discord


class Command(ABC):
    def __init__(self, client: MyClient):
        self._client = client
    def client(self) -> MyClient:
        return self._client
    @abstractmethod
    async def execute(self, message: discord.Message, args: List[str]):
        pass
