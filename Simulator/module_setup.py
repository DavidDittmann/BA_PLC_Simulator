import simpy
from . import node
from . import coordinator

class CustomStore(simpy.Store):
    def __init__(self, env, lqi, capacity=float('inf')):
        super().__init__(env, capacity=float('inf'))
        self.endpoints = []
        self.lqi = lqi

    def peek(self):
        if self.items:
            return self.items[0]
        return None

    def add_endpoint(self, endpoint):
        self.endpoints.append(endpoint)

    def get_endpoint_ids(self):
        return [node.node_id for node in self.endpoints]

    def get_channel_data(self):
        item = None
        if self.items:
            item = self.items[0]
            return "CHANNEL" + str(self.get_endpoint_ids()) + " " +str(item)
        return None

    def __repr__(self):
        return "Channel" + str(self.get_endpoint_ids())

def setup_nodes(env, topologie, node_config, coord_config, optimized):
    nodes = []
    for node_id in topologie.keys():
        # coordinator
        if node_id == "0":
            nodes.append(coordinator.Coordinator(env, node_id, coord_config, optimized))
        # node
        else:
            nodes.append(node.Node(env, node_id, node_config, optimized))
    return nodes

def setup_channels(env, topologie):
    res = {}
    for node_id, neighbors in topologie.items():
        neighbors = neighbors["neighbors"]
        for node2, lqi in neighbors.items():
            con = node_id + ":" + node2
            con_inv = node2 + ":" + node_id
            if not res.get(con, None) and not res.get(con_inv, None):
                res[con] = CustomStore(env, lqi, capacity=1)
    return res

def update_nodes_channels(channels, nodes):
    # channel01.add_endpoint(Node0)
    for name, channel in channels.items():
        node_name_1 = name.split(':')[0]
        node_name_2 = name.split(':')[1]
        for Node in nodes:
            if Node.node_id == node_name_1 or Node.node_id == node_name_2:
                channel.add_endpoint(Node)
                Node.add_channel(channel)

def startup_nodes(topologie, nodes):
    for node_id, neighbors in topologie.items():
        neighbors = neighbors["neighbors"].keys()
        base_node = [node for node in nodes if node.node_id == node_id][0]
        n_nodes = [node for node in nodes if node.node_id in neighbors]
        base_node.start_up(n_nodes)
