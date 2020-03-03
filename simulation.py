"""
Simulation definition
"""
import json
import node

TOPOLOGIE = {}
with open("topologie.json", 'r') as json_file:
    TOPOLOGIE = json.load(json_file)

NODE_CONFIG = {}
with open("node_config.json", 'r') as json_file:
    NODE_CONFIG = json.load(json_file)
