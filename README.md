# LXMFBot

Python class to easily develop a simple Telethon style chatbot for the LXMF protocol.

## Installation

```
$ pip install -r requirements.txt
```

## Usage

- Instantiate the class with a name for the bot as parameter
- Use the `received` decorator to define functions for parsing received messages
- Use the `send(recipient_hash, message)` or `reply(message)` methods to send messages
- Launch the bot using the `run` method

Example of a bot that echos a message back to the sender:

```Python
from bot import LXMFBot

bot = LXMFBot("NodeBot")

@bot.received
def echo_msg(msg):
    msg.reply(msg.content)

bot.run()
```