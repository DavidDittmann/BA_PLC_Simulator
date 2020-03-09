import time
import simpy
from . import module_setup
from Log import log

logger = log.Logger().get_logger()

class Simulator:
    def __init__(self, topologie, sim_time, node_config, coord_config, optimized):
        print("Setup Simulation")
        self.env = simpy.Environment()
        self.start_sim_event = self.env.event()
        self.sim_time = sim_time * 60 * 60 * 100

        # Einrichten der Nodes und des Koordinators
        self.res = module_setup.setup_line_resources(self.env, topologie)
        self.nodes = module_setup.setup_nodes(self.env, topologie, self.res, node_config, coord_config, optimized)

        print("Setup complete")

    def start_simulation(self):
        logger.info("Starting simulation...")
        print("Starting simulation...")
        for node in self.nodes[::-1]:
            self.env.process(node.update())
        self.env.run(until=200)
