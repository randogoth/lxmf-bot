from bot import LXMFBot
from pprint import pprint

bot = LXMFBot("Randobot")

@bot.received
def echo_msg(msg):
    msg.reply(msg.content)

bot.run()