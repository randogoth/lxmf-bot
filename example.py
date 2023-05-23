from lxmfbot import LXMFBot

bot = LXMFBot("testbot")

@bot.received
def echo_msg(msg):
    msg.reply(msg.content)

bot.run()