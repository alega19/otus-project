import asyncio
import logging

from vkapi.db import Database
from vkapi.vkapiclient import VKAPIClient
from vkapi.tasks.community import TaskToUpdateCommunities
from vkapi.tasks.audience import TaskToUpdateAudience


class App:

    def start(self):
        loop = asyncio.get_event_loop()
        try:
            client = VKAPIClient(loop, [TaskToUpdateCommunities, TaskToUpdateAudience])
            loop.run_until_complete(client.run())
        finally:
            Database.close()
            loop.close()


def main():
    logging.basicConfig(level=logging.INFO)
    App().start()


if __name__ == '__main__':
    main()
