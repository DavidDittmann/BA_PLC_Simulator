"""
Node definition
"""

import random
import hashlib
from Log import log
from . import reader_writer as rw

logger = log.Logger().get_logger()

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
        self.writer = rw.Writer(env, self)
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
        self.joined_nodes = []

    def __repr__(self):
        return str(self.node_id)

    def start_up(self, neighbor_nodes):
        for node in neighbor_nodes:
            self.neighbor_nodes.append(node)
        for channel in self.reading_channels:
            self.readers.append(rw.Reader(self.env, self, channel))

        for neighbor_node in neighbor_nodes:
            channels = neighbor_node.get_channels()
            for channel in channels:
                self.writer.add_channel(channel)

        for reader in self.readers:
            self.env.process(reader.read_message())
        self.env.process(self.writer.write_message())
        self.env.process(self.update())

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

    # TODO: node_delete_time
    # TODO: reconnection_timeout
    # TODO: BLACKLISTING

    def update(self):
        while True:
            yield self.env.timeout(0.01)

            # BREQ senden wenn keine PAN-ID + Rng Jointime vorbei + Beacon nicht beantwortet in zeit (beacon_scan_duration)
            if self.pan_id is None and self.rnd_jointime <= self.env.now and (self.last_beacon is None or self.last_beacon < self.env.now - self.config.get("beacon_scan_duration", 12) * self.beacon_tries):
                self.started_join = True
                self.output_queue.append(rw.Message(self.node_id, "-1", "-1", "BREQ", created_on=self.env.now))
                self.last_beacon = self.env.now
                self.beacon_tries = min(self.beacon_tries * 3, 1800) # maximale Wartezeit ist halbe stunde zwischen BeaconReqs

            elif self.input_queue:

                msg = self.input_queue.pop(0)
                if msg.msg_type == "BREQ":
                    # Jede gejointe Node darf BREP senden
                    if self.joined:
                        self.output_queue.append(rw.Message(self.node_id, msg.origin, msg.origin, "BREP", self.env.now, {"pan_id": self.pan_id, "hop_count": self.hop_count + 1}))
                elif msg.msg_type == "BREP":
                    # Noch kein Join agent vorhanden
                    if not self.join_agent and self.started_join:
                        self.join_agent["node_id"] = msg.origin
                        self.join_agent["hop_count"] = msg.data.get("hop_count", None)
                        self.join_agent["pan_id"] = msg.data.get("pan_id", None)
                        self.pan_id = msg.data.get("pan_id", None)
                        self.env.process(self.wait_for_agent_responses())
                        # joinagent vorhanden, warten auf bessere responses (hopcount zu coordinator entscheidend) oder coordinator direkt
                    elif self.started_join and self.join_agent.get("hop_count") > msg.data.get("hop_count") or msg.origin == "0":
                        self.join_agent["node_id"] = msg.origin
                        self.join_agent["hop_count"] = msg.data.get("hop_count", None)
                        self.join_agent["pan_id"] = msg.data.get("pan_id", None)
                        self.pan_id = msg.data.get("pan_id", None)

                elif msg.msg_type == "JREQ":
                    # Koordinator erhält JREQ
                    if self.node_id == "0" and msg.data["joining_id"] not in self.joined_nodes:
                        agent = msg.data.get("agent")
                        if agent == "0":
                            self.output_queue.append(rw.Message(self.node_id, msg.origin, msg.origin, "MSG1", self.env.now, msg.data, self._get_next_sqz_number()))
                        else:
                            self.routed_sending(self.node_id, agent, "MSG1", self.env.now, msg.data, self._get_next_sqz_number())

                    # AGENT / Zwischennode leitet weiter. angemeldet und join von joining_id node noch nicht fix
                    elif self.joined and msg.data["joining_id"] not in self.joined_nodes:
                        self.routed_sending(self.node_id, "0", msg.msg_type, self.env.now, msg.data, msg.sequenznumber)

                # RICHTUNG JOINING NODE
                elif msg.msg_type in ["MSG1", "MSG3"]:
                    # weiterleiten man joined ist und nicht selbst das ziel und join noch nicht bekannt
                    if self.joined and msg.data.get("joining_id") != self.node_id and msg.data["joining_id"] not in self.joined_nodes:
                        # man ist der agent zur joining_id und diese ist noch nicht als joined bekannt
                        if self.node_id == msg.final_dest and msg.data["joining_id"] not in self.joined_nodes:
                            joining_id = msg.data.get("joining_id")
                            self.output_queue.append(rw.Message(self.node_id, joining_id, joining_id, msg.msg_type, self.env.now, msg.data, msg.sequenznumber))
                        # nicht der agent und join der ziel node noch unbekannt -> weiterleitung nächste node bis agent
                        elif self.node_id != msg.final_dest and msg.data["joining_id"] not in self.joined_nodes:
                            self.routed_sending(self.node_id, msg.final_dest, msg.msg_type, self.env.now, msg.data, msg.sequenznumber)
                    # Ziel ist man selbst und man ist noch nicht gejoined
                    elif not self.joined and msg.data.get("joining_id") == self.node_id and self.started_join and self.join_agent:
                        msg_type = "MSG2"
                        if msg.msg_type == "MSG3":
                            msg_type = "MSG4"
                        self.output_queue.append(rw.Message(self.node_id, self.join_agent["node_id"], "0", msg_type, self.env.now, msg.data, self._get_next_sqz_number()))

                # RICHTUNG KOORDINATOR
                elif msg.msg_type in ["MSG2", "MSG4"]:
                    # Koordinator erreicht und join noch nicht bekannt
                    if self.node_id == "0" and msg.data["joining_id"] not in self.joined_nodes:
                        agent = msg.data.get("agent")
                        msg_type = "MSG3"
                        if msg.msg_type == "MSG4":
                            msg_type = "JACC"
                            self.joined_nodes.append(msg.data["joining_id"])
                        # Koord direkt angesprochen
                        if agent == "0":
                            self.output_queue.append(rw.Message(self.node_id, msg.origin, msg.origin, msg_type, self.env.now, msg.data, self._get_next_sqz_number()))
                        else:
                            self.routed_sending(self.node_id, agent, msg_type, self.env.now, msg.data, self._get_next_sqz_number())
                    # Weiterleitung wenn join noch nicht bekannt
                    elif self.joined and msg.data["joining_id"] not in self.joined_nodes:
                        self.routed_sending(self.node_id, msg.final_dest, msg.msg_type, self.env.now, msg.data, msg.sequenznumber)

                # JACC / JDEC SIND IMMER RICHTUNG JOINING NODE
                elif msg.msg_type in ["JACC", "JDEC"]:
                    # weiterleiten man joined ist und nicht selbst das ziel und join noch nicht bekannt
                    if self.joined and msg.data.get("joining_id") != self.node_id and msg.data["joining_id"] not in self.joined_nodes:
                        joining_id = msg.data.get("joining_id")
                        # man ist der agent zur joining_id und diese ist noch nicht als joined bekannt
                        if self.node_id == msg.final_dest and msg.data["joining_id"] not in self.joined_nodes:
                            self.output_queue.append(rw.Message(self.node_id, joining_id, joining_id, msg.msg_type, self.env.now, msg.data, msg.sequenznumber, msg.checksum, msg.hop_count + 1))
                            if msg.msg_type == "JACC":
                                self.joined_nodes.append(joining_id)
                        # nicht der agent und join der ziel node noch unbekannt -> weiterleitung nächste node bis agent
                        elif self.node_id != msg.final_dest and msg.data["joining_id"] not in self.joined_nodes:
                            self.routed_sending(self.node_id, msg.final_dest, msg.msg_type, self.env.now, msg.data, msg.sequenznumber, msg.checksum, msg.hop_count + 1)
                            if msg.msg_type == "JACC":
                                self.joined_nodes.append(joining_id)
                    # Ziel ist man selbst und man ist noch nicht gejoined
                    elif not self.joined and msg.data.get("joining_id") == self.node_id and self.started_join:
                        if msg.msg_type == "JACC":
                            self.joined = True
                            self.hop_count = msg.hop_count or 2
                        else:
                            self.reset_joining_process()

                elif msg.msg_type == "RREQ":
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
                            if self.rreq_table.get(rreq_origin, None) is None or self.rreq_table.get(rreq_origin).get(rreq_id, None) is None:
                                self.output_queue.append(rw.Message(self.node_id, "-1", msg.final_dest, msg.msg_type, self.env.now, {"rreq_origin": rreq_origin, "hop_count": hop_count + 1, "forward_rc": forward_rc}, msg.sequenznumber))

                            self.update_rreq_table(rreq_origin, rreq_id, forward_rc, msg.origin)

                        # Ziel ist man selbst oder Route zu Ziel bekannt -> Warten auf weitere RREQ mit selber RREQ ID eintragung in RREQ Table
                        # update wenn RC besser und antworten mit RREP wenn wartezeit vorbei!
                        elif msg.final_dest == self.node_id or (msg.final_dest in self.routing_table and rreq_origin != self.routing_table[msg.final_dest]["next_hop_addr"]):
                            # rreq neu oder rreg mit rreq id neu -> start sendback time und schedule rrep
                            self.update_rreq_table(rreq_origin, rreq_id, forward_rc, msg.origin)

                            if msg.final_dest != self.node_id:
                                self.env.process(self.wait_for_rreq_send_rrep(rreq_origin, rreq_id, msg.final_dest))
                            else:
                                self.env.process(self.wait_for_rreq_send_rrep(rreq_origin, rreq_id, self.node_id))

                elif msg.msg_type == "RREP":
                    if self.joined:
                        # Ziel ist wer anderer -> weiterleiten, Routing table eintrag/update richtung RREP Originator, Routingtable eintrag zu RREQ Originator, rreq table eintrag löschen
                        rreq_origin = msg.final_dest
                        rrep_origin = msg.data.get("rrep_origin")

                        # RREP Weiterleitung + Speichern der Route
                        if msg.final_dest != self.node_id:
                            # routing table update für rreq destination
                            self.update_routing_table(rrep_origin, msg.origin, msg.data.get("forward_rc"))

                            # routing table update für rrep destination
                            if self.rreq_table.get(rreq_origin, False) and self.rreq_table[rreq_origin].get(msg.sequenznumber, False):
                                self.update_routing_table(rreq_origin, self.rreq_table[rreq_origin][msg.sequenznumber]["via"], self.rreq_table[rreq_origin][msg.sequenznumber]["forward_rc"])

                            # weiterleitung rrep
                            data = msg.data
                            data["hop_count"] = data["hop_count"] + 1
                            if self.routing_table.get(rreq_origin, None):
                                self.output_queue.append(rw.Message(self.node_id, self.routing_table[rreq_origin]["next_hop_addr"], rreq_origin, msg.msg_type, self.env.now, data, msg.sequenznumber))
                        # Ziel ist man selbst -> Routing table update
                        else:
                            self.update_routing_table(rrep_origin, msg.origin, msg.data.get("forward_rc"))

                            if rrep_origin == "0":
                                self.hop_count = msg.data["hop_count"]

                            if self.rreq_table.get(self.node_id):
                                del self.rreq_table[self.node_id]

                elif msg.msg_type == "RERR":
                    if self.joined:
                        if self.routing_table.get(msg.data["delete_node"], None) is not None:
                            del self.routing_table[msg.data["delete_node"]]

                        if self.node_id != msg.final_dest:
                            self.routed_sending(self.node_id, msg.final_dest, msg.msg_type, self.env.now, msg.data, msg.sequenznumber, msg.checksum)

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

                # update der destination adressen für outgoing nachrichten
                for message in self.output_queue:
                    if self.routing_table.get(message.final_dest, None) is not None:
                        message.dest = self.routing_table[message.final_dest]["next_hop_addr"]

                self.check_stored_messages()

                if not self.joined and self.last_beacon and self.last_beacon < self.env.now - 1200:
                    self.reset_joining_process()

    def routed_sending(self, origin, final_dest, msg_type, time=None, data=None, sqz=None, chs=None, hops=None):
        if self.routing_table.get(final_dest):
            self.output_queue.append(rw.Message(origin, self.routing_table[final_dest]["next_hop_addr"], final_dest, msg_type, time, data, sqz, chs, hops))
        else:
            self.output_queue.append(rw.Message(origin, None, final_dest, msg_type, time, data, sqz, chs, hops))

    def update_routing_table(self, dest, next_hop_addr, forward_rc, gueltig_bis=None):
        gueltig_bis = gueltig_bis or self.env.now + self.config.get("node_delete_time", 432000)
        if self.routing_table.get(dest, None) is None or self.routing_table[dest].get("forward_rc") > forward_rc:
            self.routing_table[dest] = {
                "next_hop_addr": next_hop_addr,
                "forward_rc": forward_rc,
                "status": True,
                "gueltig_bis": gueltig_bis,
                "flaged": False,
                "retries": 0
            }

    def update_rreq_table(self, rreq_origin, rreq_id, forward_rc, via, gueltig_bis=None):
        gueltig_bis = gueltig_bis or self.env.now + self.config.get("discovery_time", 20)
        if self.rreq_table.get(rreq_origin, None) is None:
            self.rreq_table[rreq_origin] = {
                rreq_id: {
                    "forward_rc": forward_rc,
                    "gueltig_bis": gueltig_bis,
                    "via": via
                }
            }
        elif self.rreq_table[rreq_origin].get(rreq_id, None) is None:
            self.rreq_table[rreq_origin][rreq_id] = {
                "forward_rc": forward_rc,
                "gueltig_bis": gueltig_bis,
                "via": via
            }
        elif self.rreq_table[rreq_origin][rreq_id].get("forward_rc") > forward_rc:
            self.rreq_table[rreq_origin][rreq_id] = {
                "forward_rc": forward_rc,
                "gueltig_bis": gueltig_bis,
                "via": via
            }

    def check_stored_messages(self):
        # Duplikate entfernen
        if self.output_queue:
            tmp = self.output_queue[1:]
            first = self.output_queue[0]
            self.output_queue = [message for message in tmp if not rw.Message.is_equal(first, message)]
            self.output_queue.insert(0, first)

        # # Veraltete Nachrichten verwerfen
        if self.output_queue:
            self.output_queue = [message for message in self.output_queue if message.created_on > self.env.now - 60]

        del_checksums = []
        for checksum, msg_data in self.sent_messages.items():
            if msg_data["tries"] > 10:
                if self.joined and not (msg_data["msg"].data.get("joining_id", False) and msg_data["msg"].data.get("joining_id") == msg_data["msg"].dest):
                    #route repair falls nicht zustellbar und nicht zu joining node als dest
                    logger.error(str(self.node_id) + " " + str(checksum) + " " + str(msg_data))
                    if self.routing_table.get(msg_data["msg"].final_dest, None) is not None:
                        del self.routing_table[msg_data["msg"].final_dest]
                    if msg_data["msg"].msg_type == "RREP":
                        self.create_rerr(msg_data["msg"])
                    else:
                        for message in self.output_queue:
                            if message.checksum == checksum:
                                message.dest = None
                    del_checksums.append(checksum)
                elif not self.joined:
                    # muss msg aus eigenem join verfahren sein und keine antwort --> zurücksetzen des vorgangs!
                    # self.pan_id is None and self.rnd_jointime <= self.env.now and (self.last_beacon is None or self.last_beacon <= self.env.now - self.config.get("beacon_scan_duration", 12) * self.beacon_tries)
                    self.reset_joining_process()
        for checksum in del_checksums:
            del self.sent_messages[checksum]

    def create_rerr(self, msg):
        # self.output_queue.append(rw.Message(self.node_id, destination, rreq_origin, "RREP", self.env.now, {"rrep_origin": rrep_origin, "forward_rc": 0, "hop_count": 1}, sequenznumber=rreq_id))
        self.output_queue.insert(0, rw.Message(self.node_id, None, msg.final_dest, msg.msg_type, self.env.now, data=msg.data, sequenznumber=msg.sequenznumber))
        if self.node_id != msg.data["rrep_origin"] and self.routing_table.get(msg.data["rrep_origin"]):
            self.output_queue.insert(0, rw.Message(self.node_id, self.routing_table[msg.data["rrep_origin"]]["next_hop_addr"], msg.data["rrep_origin"], "RERR", self.env.now, {"delete_node": msg.final_dest}))

    def reset_joining_process(self):
        self.pan_id = None
        self.join_agent = {}
        self.last_beacon = None
        self.rnd_jointime = self.env.now + random.randint(5, self.config.get("random_join_time", 120))
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
        self.output_queue.append(rw.Message(self.node_id, destination, rreq_origin, "RREP", self.env.now, {"rrep_origin": rrep_origin, "forward_rc": 0, "hop_count": 1}, sequenznumber=rreq_id))


    def wait_for_agent_responses(self):
        yield self.env.timeout(self.config.get("discovery_time", 20))
        if self.join_agent:
            self.output_queue.append(rw.Message(self.node_id, self.join_agent["node_id"], "0", "JREQ", self.env.now, {"joining_id": self.node_id, "agent": self.join_agent["node_id"]}, self._get_next_sqz_number()))
