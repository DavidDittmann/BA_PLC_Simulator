import time
import simpy
from . import module_setup
from Log import log

logger = log.Logger().get_logger()

class Simulator:
    def __init__(self, topologie, sim_time, node_config, coord_config, optimized):
        print("Setup Simulation")
        self.env = simpy.Environment()
        self.sim_time = sim_time * 60 * 60 * 1000

        # Einrichten der Nodes und des Koordinators
        self.channels = module_setup.setup_channels(self.env, topologie)
        self.nodes = module_setup.setup_nodes(self.env, topologie, node_config, coord_config, optimized)
        module_setup.update_nodes_channels(self.channels, self.nodes)
        module_setup.startup_nodes(topologie, self.nodes)

        for node in self.nodes:
            print(node, node.neighbor_nodes, node.reading_channels)

        print("Setup complete")

    def start_simulation(self):
        logger.info("Starting simulation...")
        print("Starting simulation...")
        # self.env.process(self.check_node_state())
        self.env.run(until=self.env.process(self.check_node_state()))
        # self.env.run(until=150000)
        # for node in self.nodes[::-1]:
        #     print(node.node_id, node.pan_id)

    def check_node_state(self):
        num_nodes = len(self.nodes)
        num_joined = 0
        while True:
            yield self.env.timeout(60)
            num_joined = 0
            joined_nodes = []
            for node in self.nodes:
                if node.joined:
                    num_joined = num_joined + 1
                    joined_nodes.append(node.node_id)

            logger.info("Joined: {} at {}. {}".format(num_joined/num_nodes * 100, self.env.now, joined_nodes))
            # msg = [(node.node_id, node.joined) for node in self.nodes]
            # for node in self.nodes:
            #    print(node.node_id, node.joined, node.rreq_table, node.routing_table)
            # print(self.env.now, msg)

            if num_joined/num_nodes == 1 or self.env.now > 18000:
                break

        logger.info("{} %% joined after {} seconds".format(num_joined/num_nodes * 100, self.env.now))
        print("{} %% joined after {} seconds".format(num_joined/num_nodes * 100, self.env.now))
        return True
        # python main.py --S 2762 --n 500