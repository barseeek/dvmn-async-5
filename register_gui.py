import argparse
import asyncio
import json
import sys
import tkinter as tk
from json import JSONDecodeError
from tkinter import messagebox

import aiofiles
from anyio import create_task_group
from environs import Env

from gui import update_tk, TkAppClosed, process_new_message
from utils import get_connection, read_message, write_message


async def draw(queue):
    root = tk.Tk()

    root.title('Регистрация Майнкрафтера')

    root_frame = tk.Frame(root)
    root_frame.pack(fill="both", expand=True)
    label_username = tk.Label(height=1, text="Введите имя пользователя")
    label_username.pack()

    input_username = tk.Entry(width=50)
    input_username.bind("<Return>", lambda event: process_new_message(input_username, queue))
    input_username.pack()

    submit_button = tk.Button(text="Зарегистрироваться")
    submit_button.bind("<Button-1>", lambda event: process_new_message(input_username, queue))
    submit_button.pack()

    await update_tk(root_frame)


async def save_account(account_payload, filepath):
    async with aiofiles.open(filepath, 'w') as file:
        await file.write(str(account_payload.get('account_hash')))


async def register_user(host, port, queue, filepath):
    username = await queue.get()
    async with get_connection(host, port) as (reader, writer):
        if not username:
            messagebox.showinfo('Error', 'Введите имя')
            raise TkAppClosed()
        await read_message(reader)
        await write_message(writer)
        await read_message(reader)
        await write_message(writer, f'{username}\n')
        account_payload = await read_message(reader)
        try:
            account_data = json.loads(account_payload)
            await save_account(account_data, filepath)
            messagebox.showinfo('Success', 'Registration successful, {}!'.format(account_data.get('nickname')))
        except JSONDecodeError:
            messagebox.showinfo('Error', 'Registration failed')
        finally:
            raise TkAppClosed()


def parse_args():
    env = Env()
    env.read_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("-ho", "--host", type=str,
                        default=env.str('HOST', 'minechat.dvmn.org'),
                        help="Set the host address")
    parser.add_argument("-pw", "--port_write", type=int,
                        default=env.int('PORT_WRITER', 5050),
                        help="Set the port number on which you want to write messages")
    parser.add_argument("-tf", "--token_file", type=str,
                        default=env.str('CHAT_TOKEN_FILE', 'access_token.txt'),
                        help="Set path to the file where the account data will be written to")
    return parser.parse_args()


async def main():
    args = parse_args()
    queue = asyncio.Queue()
    try:
        async with create_task_group() as tg:
            tg.start_soon(draw, queue)
            tg.start_soon(register_user, args.host, args.port_write, queue, args.token_file)
    except ExceptionGroup as exception_group:
        for exception in exception_group.exceptions:
            if isinstance(exception, TkAppClosed):
                sys.stderr.write('Registration is closed.\n')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.stderr.write('Keyboard interrupt.\n')
