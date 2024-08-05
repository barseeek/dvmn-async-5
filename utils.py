import asyncio
import logging
import socket
from contextlib import asynccontextmanager
from dataclasses import dataclass

import aiofiles

logger = logging.getLogger(__name__)


class InvalidToken(Exception):
    pass


@dataclass
class Settings:
    host: str
    port: int
    port_write: int
    name: str
    token: str
    logging: bool


@dataclass
class Queues:
    messages_queue: asyncio.Queue
    sending_queue: asyncio.Queue
    status_updates_queue: asyncio.Queue
    save_messages_queue: asyncio.Queue
    watchdog_queue: asyncio.Queue


@asynccontextmanager
async def get_connection(host, port, attempts=3, timeout=5):
    writer = None
    attempts_count = 0
    reader = None
    while not reader:
        try:
            reader, writer = await asyncio.open_connection(
                host, port)
            yield reader, writer
        except (ConnectionError, socket.gaierror):
            if attempts_count < attempts:
                logger.warning('Connection Error, try again')
                attempts_count += 1
                continue
            else:
                logger.warning(f'{attempts} Connection Error in a row, try again in {timeout} secs\n')
                await asyncio.sleep(timeout)
        finally:
            if writer:
                writer.close()
                await writer.wait_closed()


async def read_message(reader):
    message = await reader.readline()
    message = message.decode('utf-8').rstrip()
    logger.debug(f'Received message: {message}')
    return message


async def write_message(writer, message=None):
    if not message:
        message = '\n'
    writer.write(message.encode())
    logger.debug(f'Sent message: {message}')
    await writer.drain()


async def get_token(filepath):
    try:
        async with aiofiles.open(filepath, 'r') as afp:
            token = await afp.read()
            return token
    except FileNotFoundError as err:
        logger.exception(f'{err.strerror}: {err.filename}', exc_info=False)
        raise InvalidToken('Файл не найден', 'Файл с токеном не найден.')
