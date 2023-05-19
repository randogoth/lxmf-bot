from lxmfbot import LXMFBot

bot = LXMFBot("NodeBot")

@bot.received
def echo_msg(msg):
    msg.reply(msg.content)

bot.run()