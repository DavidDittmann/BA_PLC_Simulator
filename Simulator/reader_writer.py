"""
Node definition
"""

import random
import hashlib
from Log import log

logger = log.Logger().get_logger()

NON_ACK_TYPES = ["ACK", "RREQ", "BREQ", "BREP"]
ACK_TYPES = ["JREQ", "MSG1", "MSG2", "MSG3", "MSG4", "JACC", "JDEC", "RREP", "RERR", "RREPAIR"]

class Message():
    def __init__(self, origin, dest, final_dest, msg_type, created_on=None, data=None, sequenznumber=None, checksum=None, hop_count=None):
        self.origin = origin
        self.dest = dest
        self.final_dest = final_dest
        self.created_on = created_on
        self.msg_type = msg_type
        self.data = data or {}
        self.sequenznumber = sequenznumber
        self.hop_count = hop_count or 1

        self.checksum = checksum or self.generate_checksum(self.origin, self.final_dest, self.sequenznumber, self.created_on)

    def __repr__(self):
        # return "MESSAGE: FROM {} WITH FINAL {} CREATED AT {} with Data: {}, {} and SQZ: {} via {}".format(self.origin, self.final_dest, self.created_on, self.msg_type, self.data, self.sequenznumber, self.dest)
        return "{} FROM {} VIA {} TO {} CSM {} DATA {} ".format(self.msg_type, self.origin, self.dest, self.final_dest, self.checksum, self.data)

    def generate_checksum(self, origin, final_dest, sequenznumber, created_on):
        string = origin + final_dest + str(sequenznumber) + str(created_on)
        return hashlib.md5(string.encode()).hexdigest()

    @staticmethod
    def is_equal(msg1, msg2):
        if msg1.origin == msg2.origin and msg1.dest == msg2.dest and msg1.final_dest == msg2.final_dest:
            if msg1.msg_type == msg2.msg_type and msg1.data == msg2.data:
                return True
        return False

class Writer():
    def __init__(self, env, _node):
        self.channels = set()
        self.env = env
        self.node = _node
        self.csma_time = 0.08
        self.last_rreq_id = 0
        self.last_msg_time = None

    def add_channel(self, channel):
        self.channels.add(channel)

    def write_message(self):
        while True:
            if self.channels and self.node.output_queue:
                # Channels frei?
                if self.csma_check():
                    self.update_csma()

                    # destination unbekannt
                    if self.is_message_dest_unknown():
                        # Aussenden RREQ wenn noch nicht erstellt oder abgelaufen
                        if self.node.rreq_table.get(self.node.node_id, None) is None or self.node.rreq_table[self.node.node_id][self.last_rreq_id]["gueltig_bis"] < self.env.now:
                            rreq_id = self.node._get_next_sqz_number()
                            self.last_rreq_id = rreq_id
                            forward_rc = self.get_forward_rc(self)
                            gueltig_bis = self.env.now + self.node.config.get("discovery_time", 20)

                            self.node.update_rreq_table(self.node.node_id, rreq_id, forward_rc, self.node.node_id, gueltig_bis)

                            msg = Message(self.node.node_id, "-1", self.node.output_queue[0].final_dest, "RREQ", created_on=self.env.now, data={"rreq_origin": self.node.node_id, "forward_rc": forward_rc, "hop_count": 1}, sequenznumber=rreq_id)
                            logger.info("WRITER " + str(msg))
                            events = [channel.put(msg) for channel in self.channels]

                            yield self.env.all_of(events)
                        # warten auf RREP oder Ablauf RREQ Gültigkeit
                        else:
                            yield self.env.timeout(0.01)
                    # destination bekannt
                    else:
                        msg = self.node.output_queue[0]
                        timy = msg.created_on
                        # kein ack und nachricht schonmal gesendet und vor weniger als 5 sek gesendet -> warten
                        if msg.msg_type != "ACK" and self.last_msg_time is not None and Message.is_equal(self.last_msg_time[0], msg) and self.last_msg_time[1] + 5 > self.env.now:
                            yield self.env.timeout(0.01)
                        else:
                            if msg.msg_type != "ACK":
                                self.last_msg_time = (msg, self.env.now)

                            msg.created_on = self.env.now
                            # Nachricht erwartet ACK -> try merken
                            if msg.msg_type in NON_ACK_TYPES:
                                msg = self.node.output_queue.pop(0)
                                msg.created_on = self.env.now
                            else:
                                self.add_try(msg.checksum, msg)

                            # Update Forward RC vor dem Senden
                            if msg.data is not None and msg.data.get("forward_rc", None) is not None:
                                msg.data["forward_rc"] = msg.data["forward_rc"] + self.get_forward_rc(self)

                            logger.info("WRITER " + str(msg) + str(timy) + " TIME: " + str(self.env.now))
                            events = [channel.put(msg) for channel in self.channels]
                            yield self.env.all_of(events)
                # channels nicht frei
                else:
                    # zufällige zeit von csma range warten
                    yield self.env.timeout(self.csma_time)
                    self.update_csma(failed=True)
            else:
                yield self.env.timeout(0.01)

    def update_csma(self, failed=False):
        if failed:
            self.csma_time = self.csma_time * 2
            if self.csma_time > 2.55:
                self.csma_time = 2.55
        else:
            self.csma_time = max(self.csma_time - 0.64, 0.08)

    def csma_check(self):
        if not self.channels:
            raise RuntimeError("No Channels definied for writer")
        for channel in self.channels:
            if channel.peek():
                return False
        return True

    def is_message_dest_unknown(self):
        if self.node.output_queue[0].dest is None:
            return True
        return False

    def update_lqi(self):
        for channel in self.channels:
            if self.node.node_id in channel.get_endpoint_ids():
                channel.lqi = max(random.randint(channel.lqi - 20, channel.lqi + 20), 30)
                channel.lqi = min(channel.lqi, 150)

    def add_try(self, checksum, msg):
        # Nachricht bereits einmal gesendet?
        if self.node.sent_messages.get(checksum, None) is not None:
            self.node.sent_messages[checksum]["tries"] = self.node.sent_messages[checksum]["tries"] + 1
        else:
            self.node.sent_messages[checksum] = {"msg": msg, "tries": 1}

    @staticmethod
    def get_forward_rc(writer):
        lqi_sum = 0
        num_neighors = 0
        for channel in writer.channels:
            if writer.node.node_id in channel.get_endpoint_ids():
                lqi_sum = lqi_sum + channel.lqi
                num_neighors = num_neighors + 1
        writer.update_lqi()
        return int(round(200 - (lqi_sum / num_neighors)))

class Reader():
    def __init__(self, env, Node, channel):
        self.env = env
        self.node = Node
        self.channel = channel
        self.recently_recv = set()

    def read_message(self):
        while True:
            if self.channel.peek():
                if self.channel.peek().created_on < self.env.now - 0.03:
                    self.channel.get()
                elif self.channel.peek().origin != self.node.node_id and ((self.channel.peek().origin in self.node.get_neighbor_ids() and self.channel.peek().origin in self.channel.get_endpoint_ids()) or self.channel.peek().origin not in self.node.get_neighbor_ids()):
                    msg = self.channel.get()

                    yield msg
                    msg = msg.value
                    # Nachricht für diese Node bestimmt
                    if msg.dest == self.node.node_id or msg.dest == "-1":
                        if self.node.node_id in ["3"]:
                            a = True
                        # Handle MSG geACKt
                        if msg.msg_type == "ACK":
                            self.update_output_queue(msg.checksum)
                        # Nachricht annehmen wenn noch nicht vorhanden
                        elif msg.checksum not in self.recently_recv:
                            self.recently_recv.add(msg.checksum)
                            self.node.input_queue.append(msg)
                        # ACK zurück senden
                        if msg.msg_type in ACK_TYPES:
                            self.send_back_ack(msg.origin, msg.checksum)
            yield self.env.timeout(0.01)

    def msg_in_input_queue(self, msg):
        for message in self.node.input_queue:
            if Message.is_equal(message, msg):
                return True
        return False

    def send_back_ack(self, dest, checksum):
        ack_in_queue = False
        for msg in self.node.output_queue:
            if msg.msg_type == "ACK" and msg.checksum == checksum:
                ack_in_queue = True
        if not ack_in_queue:
            self.node.output_queue.insert(0, Message(self.node.node_id, dest, dest, "ACK", self.env.now, checksum=checksum))

    def update_output_queue(self, checksum):
        self.node.output_queue = [message for message in self.node.output_queue if message.checksum != checksum]


# löschen rreq_table[self.node_id] -> None wenn RREP erhalten