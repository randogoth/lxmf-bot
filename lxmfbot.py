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
    receipts = []
    queue = Queue(maxsize = 5)
    announce_time = 360

    def __init__(self, name='LXMFBot', announce=360, announce_immediately=False):

        # initialize identiy
        self.name = name
        self.announce_time = announce
        dirs = AppDirs("LXMFBot", "randogoth")
        self.config_path = os.path.join(dirs.user_data_dir, name)
        idfile = os.path.join(self.config_path, "identity")
        if not os.path.isdir(dirs.user_data_dir):
                os.mkdir(dirs.user_data_dir)
        if not os.path.isdir(self.config_path):
                os.mkdir(self.config_path)
        if not os.path.isfile(idfile):
            RNS.log('No Primary Identity file found, creating new...', RNS.LOG_INFO)
            id = RNS.Identity(True)
            id.to_file(idfile)
        self.id = RNS.Identity.from_file(idfile)
        RNS.log('Loaded identity from file', RNS.LOG_INFO)
        if announce_immediately:
            af = os.path.join(self.config_path, "announce")
            if os.path.isfile(af):
                os.remove(af)
                RNS.log('Announcing now. Timer reset.', RNS.LOG_INFO)

        # start RNS and LXMFRouter
        RNS.Reticulum(loglevel=RNS.LOG_VERBOSE)
        self.router = LXMRouter(identity = self.id, storagepath = dirs.user_data_dir)
        self.local = self.router.register_delivery_identity(self.id, display_name=name)
        self.router.register_delivery_callback(self._message_received)
        RNS.log('LXMF Router ready to receive on: {}'.format(RNS.prettyhexrep(self.local.hash)), RNS.LOG_INFO)
        self._announce()

    def _announce(self):
        announce_path = os.path.join(self.config_path, "announce")
        if os.path.isfile(announce_path):
            with open(announce_path, "r") as f:
                announce = int(f.readline())
        else:
            RNS.log('failed to open announcepath', RNS.LOG_DEBUG)
            announce = 1
        if announce > int(time.time()):
            RNS.log('Recent announcement', RNS.LOG_DEBUG)
        else:
            with open(announce_path, "w+") as af:
                next_announce = int(time.time()) + self.announce_time
                af.write(str(next_announce))
            self.local.announce()
            RNS.log('Announcement sent, expr set 1800 seconds', RNS.LOG_INFO)
    
    def received(self, function):
        self.delivery_callbacks.append(function)
        return function
    
    def _message_received(self, message):
        sender = RNS.hexrep(message.source_hash, delimit=False)
        receipt = RNS.hexrep(message.hash, delimit=False)
        RNS.log(f'Message receipt <{receipt}>', RNS.LOG_INFO)
        def reply(msg):
            self.send(sender, msg)
        if receipt not in self.receipts:
            self.receipts.append(receipt)
            if len(self.receipts) > 100:
                self.receipts.pop(0)
            for callback in self.delivery_callbacks:
                obj = {
                    'lxmf' : message,
                    'reply' : reply,
                    'sender' : sender,
                    'content' : message.content.decode('utf-8'),
                    'hash' : receipt
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