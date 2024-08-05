# dvmn-async-5

Асинхронный чат с графическим интерфейсом.
Для отправки сообщений необходим токен.
Для зарегистрированных пользователей можно добавить токен в переменную окружения `CHAT_TOKEN`.
Для регистрации запустите скрипт `register_gui.py` и введите имя пользователя.

## Как установить
Для работы утилиты нужен Python версии не ниже 3.11.
1. Клонирование репозитория
```bash
git clone https://github.com/barseeek/dvmn-async-5.git
```

#### 2. Установка необходимых библиотек Python
```bash
pip install -r requirements.txt
```

## Аргументы командной строки:

```bash 
usage: main.py [-h] [-ho HOST] [-p PORT] [-pw PORT_WRITE] [-f FILEPATH] [-n NAME] [-t TOKEN] [-tf TOKEN_FILE] [-l]

Async chat listener

options:
  -h, --help            show this help message and exit
  -ho HOST, --host HOST
                        Set the host address
  -p PORT, --port PORT  Set the port number on which you want to listen to messages
  -pw PORT_WRITE, --port_write PORT_WRITE
                        Set the port number on which you want to write messages
  -f FILEPATH, --filepath FILEPATH
                        Set path to the file where the messages will be written to
  -n NAME, --name NAME  Set your nickname
  -t TOKEN, --token TOKEN
                        Set your token
  -tf TOKEN_FILE, --token_file TOKEN_FILE
                        Set your token file path
  -l, --logging


```
```bash
usage: register_gui.py [-h] [-ho HOST] [-pw PORT_WRITE] [-tf TOKEN_FILE]

options:
  -h, --help            show this help message and exit
  -ho HOST, --host HOST
                        Set the host address
  -pw PORT_WRITE, --port_write PORT_WRITE
                        Set the port number on which you want to write messages
  -tf TOKEN_FILE, --token_file TOKEN_FILE
                        Set path to the file where the account data will be written to


```
## Переменные окружения
`HOST` - адрес чата. По умолчанию `minechat.dvmn.org`.

`PORT_LISTENER` - порт для прослушивания сообщений чата. По умолчанию 5000.

`PORT_WRITER` - порт для отправки сообщений в чат. По умолчанию 5050.

`FILE_PATH` - путь до файла, куда записывается история сообщений. По умолчанию `messages.txt`.

`NAME` - имя пользователя, по умолчанию `Anonymous`.

`CHAT_TOKEN` - токен пользователя. Если токена нет, необходимо зарегистрироваться и получить токен.

`CHAT_TOKEN_FILE` - путь до файла, куда записывается токен зарегистрированного пользователя. По умолчанию `access_token.txt`.

## Как запустить

Скрипт прослушивания чата запускают со следующими необязательными параметрами:

`--host`  - адрес чата.

`--port` - порт для прослушивания сообщений чата.

`--filepath` - путь до файла, куда записывается история сообщений. 

### Пример ENV-файла
```env
HOST=minechat.dvmn.org
PORT_LISTENER=5000
PORT_WRITER=5050
FILE_PATH=history.txt
NAME=Nikita
CHAT_TOKEN=
CHAT_TOKEN_FILE=my_token.txt
```

