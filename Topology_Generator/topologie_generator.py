import json
import random

def get_random_LQI():
    return random.randrange(30, 150)

class NODE:
    def __init__(self, _id):
        self.id = _id
        self.neighbors = {}

    def set_neighbor(self, neighbor_node_id, lqi):
        self.neighbors[str(neighbor_node_id)] = lqi

    def get_neighbor_list(self):
        return list(self.neighbors.keys())

    def __repr__(self):
        return str(self.id) + str(self.neighbors)

class TopologieGenerator:
    def __init__(self, node_number, urban):
        self.node_number = node_number
        self.urban = urban
        self.nodes = [NODE(0)]

    def _generate_basetree(self):
        for num in range(1, self.node_number + 1):
            node = NODE(num)
            # jede erzeugte Node bekommt zunächst einen Random Neighbor
            if self.urban:
                # 40% direkt gelinkt zu koordinator
                if random.randrange(10) >= 4:
                    rand = random.randrange(num)
                    node.set_neighbor(rand, get_random_LQI())
                    self.nodes.append(node)
                else:
                    node.set_neighbor(0, get_random_LQI())
                    self.nodes.append(node)
            else:
                rand = random.randrange(num)
                node.set_neighbor(rand, get_random_LQI())
                self.nodes.append(node)

    def _link_reverse(self):
        for node in self.nodes:
            neighbors = node.get_neighbor_list()
            for neighbor in neighbors:
                _node = self.nodes[int(neighbor)]
                _node.set_neighbor(str(node.id), get_random_LQI())

    def _generate_alternate_links(self):
        if self.node_number >= 10:
            for num in range(10, self.node_number, 4):
                # jede erzeugte Node bekommt zunächst einen Random Neighbor
                passed = False
                node = self.nodes[num]
                num_neighbors = len(list(self.nodes[num].neighbors))

                tmp = 1
                while tmp == 1:
                    rand = random.randrange(num_neighbors)
                    selected_node_id = list(self.nodes[num].neighbors)[rand]
                    tmp = len(list(self.nodes[int(selected_node_id)].neighbors))
                while not passed:
                    num_neighbors = len(list(self.nodes[int(selected_node_id)].neighbors))
                    rand = random.randrange(num_neighbors)
                    alt_id = list(self.nodes[int(selected_node_id)].neighbors)[rand]
                    passed = not node.id == alt_id
                node.set_neighbor(alt_id, get_random_LQI())

    def generate(self):
        self._generate_basetree()
        self._link_reverse()
        self._generate_alternate_links()

    def get_topologie_data(self):
        node_data = {}
        for node in self.nodes:
            node_data[str(node.id)] = {
                "neighbors": node.neighbors
            }

        from graphviz import Graph
        graph = Graph("PLC-Topologie", filename="topologie.gv")
        # graph.edge(str(Node.id), str(alt_id))
        tmp = []
        del_list = []
        for node in self.nodes:
            for neighbor in node.neighbors:
                if str(node.id) == neighbor:
                    del_list.append(node.id)
                elif str(node.id) + ":" + str(neighbor) not in tmp and str(neighbor) + ":" + str(node.id) not in tmp:
                    tmp.append(str(node.id) + ":" + str(neighbor))
                    graph.edge(str(node.id), str(neighbor))

        for node in self.nodes:
            if node.id in del_list:
                del node.neighbors[str(node.id)]
        graph.view()

        return node_data
