"""
Node definition
"""

import random

class Node:
    def __init__(self, env, node_id, phy_neighbors, node_config, optimized):
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
        self.optimized = optimized

        # self.env.timeout(self.rand_join_time)
        self.update()


    def update(self):
        i = 0
        while(True):
            print("Node {}: Meldung {}".format(self.node_id, i))
            i = i + 1
            yield self.env.timeout(100)
