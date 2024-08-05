import argparse
import asyncio
import logging
import socket
import sys
import time
from tkinter import messagebox

import aiofiles
import anyio
import async_timeout
from environs import Env

import gui
from authorization import authorize_user
from utils import get_connection, read_message, write_message, InvalidToken, Settings, Queues, get_token

logger = logging.getLogger('listener')
watchdog_logger = logging.getLogger('watchdog')

TIMEOUT_SECONDS = 5


def reconnect(async_function):
    async def wrapper(settings, queues):
        while True:
            try:
                await async_function(settings, queues)
            except (ConnectionError, socket.gaierror):
                continue
            except InvalidToken:
                sys.stderr.write('Connection with wrong token.\n')
                messagebox.showinfo('Wrong token', 'Connection with wrong token.\n')
                break

    return wrapper


@reconnect
async def read_msgs(settings: Settings, queues: Queues):
    try:
        queues.status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
        async with get_connection(settings.host, settings.port) as (reader, writer):
            queues.status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            while True:
                message = await read_message(reader)
                queues.messages_queue.put_nowait(message)
                queues.save_messages_queue.put_nowait(message)
                queues.watchdog_queue.put_nowait('New message in chat')
    except ConnectionError:
        queues.status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)


@reconnect
async def send_msgs(settings: Settings, queues: Queues):
    try:
        queues.status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
        async with get_connection(settings.host, settings.port_write) as (reader, writer):
            account = await authorize_user(reader, writer, settings.token, settings.name)
            if not account:
                queues.status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
                queues.watchdog_queue.put_nowait('Auth failed')
                raise InvalidToken('Wrong token')
            else:
                nickname = account.get('nickname')
                logger.info(f'User {nickname} successfully authenticated')
                queues.watchdog_queue.put_nowait('Auth success')
                queues.status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
                queues.status_updates_queue.put_nowait(gui.NicknameReceived(nickname))

            while True:
                message = await queues.sending_queue.get()
                await write_message(writer, f'{message}\n\n')
                queues.watchdog_queue.put_nowait('Sent message')
    except ConnectionError:
        queues.status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)


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
    parser.add_argument("-n", "--name", type=str,
                        default=env.str('NAME', 'Anonymous'),
                        help="Set your nickname")
    parser.add_argument("-t", "--token", type=str,
                        default=env.str('CHAT_TOKEN', ''),
                        help="Set your token")
    parser.add_argument("-tf", "--token_file", type=str,
                        default=env.str('CHAT_TOKEN_FILE', 'access_token.txt'),
                        help="Set your token file path")
    parser.add_argument("-l", "--logging", action='store_false')

    return parser.parse_args()


async def save_messages(save_messages_queue, filename):
    async with aiofiles.open(filename, 'a') as file:
        while True:
            message = await save_messages_queue.get()
            if message is None:
                break
            await file.write(message + '\n')
        save_messages_queue.task_done()


async def handle_connection(settings: Settings, queues: Queues):
    async with anyio.create_task_group() as tg:
        tg.start_soon(send_msgs, settings, queues)
        tg.start_soon(watch_for_connection, settings, queues)
        tg.start_soon(read_msgs, settings, queues)
        tg.start_soon(ping_server, settings, queues)


@reconnect
async def ping_server(settings: Settings, queues: Queues):
    async with get_connection(settings.host, settings.port) as (reader, writer):
        try:
            async with async_timeout.timeout(TIMEOUT_SECONDS) as tm:
                await write_message(writer, '')
                await read_message(reader)
                queues.watchdog_queue.put_nowait('Pinged server')
            await asyncio.sleep(TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            pass


@reconnect
async def watch_for_connection(settings: Settings, queues: Queues):
    while True:
        try:
            async with async_timeout.timeout(TIMEOUT_SECONDS):
                message = await queues.watchdog_queue.get()
                watchdog_logger.debug(f'[{int(time.time())}] Connection is alive. {message}')
        except asyncio.TimeoutError:
            watchdog_logger.debug(f'[{int(time.time())}] {TIMEOUT_SECONDS}s timeout is elapsed')
            raise ConnectionError


async def main():
    args = parse_args()
    token = args.token
    if token == '':
        token = await get_token(args.token_file)
    settings = Settings(
        host=args.host,
        port=args.port,
        port_write=args.port_write,
        name=args.name,
        token=token,
        logging=args.logging
    )
    queues = Queues(
        messages_queue=asyncio.Queue(),
        sending_queue=asyncio.Queue(),
        status_updates_queue=asyncio.Queue(),
        save_messages_queue=asyncio.Queue(),
        watchdog_queue=asyncio.Queue(),
    )
    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(gui.draw, queues)
            tg.start_soon(handle_connection, settings, queues)
    except ExceptionGroup as exception_group:
        for exception in exception_group.exceptions:
            if isinstance(exception, gui.TkAppClosed):
                sys.stderr.write('Application is closed.\n')
    finally:
        queues.status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
        queues.status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)


if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)
    watchdog_logger.setLevel(logging.DEBUG)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Keyboard Interrupt')
    except InvalidToken:
        sys.stderr.write('Connection with wrong token.\n')
        messagebox.showinfo('Wrong token', 'Connection with wrong token.\n')
    finally:
        sys.exit(0)
