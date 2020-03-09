import simpy
from . import node
from . import coordinator


def setup_nodes(env, topologie, channels, node_config, coord_config, optimized):
    nodes = []
    for node_id, neighbors in topologie.items():
        node_channel = []
        phy_neighbors = neighbors["neighbors"]
        # coordinator
        if node_id == "0":
            for neighbor_id in phy_neighbors.keys():
                channel = None
                channel = channels.get(node_id+":"+neighbor_id, None) or channels.get(neighbor_id+":"+node_id, None)
                if channel is not None:
                    node_channel.append(channel)
            nodes.append(coordinator.Coordinator(env, node_id, phy_neighbors, node_channel, coord_config, optimized))
        # node
        else:
            for neighbor_id in phy_neighbors.keys():
                channel = None
                channel = channels.get(node_id+":"+neighbor_id, None) or channels.get(neighbor_id+":"+node_id, None)
                if channel is not None:
                    node_channel.append(channel)
            nodes.append(node.Node(env, node_id, phy_neighbors, node_channel, node_config, optimized))

    return nodes

def setup_line_resources(env, topologie):
    res = {}
    for node_id, neighbors in topologie.items():
        neighbors = neighbors["neighbors"]
        for node2 in neighbors.keys():
            con = node_id + ":" + node2
            con_inv = node2 + ":" + node_id
            if not res.get(con, None) and not res.get(con_inv, None):
                res[con] = simpy.Store(env, capacity=1)

    return res
