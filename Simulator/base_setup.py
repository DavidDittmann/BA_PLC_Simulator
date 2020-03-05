import simpy
from . import module_setup
from Log import log

logger = log.Logger().get_logger()

class Simulator:
    def __init__(self, topologie, sim_time, node_config, coord_config, optimized):
        self.env = simpy.Environment()
        self.start_sim_event = self.env.event()
        self.sim_time = sim_time * 60 * 60 * 100

        # Einrichten der Nodes und des Koordinators
        self.nodes = module_setup.setup_nodes(self.env, topologie, node_config, coord_config, optimized)

    def start_simulation(self):
        logger.info("Starting simulation...")
        for node in self.nodes:
            self.env.process(node.update())
        self.env.run(until=self.sim_time)
