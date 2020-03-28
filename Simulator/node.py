"""
Node definition
"""

import random
# import collections
# import simpy
from . import telegram as tlgm

class Message():
    def __init__(self, created_on, origin, dest, final_dest, msg_type, data=None, sequenznumber=None):
        self.origin = origin
        self.dest = dest
        self.final_dest = final_dest
        self.created_on = created_on
        self.msg_type = msg_type
        self.data = data or {}
        self.sequenznumber = sequenznumber
        self.checksum = generate_checksum(self.origin, self.dest, self.final_dest, self.created_on)

    def __repr__(self):
        return "MESSAGE: FROM {} TO {} VIA {} CREATED AT {} with Data: {}".format(self.origin, self.final_dest, self.dest, self.created_on, self.data)

def generate_checksum(origin, dest, final_dest, created_on):
    return 0
class Writer():
    # TODO: when write handle ACK requirement
    def __init__(self, env, Node):
        self.channels = set()
        self.env = env
        self.node = Node

    def write_message(self):
        while True:
            if self.channels:
                if self.node.output_queue:
                    if self.csma_check():
                        if self.node.output_queue[0].dest is None:
                            msg = Message(self.env.now, self.node.node_id, "-1", self.node.output_queue[0].final_dest, "RREQ")
                        else:
                            msg = self.node.output_queue.pop(0)
                        # print("WRITER of Node {} sending msg: {} at {}".format(self.node.node_id, msg, self.env.now))
                        events = [channel.put(msg) for channel in self.channels]
                        yield self.env.all_of(events)
                    else:
                        yield self.env.timeout(random.randint(5, 15)) # TODO: update csma timeout time
                else:
                    yield self.env.timeout(1)
            else:
                yield self.env.timeout(1)

    def add_channel(self, channel):
        self.channels.add(channel)

    def csma_check(self):
        if not self.channels:
            raise RuntimeError("No Channels definied for writer")
        for channel in self.channels:
            if channel.peek():
                return False
        return True

class Reader():
    def __init__(self, env, Node, channel):
        self.env = env
        self.node = Node
        self.channel = channel

    def read_message(self):
        while True:
            if self.channel.peek():
                if (self.node.last_msg is None and self.channel.peek().origin != self.node.node_id) or (self.node.last_msg is not None and self.node.last_msg.value is not self.channel.peek() and self.channel.peek().origin != self.node.node_id):
                    if self.channel.peek().origin == self.node.node_id or (self.channel.peek().origin in self.node.get_neighbor_ids() and self.channel.peek().origin not in self.channel.get_endpoint_ids()):
                        pass
                    else:
                        msg = self.channel.get()
                        self.node.last_msg = msg
                        yield msg
                        # print('at time {} on channel {}: Node {} received message: {}.'.format(self.env.now, self.channel, self.node.node_id, msg.value))
                        if msg.value.dest == self.node.node_id or msg.value.dest == "-1":
                            self.node.input_queue.append(msg)
            yield self.env.timeout(1)

class Node:
    def __init__(self, env, node_id, config, optimized=False):
        self.env = env
        self.node_id = node_id
        self.config = config
        self.pan_id = None
        self.joined = False
        self.optimized = optimized
        self.neighbor_nodes = []
        self.reading_channels = []
        self.writer = Writer(env, self)
        self.readers = []
        self.output_queue = []
        self.input_queue = []
        self.last_msg = None
        self.rnd_jointime = random.random(self.config.get("random_join_time", 120))
        self.last_beacon = None
        self.beacon_tries = 1
        self.sequenznumber = 0
        self.routing_table = {}
        self.rreq_table = {}
        self.joining_table = {}
        self.hop_count = None
        self.join_agent = None

    def __repr__(self):
        return str(self.node_id)

    def start_up(self, neighbor_nodes):
        for node in neighbor_nodes:
            self.neighbor_nodes.append(node)
        for channel in self.reading_channels:
            self.readers.append(Reader(self.env, self, channel))

        for neighbor_node in neighbor_nodes:
            channels = neighbor_node.get_channels()
            for channel in channels:
                self.writer.add_channel(channel)

        for reader in self.readers:
            self.env.process(reader.read_message())
        self.env.process(self.writer.write_message())
        self.env.process(self.update())

        # if self.node_id == "0":
        #     self.output_queue.append(Message(self.env.now, "0", "0", "-1", "-1", "DATA"))

    def get_channels(self):
        return self.reading_channels

    def add_channel(self, channel):
        self.reading_channels.append(channel)

    def put_message(self, message):
        self.output_queue.append(message)

    def get_neighbor_ids(self):
        return [node.node_id for node in self.neighbor_nodes]

    def revoke_route(self):
        pass

    def add_route(self, destination, final_dest):
        pass

    def update(self):
        while True:
            yield self.env.timeout(1)

            if self.pan_id is None and self.rnd_jointime <= self.env.now and (self.last_beacon is None or self.last_beacon <= self.env.now - self.config.get("beacon_scan_duration", 12) * self.beacon_tries):
                self.output_queue.append(Message(self.env.now, self.node_id, "-1", "-1", "BREQ"))
                self.last_beacon = self.env.now
                self.beacon_tries = min(self.beacon_tries * 3, 150000) # maximale Wartezeit ist halbe stunde zwischen BeaconReqs

            if self.pan_id is not None and self.join_agent is not None and self.env.now >= self.last_beacon + (self.config.get("discovery_time", 40) * 1000):
                self.output_queue.append(Message(self.env.now, self.node_id, self.join_agent["agent"], self.join_agent["agent"], "JREQ", {"JREQ_Origin": self.node_id}, sequenznumber=0))
                self.join_agent = None

            elif self.input_queue:
                msg = self.input_queue.pop(0)
                if msg.msg_type == "BREQ":
                    if self.joined:
                        self.output_queue.append(Message(self.env.now, self.node_id, msg.origin, msg.origin, "BREP", {"pan_id": self.pan_id, "hop_count": self.hop_count + 1}))
                elif msg.msg_type == "BREP":
                    if self.env.now < self.last_beacon + (self.config.get("discovery_time", 40) * 1000):
                        if self.join_agent is None or self.join_agent.get("hop_count") > msg.data.get("hop_count", 9999):
                            self.join_agent["agent"] = msg.origin
                            self.join_agent["hop_count"] = msg.data.get("hop_count", None)
                            self.join_agent["pan_id"] = msg.data.get("pan_id", None)
                            self.pan_id = msg.data.get("pan_id", None)
                            self.hop_count = self.join_agent["hop_count"] + 1
                elif msg.msg_type == "JREQ":
                    if self.joined:
                        self.joining_table[msg.data.get("join_origin")] = msg.origin
                        self.output_queue.append(Message(self.env.now, self.node_id, self.routing_table.get("0", None), "0", "JREQ", msg.data, msg.sequenznumber))
                elif msg.msg_type in ["MSG1", "MSG2", "MSG3", "MSG4"]:
                    if self.joined:
                        if msg.data.get("join_origin", None) and msg.data.get("join_origin") == self.node_id:
                            # eigener join request ablauf
                            if msg.msg_type == "MSG1":
                                self.output_queue.append(Message(self.env.now, self.node_id, self.join_agent.get("agent"), "0", "MSG2", {"join_origin": self.node_id}, self.sequenznumber))
                            elif msg.msg_type == "MSG3":
                                self.output_queue.append(Message(self.env.now, self.node_id, self.join_agent.get("agent"), "0", "MSG4", {"join_origin": self.node_id}, self.sequenznumber))
                        elif msg.data.get("join_origin", None) and msg.data.get("join_origin") != self.node_id:
                            # join weiterleitung als agent
                            if msg.msg_type in ["MSG1", "MSG3"]:
                                # Richtung Node
                                self.output_queue.append(Message(self.env.now, self.node_id, self.joining_table.get(msg.data.get("join_origin")), msg.data.get("join_origin"), msg.msg_type, msg.data, msg.sequenznumber))
                            else:
                                # Richtung Koordinator
                                self.joining_table[msg.data.get("join_origin")] = msg.origin
                                self.output_queue.append(Message(self.env.now, self.node_id, self.routing_table.get("0", None), "0", msg.msg_type, msg.data, msg.sequenznumber))
                elif msg.msg_type in ["JACC", "JDEC"]:
                    #TODO: self.joined True wenn hop_count und pan_id gesetzt
                    if msg.data.get("join_origin", None) and msg.data.get("join_origin") == self.node_id:
                        # Join ACC für Node selbst
                        if msg.msg_type == "JACC" and self.pan_id and self.hop_count:
                            self.joined = True
                        else:
                            self.pan_id = None
                            self.hop_count = None
                        self.join_agent = None
                    elif msg.data.get("join_origin", None) and msg.data.get("join_origin") != self.node_id:
                        self.output_queue.append(Message(self.env.now, self.node_id, self.joining_table.get(msg.data.get("join_origin")), msg.data.get("join_origin"), msg.msg_type, msg.sequenznumber))
                elif msg.msg_type == "RREQ":
                    if self.joined:
                        if msg.final_dest in self.routing_table:
                            self.output_queue.append(Message(self.env.now, self.node_id, msg.origin, msg.data["rreq_origin"], "RREP", {"hop_count": msg.data["hop_count"] + self.routing_table[msg.final_dest]["hop_count"]}))
                        else:
                            self.output_queue.append(Message(self.env.now, self.node_id, "-1", msg.final_dest, "RREQ", {"hop_count": msg.data["hop_count"] + 1}))
                elif msg.msg_type == "RREP":
                    if self.joined:
                        pass
                elif msg.msg_type == "RERR":
                    if self.pan_id is not None:
                        pass
                elif msg.msg_type == "RREPAIR":
                    pass


            # if self.input_queue:
            #     msg = self.input_queue[0].value
            #     msg = Message(self.env.now, self.node_id, self.node_id, -1, -1, "DATA")
            #     self.output_queue.append(msg)