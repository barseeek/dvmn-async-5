import json
from json import JSONDecodeError

from utils import read_message, write_message


async def authorize_user(reader, writer, token, username):
    await read_message(reader)
    await write_message(writer, f'{token}\n')
    account_payload = await read_message(reader)
    try:
        account = json.loads(account_payload)
        return account
    except JSONDecodeError:
        return None
