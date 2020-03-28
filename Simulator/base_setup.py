import time
import simpy
from . import module_setup
from Log import log

logger = log.Logger().get_logger()

class Simulator:
    def __init__(self, topologie, sim_time, node_config, coord_config, optimized):
        print("Setup Simulation")
        self.env = simpy.Environment()
        self.sim_time = sim_time * 60 * 60 * 100

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
        self.env.run(until=50)
        # for node in self.nodes[::-1]:
        #     print(node.node_id, node.pan_id)
