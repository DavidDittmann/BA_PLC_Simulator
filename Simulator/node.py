"""
Node definition
"""

import random
import hashlib
# import collections
# import simpy
from . import telegram as tlgm

from Log import log

logger = log.Logger().get_logger()

class Message():
    def __init__(self, created_on, origin, dest, final_dest, msg_type, data=None, sequenznumber=None, checksum=None):
        self.origin = origin
        self.dest = dest
        self.final_dest = final_dest
        self.created_on = created_on
        self.msg_type = msg_type
        self.data = data or {}
        self.sequenznumber = sequenznumber

        self.checksum = checksum or generate_checksum(self.origin, self.final_dest, self.sequenznumber, self.created_on)

    def __repr__(self):
        # return "MESSAGE: FROM {} WITH FINAL {} CREATED AT {} with Data: {}, {} and SQZ: {} via {}".format(self.origin, self.final_dest, self.created_on, self.msg_type, self.data, self.sequenznumber, self.dest)
        return "{} FROM {} VIA {} TO {} WITH CSM {}".format(self.msg_type, self.origin, self.dest, self.final_dest, self.checksum)

def generate_checksum(origin, final_dest, sequenznumber, created_on):
    string = origin + final_dest + str(sequenznumber) + str(created_on)
    return hashlib.md5(string.encode()).hexdigest()
class Writer():
    # TODO: Update forward RC bei absenden mittels aktuellem LQI im Writer!
    def __init__(self, env, _node):
        self.channels = set()
        self.env = env
        self.node = _node
        self.csma_time = 8
        self.last_rreq_id = 0

    def write_message(self):
        while True:
            if self.channels:
                if self.node.output_queue:
                    if self.csma_check():
                        self.csma_time = max(self.csma_time - 64, 8)
                        if self.node.output_queue[0].dest is None:
                            if self.node.routing_table.get(self.node.output_queue[0].final_dest, None):
                                self.node.output_queue[0].dest = self.node.routing_table[self.node.output_queue[0].final_dest]["next_hop_addr"]
                                yield self.env.timeout(0.01)
                            elif self.node.rreq_table.get(self.node.node_id, None) is None:
                                rreq_id = self.node._get_next_sqz_number()
                                self.last_rreq_id = rreq_id
                                msg = Message(self.env.now, self.node.node_id, "-1", self.node.output_queue[0].final_dest, "RREQ", {"rreq_origin": self.node.node_id, "forward_rc": random.randint(5, 20), "hop_count": 1}, rreq_id)
                                # TODO: forward RC von LQI ableiten
                                self.node.rreq_table[self.node.node_id] = {
                                    rreq_id: {
                                        "forward_rc": 10,
                                        "gueltig_bis": self.env.now + self.node.config.get("discovery_time", 20),
                                        "via": self.node.node_id
                                    }
                                }
                                # logger.info("WRITER " + str(msg))
                                # print("NODE {} NEW RREQ FOR DEST {}".format(self.node.node_id, self.node.output_queue[0].final_dest))
                                events = [channel.put(msg) for channel in self.channels]
                                yield self.env.all_of(events)
                            elif self.node.rreq_table.get(self.node.node_id).get(self.last_rreq_id).get("gueltig_bis") < self.env.now:
                                rreq_id = self.node._get_next_sqz_number()
                                self.last_rreq_id = rreq_id
                                msg = Message(self.env.now, self.node.node_id, "-1", self.node.output_queue[0].final_dest, "RREQ", {"rreq_origin": self.node.node_id, "forward_rc": random.randint(5, 20), "hop_count": 1}, rreq_id)
                                # TODO: forward RC von LQI ableiten
                                self.node.rreq_table[self.node.node_id] = {
                                    rreq_id: {
                                        "forward_rc": 10,
                                        "gueltig_bis": self.env.now + self.node.config.get("discovery_time", 20),
                                        "via": self.node.node_id
                                    }
                                }
                                # logger.info("WRITER " + str(msg))
                                # print("NODE {} LATE RREQ FOR DEST {}".format(self.node.node_id, self.node.output_queue[0].final_dest))
                                events = [channel.put(msg) for channel in self.channels]
                                yield self.env.all_of(events)
                            else:
                                # logger.info(" INACTIVE WRITER " + str(msg))
                                # print("{} WAITING FOR RREP TO {}".format(self.node.node_id, self.node.output_queue[0].final_dest))
                                yield self.env.timeout(0.01)
                        else:
                            msg = self.node.output_queue[0]
                            if msg.msg_type in ["ACK", "RREQ", "BREQ", "BREP"]:
                                msg = self.node.output_queue.pop(0)
                            msg.created_on = self.env.now
                            if not self.node.sent_messages.get(msg.checksum) and msg.msg_type not in ["ACK", "RREQ", "BREQ", "BREP"]:
                                self.node.sent_messages[msg.checksum] = {"msg": msg, "tries": 1}
                            elif self.node.sent_messages.get(msg.checksum) and msg.msg_type not in ["ACK", "RREQ", "BREQ", "BREP"]:
                                self.node.sent_messages[msg.checksum]["tries"] = self.node.sent_messages[msg.checksum]["tries"] + 1
                            #logger.info("WRITER " + str(msg) + " TIME: " + str(self.env.now))
                            # print("WRITER of Node {} at {} >>>>{}".format(self.node.node_id, self.env.now, msg))
                            events = [channel.put(msg) for channel in self.channels]
                            yield self.env.all_of(events)
                    else:
                        rng = random.randrange(1, self.csma_time)
                        yield self.env.timeout(rng)
                        self.csma_time = self.csma_time * 2
                        if self.csma_time > 2**8:
                            self.csma_time = 2**8
                else:
                    yield self.env.timeout(0.01)
            else:
                yield self.env.timeout(0.01)

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
                if self.channel.peek().created_on < self.env.now - 0.05:
                    self.channel.get()
                elif self.channel.peek().origin != self.node.node_id and ((self.channel.peek().origin in self.node.get_neighbor_ids() and self.channel.peek().origin in self.channel.get_endpoint_ids()) or self.channel.peek().origin not in self.node.get_neighbor_ids()):
                    msg = self.channel.get()

                    yield msg
                    if msg.value.dest == self.node.node_id or msg.value.dest == "-1":
                        logger.info("READER NODE {} ".format(self.node.node_id) + str(msg.value))
                        # print('at time {} on channel {}: Node {} received message: >>>>{}.'.format(self.env.now, self.channel, self.node.node_id, msg.value))
                        tmp = [str(message.value) for message in self.node.input_queue]
                        tmp2 = [str(message.checksum) for message in self.node.output_queue]
                        if str(msg.value) not in tmp and ((msg.value.msg_type != "ACK" and msg.value.checksum not in tmp2) or msg.value.msg_type == "ACK"):
                            self.node.input_queue.append(msg)
                        if msg.value.sequenznumber is not None and msg.value.msg_type != "RREQ":
                            self.node.output_queue.insert(0, Message(self.env.now, self.node.node_id, msg.value.origin, msg.value.origin, "ACK", checksum=msg.value.checksum))
            yield self.env.timeout(0.01)

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
        self.rnd_jointime = random.randint(5, self.config.get("random_join_time", 120))
        self.last_beacon = None
        self.beacon_tries = 1
        self.sequenznumber = 0
        self.routing_table = {}
        self.rreq_table = {}
        self.joining_table = {}
        self.hop_count = 0
        self.join_agent = {}
        self.clients = []
        self.sent_messages = {}
        self.started_join = False
        # {
        #   checksum: {
        #       msg: msg,
        #       tries: 1
        #   }
        # }

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

    def _get_next_sqz_number(self):
        sqz = self.sequenznumber
        self.sequenznumber = sqz + 1
        return sqz

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
            # print("UPDATE", self.node_id, self.env.now)
            yield self.env.timeout(0.01)

            if self.pan_id is None and self.rnd_jointime <= self.env.now and (self.last_beacon is None or self.last_beacon <= self.env.now - self.config.get("beacon_scan_duration", 12) * self.beacon_tries):
                self.started_join = True
                self.output_queue.append(Message(self.env.now, self.node_id, "-1", "-1", "BREQ"))
                self.last_beacon = self.env.now
                self.beacon_tries = min(self.beacon_tries * 3, 1800) # maximale Wartezeit ist halbe stunde zwischen BeaconReqs

            elif self.input_queue:
                msg = self.input_queue.pop(0)
                msg = msg.value
                if msg.msg_type == "BREQ":
                    if self.joined:
                        self.output_queue.append(Message(self.env.now, self.node_id, msg.origin, msg.origin, "BREP", {"pan_id": self.pan_id, "hop_count": self.hop_count + 1}))
                elif msg.msg_type == "BREP":
                    if not self.join_agent and self.started_join:
                        self.join_agent["node_id"] = msg.origin
                        self.join_agent["hop_count"] = msg.data.get("hop_count", None)
                        self.join_agent["pan_id"] = msg.data.get("pan_id", None)
                        self.pan_id = msg.data.get("pan_id", None)
                        # print("BREP empfangen:", self.node_id, self.pan_id, self.join_agent["node_id"])
                        self.env.process(self.wait_for_agent_responses())
                    elif self.join_agent.get("hop_count") > msg.data.get("hop_count"):
                        self.join_agent["node_id"] = msg.origin
                        self.join_agent["hop_count"] = msg.data.get("hop_count", None)
                        self.join_agent["pan_id"] = msg.data.get("pan_id", None)
                        self.pan_id = msg.data.get("pan_id", None)
                    # JREQ data --> {"joining_id": self.node_id, "agent": self.join_agent["node_id"]}
                elif msg.msg_type == "JREQ":
                    # Koordinator erhält JREQ
                    if self.node_id == "0":
                        agent = msg.data.get("agent")
                        if agent != "0":
                            if self.routing_table.get(agent):
                                self.output_queue.append(Message(self.env.now, self.node_id, self.routing_table[agent]["next_hop_addr"], agent, "MSG1", msg.data, self._get_next_sqz_number()))
                            else:
                                self.output_queue.append(Message(self.env.now, self.node_id, None, agent, "MSG1", msg.data, self._get_next_sqz_number()))
                        else:
                            self.output_queue.append(Message(self.env.now, self.node_id, msg.origin, msg.origin, "MSG1", msg.data, self._get_next_sqz_number()))
                    # AGENT / Zwischennode leitet weiter
                    elif self.joined:
                        # print("JREQ", self.node_id, msg.origin)
                        if self.routing_table.get("0"):
                            self.output_queue.append(Message(self.env.now, self.node_id, self.routing_table["0"]["next_hop_addr"], "0", msg.msg_type, msg.data, msg.sequenznumber))
                        else:
                            self.output_queue.append(Message(self.env.now, self.node_id, None, "0", msg.msg_type, msg.data, msg.sequenznumber))
                # RICHTUNG JOINING NODE
                elif msg.msg_type in ["MSG1", "MSG3"]:
                    if self.joined:
                        if self.node_id == msg.data.get("agent"):
                            joining_id = msg.data.get("joining_id")
                            self.output_queue.append(Message(self.env.now, self.node_id, joining_id, joining_id, msg.msg_type, msg.data, msg.sequenznumber))
                        else:
                            self.output_queue.append(Message(self.env.now, self.node_id, self.routing_table[msg.final_dest]["next_hop_addr"], msg.final_dest, msg.msg_type, msg.data, msg.sequenznumber))
                    elif msg.data.get("joining_id") == self.node_id and self.started_join:
                        msg_type = "MSG2"
                        if msg.msg_type == "MSG3":
                            msg_type = "MSG4"
                        self.output_queue.append(Message(self.env.now, self.node_id, self.join_agent["node_id"], "0", msg_type, msg.data, self._get_next_sqz_number()))
                # RICHTUNG KOORDINATOR
                elif msg.msg_type in ["MSG2", "MSG4"]:
                    if self.joined:
                        agent = msg.data.get("agent")
                        if self.node_id == "0":
                            msg_type = "MSG3"
                            if msg.msg_type == "MSG4":
                                msg_type = "JACC"
                            if agent != "0":
                                self.output_queue.append(Message(self.env.now, self.node_id, self.routing_table[agent]["next_hop_addr"], agent, msg_type, msg.data, self._get_next_sqz_number()))
                            else:
                                self.output_queue.append(Message(self.env.now, self.node_id, msg.origin, msg.origin, msg_type, msg.data, self._get_next_sqz_number()))
                        else:
                            self.output_queue.append(Message(self.env.now, self.node_id, self.routing_table[msg.final_dest]["next_hop_addr"], msg.final_dest, msg.msg_type, msg.data, msg.sequenznumber))
                # JACC / JDEC SIND IMMER RICHTUNG JOINING NODE
                elif msg.msg_type in ["JACC", "JDEC"]:
                    if self.joined:
                        if self.node_id == msg.data.get("agent"):
                            joining_id = msg.data.get("joining_id")
                            self.output_queue.append(Message(self.env.now, self.node_id, joining_id, joining_id, msg.msg_type, msg.data, msg.sequenznumber))
                        elif self.node_id != msg.data.get("joining_id"):
                            self.output_queue.append(Message(self.env.now, self.node_id, self.routing_table[msg.final_dest]["next_hop_addr"], msg.final_dest, msg.msg_type, msg.data, msg.sequenznumber))
                    elif msg.data.get("joining_id") == self.node_id and self.started_join:
                        if msg.msg_type == "JACC":
                            self.joined = True
                            # print("JOINED", self.node_id)
                        else:
                            self.pan_id = None
                            self.join_agent = {}
                            self.last_beacon = None
                            self.rnd_jointime = random.randint(5, self.config.get("random_join_time", 120))
                elif msg.msg_type == "RREQ":
                    # print("RREQ", self.node_id)
                    # ausschluss eigene RREQ
                    if self.joined and msg.data["rreq_origin"] != self.node_id:
                        rreq_origin = msg.data.get("rreq_origin")
                        forward_rc = msg.data.get("forward_rc")
                        hop_count = msg.data.get("hop_count")
                        rreq_id = msg.sequenznumber
                        # Route zu Ziel unbekannt
                        # Eintragung in rreq table falls noch nicht vorhanden oder update falls RC besser / hops weniger. (GÜLTIGKEIT, RREQ ID)
                        # Weiterleitung nur wenn RREQ ID nicht bekannt und max hops nicht überschritten -> Update RC und Hops
                        if msg.final_dest != self.node_id and msg.final_dest not in self.routing_table and hop_count < self.config.get("max_hop_limit", 8):
                            # RREQ mit RREQ ID noch nicht bekannt -> Weiterleitung
                            if self.rreq_table.get(rreq_origin, None) is None:
                                self.rreq_table[rreq_origin] = {
                                    rreq_id: {
                                        "forward_rc": forward_rc,
                                        "gueltig_bis": self.env.now + self.config.get("discovery_time", 20),
                                        "via": msg.origin
                                    }
                                }
                                self.output_queue.append(Message(self.env.now, self.node_id, "-1", msg.final_dest, msg.msg_type, {"rreq_origin": rreq_origin, "hop_count": hop_count + 1, "forward_rc": forward_rc}, msg.sequenznumber))
                            elif self.rreq_table.get(rreq_origin).get(rreq_id, None) is None:
                                self.rreq_table[rreq_origin][rreq_id] = {
                                    "forward_rc": forward_rc,
                                    "gueltig_bis": self.env.now + self.config.get("discovery_time", 20),
                                    "via": msg.origin
                                }
                                self.output_queue.append(Message(self.env.now, self.node_id, "-1", msg.final_dest, msg.msg_type, {"rreq_origin": rreq_origin, "hop_count": hop_count + 1, "forward_rc": forward_rc}, msg.sequenznumber))
                            # RREQ bekannt, update rreq table falls besserer RC in RREQ, keine Weiterleitung
                            else:
                                if forward_rc < self.rreq_table.get(rreq_origin).get(rreq_id).get("forward_rc"):
                                    self.rreq_table[rreq_origin][rreq_id]["via"] = msg.origin
                                    self.rreq_table[rreq_origin][rreq_id]["forward_rc"] = forward_rc

                        # Ziel ist man selbst oder Route zu Ziel bekannt -> Warten auf weitere RREQ mit selber RREQ ID eintragung in RREQ Table
                        # update wenn RC besser und antworten mit RREP wenn wartezeit vorbei!
                        elif msg.final_dest == self.node_id or msg.final_dest in self.routing_table:
                            # rreq neu oder rreg mit rreq id neu -> start sendback time und schedule rrep
                            if self.rreq_table.get(rreq_origin, None) is None:
                                # print(self.config.get("discovery_time"))
                                self.rreq_table[rreq_origin] = {
                                    rreq_id: {
                                        "forward_rc": forward_rc,
                                        "gueltig_bis": self.env.now + self.config.get("discovery_time", 20),
                                        "via": msg.origin
                                    }
                                }
                                if msg.final_dest != self.node_id:
                                    self.env.process(self.wait_for_rreq_send_rrep(rreq_origin, rreq_id, msg.final_dest))
                                else:
                                    self.env.process(self.wait_for_rreq_send_rrep(rreq_origin, rreq_id, self.node_id))
                            elif self.rreq_table.get(rreq_origin).get(rreq_id, None) is None:
                                self.rreq_table[rreq_origin][rreq_id] = {
                                    "forward_rc": forward_rc,
                                    "gueltig_bis": self.env.now + self.config.get("discovery_time", 20),
                                    "via": msg.origin
                                }
                                if msg.final_dest != self.node_id:
                                    self.env.process(self.wait_for_rreq_send_rrep(rreq_origin, rreq_id, msg.final_dest))
                                else:
                                    self.env.process(self.wait_for_rreq_send_rrep(rreq_origin, rreq_id, self.node_id))
                            # update rreq table wenn forward rc besser
                            elif self.rreq_table.get(rreq_origin, None) is not None and self.rreq_table.get(rreq_origin).get(rreq_id, None) is not None:
                                if self.rreq_table.get(rreq_origin).get(rreq_id).get("forward_rc") > forward_rc:
                                    self.rreq_table[rreq_origin][rreq_id]["forward_rc"] = forward_rc
                                    self.rreq_table[rreq_origin][rreq_id]["via"] = msg.origin

                elif msg.msg_type == "RREP":
                    if self.joined:
                        # Ziel ist wer anderer -> weiterleiten, Routing table eintrag/update richtung RREP Originator, Routingtable eintrag zu RREQ Originator, rreq table eintrag löschen
                        rreq_origin = msg.final_dest
                        rrep_origin = msg.data.get("rrep_origin")
                        if msg.final_dest != self.node_id:
                            # routing table update für rreq destination
                            if self.routing_table.get(rrep_origin, None) is None or self.routing_table.get(rrep_origin).get("forward_rc") > msg.data.get("forward_rc"):
                                self.routing_table[rrep_origin] = {
                                    "next_hop_addr": msg.origin,
                                    "forward_rc": msg.data.get("forward_rc"),
                                    "status": True,
                                    "gueltig_bis": self.config.get("node_delete_time", 432000),
                                    "flaged": False,
                                    "retries": 0
                                }
                            # routing table update für rrep destination
                            if self.routing_table.get(rreq_origin, None) is None or self.routing_table.get(rreq_origin).get("forward_rc") > self.rreq_table[rreq_origin][msg.sequenznumber]["forward_rc"]:
                                self.routing_table[rreq_origin] = {
                                    "next_hop_addr": self.rreq_table[rreq_origin][msg.sequenznumber]["via"],
                                    "forward_rc": self.rreq_table[rreq_origin][msg.sequenznumber]["forward_rc"],
                                    "status": True,
                                    "gueltig_bis": self.config.get("node_delete_time", 432000),
                                    "flaged": False,
                                    "retries": 0
                                }

                            # weiterleitung rrep
                            data = msg.data
                            data["hop_count"] = data["hop_count"] + 1
                            self.output_queue.append(Message(self.env.now, self.node_id, self.routing_table[rreq_origin]["next_hop_addr"], rreq_origin, msg.msg_type, data, msg.sequenznumber))
                            # del self.rreq_table[rreq_origin][msg.sequenznumber]
                            # if not self.rreq_table[rreq_origin]:
                            #     del self.rreq_table[rreq_origin]
                        # Ziel ist man selbst -> Routing table update
                        else:
                            self.routing_table[rrep_origin] = {
                                "next_hop_addr": msg.origin,
                                "forward_rc": msg.data.get("forward_rc"),
                                "status": True,
                                "gueltig_bis": self.config.get("node_delete_time", 432000),
                                "flaged": False,
                                "retries": 0
                            }
                            if self.rreq_table.get(self.node_id):
                                del self.rreq_table[self.node_id]

                elif msg.msg_type == "RERR":
                    if self.pan_id is not None:
                        pass
                elif msg.msg_type == "RREPAIR":
                    pass
                elif msg.msg_type == "ACK":
                    checksum = msg.checksum
                    if self.sent_messages.get(checksum):
                        del self.sent_messages[checksum]
                        index = None
                        for num, message in enumerate(self.output_queue):
                            if message.checksum == checksum:
                                index = num
                        if index is not None:
                            self.output_queue.pop(index)

                for checksum, msg_data in self.sent_messages.items():
                    if msg_data["tries"] > 5:
                        if self.joined and not (msg_data["msg"].data.get("joining_id", False) and msg_data["msg"].data.get("joining_id") == msg_data["msg"].dest):
                            #route repair falls nicht zustellbar und nicht zu joining node als dest
                            pass
                        else:
                            # muss msg aus eigenem join verfahren sein und keine antwort --> zurücksetzen des vorgangs!
                            # self.pan_id is None and self.rnd_jointime <= self.env.now and (self.last_beacon is None or self.last_beacon <= self.env.now - self.config.get("beacon_scan_duration", 12) * self.beacon_tries)
                            self.pan_id = None
                            self.rnd_jointime = self.env.now + random.randint(5, self.config.get("random_join_time", 120))
                            self.last_beacon = None
                            self.beacon_tries = 1
                            self.output_queue = []
                            self.input_queue = []
                            self.started_join = False

    def wait_for_rreq_send_rrep(self, rreq_origin, rreq_id, rrep_origin):
        yield self.env.timeout(7)
        destination = self.rreq_table[rreq_origin][rreq_id]["via"]
        forward_rc = self.rreq_table[rreq_origin][rreq_id]["forward_rc"]

        self.routing_table[rreq_origin] = {
            "next_hop_addr": destination,
            "forward_rc": forward_rc,
            "status": True,
            "gueltig_bis": self.config.get("node_delete_time", 432000),
            "flaged": False,
            "retries": 0
        }
        # TODO: forward rc zu zwischennode einfügen durch lqi
        self.output_queue.append(Message(self.env.now, self.node_id, destination, rreq_origin, "RREP", {"rrep_origin": rrep_origin, "forward_rc": 10, "hop_count": 1}, sequenznumber=rreq_id))


    def wait_for_agent_responses(self):
        yield self.env.timeout(self.config.get("discovery_time", 20))
        self.output_queue.append(Message(self.env.now, self.node_id, self.join_agent["node_id"], "0", "JREQ", {"joining_id": self.node_id, "agent": self.join_agent["node_id"]}, self._get_next_sqz_number()))
