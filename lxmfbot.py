import os, time
import RNS
from   LXMF    import LXMRouter, LXMessage
from   appdirs import AppDirs
from   queue   import Queue
from   types   import SimpleNamespace

# Core class influenced by https://github.com/chengtripp/lxmf_messageboard
# Bot syntax inspired by Discord.py and Telethon

class LXMFBot:

    delivery_callbacks = []
    queue = Queue(maxsize = 5)

    def __init__(self, name='LXMFBot'):

        # initialize identiy
        self.name = name
        dirs = AppDirs("LXMFBot", "randogoth")
        idpath = os.path.join(dirs.user_data_dir, "identity")
        self.announce_path = os.path.join(dirs.user_data_dir, "announce")
        if not os.path.isfile(idpath):
            RNS.log('No Primary Identity file found, creating new...', RNS.LOG_INFO)
            id = RNS.Identity()
            id.to_file(idpath)
        self.id = RNS.Identity.from_file(idpath)
        RNS.log('Loaded identity from file', RNS.LOG_INFO)

        # start RNS and LXMFRouter
        RNS.Reticulum(loglevel=RNS.LOG_VERBOSE)
        self.router = LXMRouter(identity = self.id, storagepath = dirs.user_data_dir)
        self.local = self.router.register_delivery_identity(self.id, display_name=name)
        self.router.register_delivery_callback(self._message_received)
        RNS.log('LXMF Router ready to receive on: {}'.format(RNS.prettyhexrep(self.local.hash)), RNS.LOG_INFO)
        self._announce()

    def _announce(self):
        if os.path.isfile(self.announce_path):
            with open(self.announce_path, "r") as f:
                announce = int(f.readline())
        else:
            RNS.log('failed to open announcepath', RNS.LOG_DEBUG)
            announce = 1
        if announce > int(time.time()):
            RNS.log('Recent announcement', RNS.LOG_DEBUG)
        else:
            with open(self.announce_path, "w") as af:
                next_announce = int(time.time()) + 1800
                af.write(str(next_announce))
            self.local.announce()
            RNS.log('Announcement sent, expr set 1800 seconds', RNS.LOG_INFO)
    
    def received(self, function):
        self.delivery_callbacks.append(function)
        return function
    
    def _message_received(self, message):
        sender = RNS.hexrep(message.source_hash, delimit=False)
        def reply(msg):
            self.send(sender, msg)
        for callback in self.delivery_callbacks:
            obj = {
                'lxmf' : message,
                'reply' : reply,
                'sender' : sender,
                'content' : message.content.decode('utf-8')
            }
            msg = SimpleNamespace(**obj)
            callback(msg)

    def send(self, destination, message, title='Reply'):
        try:
            hash = bytes.fromhex(destination)
        except Exception as e:
            RNS.log("Invalid destination hash", RNS.LOG_ERROR)
            return

        if not len(hash) == RNS.Reticulum.TRUNCATED_HASHLENGTH//8:
            RNS.log("Invalid destination hash length", RNS.LOG_ERROR)
        else:
            id = RNS.Identity.recall(hash)

        if id == None:
            RNS.log("Could not recall an Identity for the requested address. You have probably never received an announce from it. Try requesting a path from the network first. In fact, let's do this now :)", RNS.LOG_ERROR)
            RNS.Transport.request_path(hash)
            RNS.log("OK, a path was requested. If the network knows a path, you will receive an announce with the Identity data shortly.", RNS.LOG_INFO)
        else:
            lxmf_destination = RNS.Destination(id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")
            lxm = LXMessage(lxmf_destination, self.local, message, title=title, desired_method=LXMessage.DIRECT)
            lxm.try_propagation_on_fail = True
            self.queue.put(lxm)
    
    def run(self, delay=10):
        RNS.log(f'LXMF Bot `{self.name}` reporting for duty and awaiting messages...', RNS.LOG_INFO)
        while True:
            for i in list(self.queue.queue):
                lxm = self.queue.get()
                self.router.handle_outbound(lxm)
            self._announce
            time.sleep(delay)