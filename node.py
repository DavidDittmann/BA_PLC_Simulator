"""
Node definition
"""

import json
import simpy
import random

class NODE:
    def __init__(self, env, node_id, phy_neighbors, node_config):
        self.env = env
        self.node_id = node_id
        # phy_neighbors enthält die Nachbar Node-IDs und "Leitungen" als shared Resourced dorthin
        self.phy_neighbors = phy_neighbors
        self.pan_id = None
        self.discovery_time = node_config.get("discovery_time", None) or 40
        self.rand_join_time = random.randint(1, node_config.get("random_join_time", None) or 120)
        self.beacon_scan_duration = node_config.get("beacon_scan_duration", None) or 12
        self.max_hop_limit = node_config.get("max_hop_limit", None) or 8
        self.reconnection_timeout = node_config.get("reconnection_timeout", None) or 108000
        self.route_request_table = {}
        self.routing_table = {}

        self.env.timeout(self.rand_join_time)
        self.update()

    def beacon_request(self):
        pass

    def beacon_response(self):
        pass

    def send_join_msg(self):
        pass

    def send_route_request(self):
        pass

    def send_route_reply(self):
        pass

    def send_route_error(self):
        pass

    def forward_msg(self, broadcast=False):
        pass

    def recv_msg(self, *args):
        pass

    def update_route_request_table(self):
        pass

    def update_routing_table(self):
        pass

    def get_random_LQI(self):
        return random.randrange(30, 150)

    def recieved_message(self):
        # Muss mittels LQI ausgerechnet werden mittels Kurve nach Datenauswertung
        return False

    def update(self):
        while True:
            # Hier auf shared events auf den Leitungen reagieren
            # und sonstiges
            # ....
            yield self.env.timeout(1)
