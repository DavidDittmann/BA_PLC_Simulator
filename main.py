import random
import time
import argparse
from Log import log
from Topology_Generator import topologie_generator
from Storage import storage
from Simulator import base_setup

logger = log.Logger().get_logger()
logger.info("Starting program...")


parser = argparse.ArgumentParser(description="Application for generating and simulation of PLC-Network startup.\nWhen additional parameters are set the topologie will get new generated")
parser.add_argument("--n", default=201, type=int, help="Specifying the number of nodes within the topologie. Default =: 201")
parser.add_argument("--sT", default=10, type=int, help="Specifying the emulated simulation time in hours. Default=: 10")
parser.add_argument("--cN", default="node_config.json", type=str, help="Specifying the configuration file used by the nodes. Default =: node_config.json")
parser.add_argument("--cC", default="coord_config.json", type=str, help="Specifying the configuration file used by the coordinator. Default =: coord_config.json")
parser.add_argument("--S", default=random.seed(time.time()), type=int, help="Topologie generation seed, Default =: Current timestamp")
parser.add_argument("--u", action="store_true", help='Generating an urban network topologie? About 40%% of the nodes are directly connected to the coordinator.')
parser.add_argument("--o", action="store_true", help="Using optimized routing strategies?")
parser.add_argument("--l", action="store_true", help="Loading topologie? Loading overrules specified values like the node number!")
parser.add_argument("--lf", default="topologie.json", type=str, help="Loading specified topologie file if possible. Default =: topologie.json")
parser.add_argument("--sf", default="topologie.json", type=str, help="Saving into specified topologie file. Default =: topologie.json")

args = parser.parse_args()
msg = "Settings: " + "; Seed:" + str(args.S) + "; Nodes:" + str(args.n) + "; Urban:" + str(args.u) + "; Optimized:" + str(args.o)
msg = msg + "; SimTime:" + str(args.sT) + "; Configs:" + str(args.cN) + " & " + str(args.cC) + "; Loading:" + str(args.l) + "; LoadFile:" + str(args.lf) + "; SaveFile:" + str(args.sf)
logger.info(msg)

random.seed(args.S)

top_data = None
# Laden einer Topologie falls angegeben und vorhanden
if args.l and storage.is_available(args.lf):
    logger.info("Loading topologie: " + args.lf)
    top_data = storage.read_json(args.lf)
# Generieren einer Topologie und abspeichern
else:
    logger.info("Generating new topologie")
    top_gen = topologie_generator.TopologieGenerator(args.n, args.u)
    top_gen.generate()
    top_data = top_gen.get_topologie_data()
    # TOPOLOGIE SPEICHERN
    storage.write_json(args.sf, top_data)

# print(top_data)
# Simulation starten
node_config = storage.read_json(args.cN)
coord_config = storage.read_json(args.cC)
Simulator = base_setup.Simulator(top_data, args.sT, node_config, coord_config, args.o)
Simulator.start_simulation()


# Daten aufbereiten starten



# Daten ausgeben



# Ende
input("Press Enter to continue...")
