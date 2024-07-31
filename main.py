import argparse
import asyncio
import logging

import aiofiles
from environs import Env

import gui
from utils import get_connection

logger = logging.getLogger('listener')


async def read_msgs(host, port, message_queue, save_messages_queue):
    async with get_connection(host, port) as (reader, writer):
        try:
            while True:
                message = await reader.readline()
                message_queue.put_nowait(message.decode())
                if not message:
                    continue
                else:
                    save_messages_queue.put_nowait(message.decode())
        except ConnectionError:
            logger.error('Connection Error')


def parse_args():
    env = Env()
    env.read_env()
    parser = argparse.ArgumentParser(description="Async chat listener")
    parser.add_argument("-ho", "--host", type=str,
                        default=env.str('HOST', 'minechat.dvmn.org'),
                        help="Set the host address")
    parser.add_argument("-p", "--port", type=int,
                        default=env.int('PORT_LISTENER', 5000),
                        help="Set the port number on which you want to listen to messages")
    parser.add_argument("-pw", "--port_write", type=int,
                        default=env.int('PORT_WRITER', 5050),
                        help="Set the port number on which you want to write messages")
    parser.add_argument("-f", "--filepath", type=str,
                        default=env.str('FILE_PATH', 'messages.txt'),
                        help="Set path to the file where the messages will be written to")
    return parser.parse_args()


async def save_messages(save_messages_queue, filename):
    async with aiofiles.open(filename, 'a') as file:
        while True:
            message = await save_messages_queue.get()
            if message is None:
                break
            await file.write(message + '\n')
        save_messages_queue.task_done()


async def main():
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    save_messages_queue = asyncio.Queue()
    args = parse_args()
    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        read_msgs(args.host, args.port, messages_queue, save_messages_queue),
        save_messages(save_messages_queue, args.filepath),
    )


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Keyboard Interrupt')
    except Exception:
        logger.exception('Unhandled exception')
