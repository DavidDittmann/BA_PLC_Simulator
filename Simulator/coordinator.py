import collections
from . import node
from . import telegram as tlgm
from Log import log

logger = log.Logger().get_logger()

Telegram = collections.namedtuple('Telegram', 'received, telegram')

class Coordinator(node.Node):
    def __init__(self, env, node_id, config, optimized=False):
        super().__init__(env, node_id, config, optimized)
        self.pan_id = 1234

    # def update(self):
        # for i in range(10):
        #     yield self.env.timeout(10)
        #     telegram = tlgm.BeaconReq(originator=0, destination=i, final_destination=i)
        #     yield from self.send(telegram)

    # def send(self, telegram):
    #     while not self.csma_check():
    #         yield self.env.timeout(self.csma_waiting_time)
    #         self.csma_waitingtime_update(False)
    #     self.csma_waitingtime_update(True)
    #     confirms = []
    #     for channel in self.channels:
    #         print("Sending =: Node: {}, MsgType: {}, Time: {}".format(self.node_id, type(telegram), self.env.now))
    #         confirm = self.env.event()
    #         confirms.append(confirm)
    #         msg = Telegram(confirm, telegram)
    #         yield channel.put(msg)
    #     yield self.env.all_of(confirms)
