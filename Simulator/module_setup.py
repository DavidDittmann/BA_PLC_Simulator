from . import node


def setup_nodes(env, topologie, node_config, coord_config, optimized):
    nodes = []
    for node_id, neighbors in topologie.items():
        phy_neighbors = neighbors["neighbors"]
        # coordinator
        if node_id == "0":
            pass
        # node
        else:
            nodes.append(node.Node(env, node_id, phy_neighbors, node_config, optimized))

    return nodes
