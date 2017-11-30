import asyncio
from datetime import datetime as DateTime
from queue import deque

from vkapi.db import Database
from vkapi.config import REQUEST_DELAY_PER_TOKEN


class TokenPool:

    def __init__(self, loop):
        self.loop = loop
        self.tokens = None
        self.sem = None
        self._load()

    def _load(self):
        sql = ('SELECT "token" '
               'FROM "account" '
               'WHERE "active" = TRUE')
        tokens = Database().execute(sql, handler=lambda t: t[0])
        self.tokens = deque((t, DateTime(1970, 1, 1)) for t in tokens)
        self.sem = asyncio.BoundedSemaphore(len(tokens), loop=self.loop)

    def __len__(self):
        return len(self.tokens)

    async def get(self):
        async with self.sem:
            tk, dt = self.tokens.popleft()
            delta = (DateTime.utcnow() - dt).total_seconds()
            delay = REQUEST_DELAY_PER_TOKEN - delta
            if delay > 0:
                await asyncio.sleep(delay, loop=self.loop)
            self.tokens.append((tk, DateTime.utcnow()))
            return tk
