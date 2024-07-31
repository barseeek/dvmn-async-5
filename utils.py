import asyncio
import logging
from contextlib import asynccontextmanager


logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_connection(host, port, attempts=3, timeout=5):
    writer = None
    attempts_count = 0
    reader = None
    while not reader:
        try:
            reader, writer = await asyncio.open_connection(
                host, port)
            logger.info('Connection established\n')
            yield reader, writer
        except ConnectionError:
            if attempts_count < attempts:
                logger.warning('Connection Error, try again\n')
                attempts_count += 1
                continue
            else:
                logger.warning(f'{attempts} Connection Error in a row, try again in {timeout} secs\n')
                await asyncio.sleep(timeout)
        finally:
            if writer:
                writer.close()
                await writer.wait_closed()


async def read_msg(reader):
    message = await reader.readline()
    message = message.decode('utf-8').rstrip()
    logger.debug(f'Received message: {message}')
    return message


