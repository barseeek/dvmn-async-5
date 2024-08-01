import argparse
import asyncio
import logging
import sys
import time
from tkinter import messagebox

import aiofiles
import async_timeout
from environs import Env

import gui
from authorization import authorize_user
from utils import get_connection, read_message, write_message

logger = logging.getLogger('listener')
watchdog_logger = logging.getLogger('watchdog')


TIMEOUT_SECONDS = 2

async def read_msgs(host, port, message_queue, save_messages_queue, status_updates_queue, watchdog_queue):
    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    async with get_connection(host, port) as (reader, writer):
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
        try:
            while True:
                message = await read_message(reader)
                message_queue.put_nowait(message)
                save_messages_queue.put_nowait(message)
                watchdog_queue.put_nowait('New message in chat')
        except ConnectionError:
            logger.error('Connection Error')
            status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
        finally:
            status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)


class InvalidToken(Exception):
    pass


async def send_msgs(host, port, sending_queue, status_updates_queue, watchdog_queue, token, username):
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    watchdog_queue.put_nowait('Prompt before auth')
    async with get_connection(host, port) as (reader, writer):
        account = await authorize_user(reader, writer, token, username)
        if not account:
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
            watchdog_queue.put_nowait('Auth failed')
            raise InvalidToken('Неверный токен')
        else:
            nickname = account.get('nickname')
            logger.info(f'Пользователь {nickname} успешно авторизован')
            watchdog_queue.put_nowait('Auth success')
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
            status_updates_queue.put_nowait(gui.NicknameReceived(nickname))

        while True:
            message = await sending_queue.get()
            await write_message(writer, f'{message}\n\n')
            watchdog_queue.put_nowait('Sent message')


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
    parser.add_argument("-m", "--message", type=str,
                        help="Set your message")
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


async def watch_for_connection(watchdog_queue):
    while True:
        try:
            async with async_timeout.timeout(TIMEOUT_SECONDS):
                message = await watchdog_queue.get()
                watchdog_logger.debug(f'[{int(time.time())}] Connection is alive. {message}')
        except asyncio.TimeoutError:
            watchdog_logger.debug(f'[{int(time.time())}] {TIMEOUT_SECONDS}s timeout is elapsed')


async def main():
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    save_messages_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()
    args = parse_args()

    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        read_msgs(args.host, args.port, messages_queue, save_messages_queue, status_updates_queue, watchdog_queue),
        save_messages(save_messages_queue, args.filepath),
        send_msgs(args.host, args.port_write, sending_queue, status_updates_queue, watchdog_queue,args.token, args.name),
        watch_for_connection(watchdog_queue)
    )


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    watchdog_logger.setLevel(logging.DEBUG)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Keyboard Interrupt')
    except InvalidToken:
        messagebox.showinfo("Error", "Неверный токен!")
        logger.exception('Неверный токен, зарегистрируйтесь заново')
    except (Exception):
        logger.exception('Unhandled exception')
    finally:
        sys.exit(0)
