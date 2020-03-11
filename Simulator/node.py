"""
Node definition
"""

# import random
import collections
# import simpy
from . import telegram as tlgm

Telegram = collections.namedtuple('Telegram', 'received, telegram')
# self.discovery_time = node_config.get("discovery_time", None) or 40
# self.rand_join_time = random.randint(1, node_config.get("random_join_time", None) or 120)
# self.beacon_scan_duration = node_config.get("beacon_scan_duration", None) or 12
# self.max_hop_limit = node_config.get("max_hop_limit", None) or 8
# self.reconnection_timeout = node_config.get("reconnection_timeout", None) or 108000

class Node:
    def __init__(self, env, node_id, phy_neighbors, node_channels, node_config, optimized):
        # phy_neighbors enthält die Nachbar Node-IDs und initital LQIs
        self.env = env
        self.node_id = node_id
        self.phy_neighbors = phy_neighbors
        self.channels = node_channels   # node_id:neighbor_id || neighbor_id:node:id
        self.pan_id = None
        self.pan_quality = 14
        self.pan_start = None
        self.received_pan_suggestions = False
        self.config = node_config
        self.optimized = optimized
        self.csma_waiting_time = 8  # Basis Wartezeit in Millisekunden = 8 Zeiteinheiten in der Simulation
        self.route_request_table = {}
        self.routing_table = {}
        self.sequenz_number = 0
        self.outgoing = None
        self.outgoing_queue = []
        self.default_retry_time = 100
        # 100ms für retry

        if self.node_id == "3":
            self.pan_id = 123


        self.update()

    def update(self):
        if self.pan_id is None and self.pan_start is None or (self.pan_start and self.env.now > self.pan_start + 20 * 1000):
            seq = self.nextSequenzNumber()
            self.pan_start = self.env.now
            yield from self.send(tlgm.BeaconReq(self.node_id, -1, -1, seq, self.create_hash(seq, -1, -1)))

        while True:
            yield self.env.timeout(1)
            for channel in self.channels:
                if len(channel.items) != 0:
                    yield from self.receive(channel)
            if self.outgoing is None and self.outgoing_queue:
                yield from self.send(self.outgoing_queue.pop(0))
            elif self.outgoing and self.env.now >= self.outgoing[2]:
                yield from self.send(self.outgoing[0])

    def csma_check(self):
        for channel in self.channels:
            if len(channel.items) != 0:
                return False
        return True

    def csma_waitingtime_update(self, successfull):
        if successfull:
            self.csma_waiting_time = max(self.csma_waiting_time-64, 8)
        else:
            self.csma_waiting_time = 2 * self.csma_waiting_time

    def send(self, telegram, retry_time=None):
        while(not self.csma_check()):
            print("NODE {} CANNOT SEND - CSMA/CA".format(self.node_id))
            yield self.env.timeout(self.csma_waiting_time)
            self.csma_waitingtime_update(False)
        self.csma_waitingtime_update(True)

        print("{} SEND NODE: {} >>> TEL_TYPE {}, SEQ: {}, CHECKSUM: {} TO NODE {}".format(self.env.now, self.node_id, type(telegram), telegram.sequenz_number, telegram.checksum, telegram.dest))

        confirms = []
        for channel in self.channels:
            confirm = self.env.event()
            confirms.append(confirm)
            msg = Telegram(confirm, telegram)
            yield channel.put(msg)
        yield self.env.all_of(confirms)

        if retry_time is None:
            retry_time = 100 # Standard wartezeit auf antwort 100ms

        if self.outgoing is None and not isinstance(telegram, (tlgm.Ack, tlgm.BeaconReq)):
            self.outgoing = (telegram, 0, self.env.now + retry_time)
        elif self.outgoing and telegram == self.outgoing[0]:
            self.outgoing = (self.outgoing[0], self.outgoing[1] + 1, self.env.now + retry_time)
        else:
            self.outgoing_queue.append(telegram)

    def receive(self, channel):
        msg = yield channel.get()
        yield self.env.timeout(1)
        msg.received.succeed()
        telegram = msg.telegram
        if telegram.dest == self.node_id or telegram.dest == -1:
            print("{} RECV NODE: {} >>> TEL_TYPE: {}, SEQ: {}, CHECKSUM: {} FROM NODE {}".format(self.env.now, self.node_id, type(telegram), telegram.sequenz_number, telegram.checksum, telegram.origin))

            yield from telegram.process(self)

    def update_routing_table(self, route):
        pass

    def update_rreq_table(self, route):
        pass

    def create_hash(self, sequenz_number, dest, final_dest):
        return hash(((self.env.now + sequenz_number) * int(self.node_id)) + int(dest) * int(final_dest))

    def create_telegram(self, tel_type, origin, dest, final_dest, sequenz_number, checksum):
        # Bsp.: tel_type = 'BeaconReq'
        telegram = getattr(tlgm, tel_type)(origin, dest, final_dest, sequenz_number, checksum)
        return telegram

    def nextSequenzNumber(self):
        self.sequenz_number = self.sequenz_number + 1
        return self.sequenz_number

