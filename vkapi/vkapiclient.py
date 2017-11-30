import asyncio
import logging
from queue import deque

import aiohttp

from vkapi import errors
from vkapi.tokenpool import TokenPool
from vkapi.config import REQUEST_TIMEOUT
from vkapi.config import WORKERS_PER_TOKEN
from vkapi.config import TRIES_PER_TASK


class VKAPIClient:

    def __init__(self, loop, task_classes):
        self.loop = loop
        self.task_classes = task_classes
        self.token_pool = TokenPool(loop)
        self.buffer = deque()

    async def run(self):
        async with aiohttp.ClientSession(read_timeout=REQUEST_TIMEOUT, loop=self.loop) as session:
            num = WORKERS_PER_TOKEN * len(self.token_pool)
            workers = [self._worker(session) for _ in range(num)]
            await asyncio.wait(workers, loop=self.loop)

    async def _worker(self, session):
        while True:
            if self.buffer:
                task = self.buffer.popleft()
            else:
                task = self._get_highest_priority_task()
            token = await self.token_pool.get()
            try:
                await task.handle(session, token)
            except (aiohttp.ClientError, errors.Error, asyncio.TimeoutError) as err:
                logging.warning(repr(err))
                self._handle_failed_task(task)
            except Exception as err:
                logging.exception(err)
                self._handle_failed_task(task)

    def _get_highest_priority_task(self):
        taskcls = min(self.task_classes, key=lambda cls: cls.deadline())
        return taskcls()

    def _handle_failed_task(self, task):
        task.tries += 1
        if task.tries < TRIES_PER_TASK:
            self.buffer.append(task)
        else:
            task.cancel()
