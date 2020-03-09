"""
Node definition
"""

import random
import collections
import simpy
from . import telegram as tlgm

Telegram = collections.namedtuple('Telegram', 'received, telegram')

class Node:
    def __init__(self, env, node_id, phy_neighbors, node_channels, node_config, optimized):
        self.env = env
        self.node_id = node_id
        # phy_neighbors enthält die Nachbar Node-IDs und "Leitungen" als shared Resourced dorthin
        self.phy_neighbors = phy_neighbors
        self.channels = node_channels
        self.pan_id = None
        self.pan_fixed = False
        self.link_quality = 100
        self.config = node_config
        # self.discovery_time = node_config.get("discovery_time", None) or 40
        # self.rand_join_time = random.randint(1, node_config.get("random_join_time", None) or 120)
        # self.beacon_scan_duration = node_config.get("beacon_scan_duration", None) or 12
        # self.max_hop_limit = node_config.get("max_hop_limit", None) or 8
        # self.reconnection_timeout = node_config.get("reconnection_timeout", None) or 108000
        self.route_request_table = {}
        self.routing_table = {}
        self.optimized = optimized
        self.csma_waiting_time = 8  # Basis Wartezeit in Millisekunden = 8 Zeiteinheiten in der Simulation

        # self.env.timeout(self.rand_join_time)
        self.update()


    def update(self):
        yield from self.start_join()
        while True:
            yield self.env.timeout(1)
            for channel in self.channels:
                if len(channel.items) != 0:
                    yield from self.receive(channel)

    def start_join(self):
        # Random Join timeout, default random 120 seconds
        yield self.env.timeout(random.randint(1, self.config.get("random_join_time", None) or 120)*1000)
        beacon_scan_modifier = 0
        while self.pan_id is None:
            yield self.env.timeout(beacon_scan_modifier * 1000)
            telegram = tlgm.BeaconReq(self.node_id, -1, -1)
            self.send(telegram)
            for _ in range(self.config.get("discovery_time", None) or 40):
                yield self.env.timeout(1)
                for channel in self.channels:
                    if len(channel.items) != 0:
                        yield from self.receive(channel)
            if beacon_scan_modifier == 0:
                beacon_scan_modifier = 12
            else:
                beacon_scan_modifier = max(beacon_scan_modifier * 3, 30 * 60)

    # Für Retries dann was überlegen
    def observe_telegram(self):
        pass

    def update_pan(self, link_quality, pan_id):
        if not self.pan_fixed and link_quality < self.link_quality:
            self.pan_id = pan_id

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

    def send(self, telegram):
        while(not self.csma_check()):
            yield self.env.timeout(self.csma_waiting_time)
            self.csma_waitingtime_update(False)
        self.csma_waitingtime_update(True)
        confirms = []
        for channel in self.channels:
            confirm = self.env.event()
            confirms.append(confirm)
            msg = Telegram(confirm, telegram)
            yield channel.put(msg)
        yield self.env.all_of(confirms)

    def receive(self, channel):
        msg = yield channel.get()
        yield self.env.timeout(1)
        msg.received.succeed()
        telegram = msg.telegram
        # yield from telegram.process(self)
        self.env.process(telegram.process(self))

    def update_routing_table(self, route):
        pass

    def update_rreq_table(self, route):
        pass

