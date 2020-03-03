import random
# Auch wieder mit random LQI!
import time
from graphviz import Graph
import json

# seed = time.time()
seed = 1583142593
random.seed(seed)
print(int(seed))

URBAN = False
URBAN_THRESHHOLD = 4    # -> 40% auf direkt am Koordinator

graph = Graph("PLC-Topologie", filename="topologie.gv")

def get_Random_LQI():
    return random.randrange(30, 150)

class NODE:
    def __init__(self, _id):
        self.id = _id
        self.neighbors = {}

    def set_neighbor(self, neighbor_node_id, LQI):
        self.neighbors[neighbor_node_id] = LQI

    def get_neighbor_list(self):
        return list(self.neighbors.keys())

    def __repr__(self):
        return str(self.id) + str(self.neighbors)

class COORDINATOR(NODE):
    pass

number_nodes = 51
NODES = []

NODES.append(COORDINATOR(0))

for num in range(1, number_nodes):
    Node = NODE(num)
    # jede erzeugte Node bekommt zunächst einen Random Neighbor
    if URBAN:
        if random.randrange(10) >= URBAN_THRESHHOLD:
            rand = random.randrange(num)
            Node.set_neighbor(rand, get_Random_LQI())
            NODES.append(Node)
            graph.edge(str(Node.id), str(rand))
        else:
            Node.set_neighbor(0, get_Random_LQI())
            NODES.append(Node)
            graph.edge(str(Node.id), str(0))
    else:
        rand = random.randrange(num)
        Node.set_neighbor(rand, get_Random_LQI())
        NODES.append(Node)
        graph.edge(str(Node.id), str(rand))

# Nun muss durch alle Nodes durchgegangen werden, damit die Verbindungen bidirektional sind!
for Node in NODES:
    neighbors = Node.get_neighbor_list()
    for neighbor in neighbors:
        _node = NODES[neighbor]
        _node.set_neighbor(Node.id, get_Random_LQI())

# Alternative Routen
if number_nodes >= 10:
    for num in range(10, number_nodes, 4):
        # jede erzeugte Node bekommt zunächst einen Random Neighbor
        passed = False
        Node = NODES[num]
        num_neighbors = len(list(NODES[num].neighbors))

        tmp = 1
        while tmp == 1:
            rand = random.randrange(num_neighbors)
            selected_node_id = list(NODES[num].neighbors)[rand]
            tmp = len(list(NODES[selected_node_id].neighbors))
        while not passed:
            num_neighbors = len(list(NODES[selected_node_id].neighbors))
            rand = random.randrange(num_neighbors)
            alt_id = list(NODES[selected_node_id].neighbors)[rand]
            passed = not Node.id == alt_id
        Node.set_neighbor(alt_id, get_Random_LQI())
        graph.edge(str(Node.id), str(alt_id))

NODE_DATA = {}
for Node in NODES:
    NODE_DATA[Node.id] = {
        "neighbors": Node.neighbors
    }
with open("topologie.json", 'w') as json_file:
    json.dump(NODE_DATA, json_file)

graph.view()
