import random

class Telegram():
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        self.origin = originator
        self.dest = destination
        self.final_dest = final_destination
        self.sequenz_number = sequenz_number
        self.checksum = checksum
        self.data = {}

    def __repr__(self):
        return str(self.origin) + " " + str(self.dest) + " " + str(self.final_dest) + " " + str(self.sequenz_number) + " " + str(self.checksum) + " " + str(self.data)

    def process(self, Node):
        raise NotImplementedError
        # yield Node.env.timeout(10)

class Ack(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'Ack'

    def process(self, Node):
        if Node.outgoing is not None:
            if Node.outgoing[0].checksum == self.checksum:
                print("ACK!!!")
                Node.outgoing = None
class BeaconReq(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'BeaconReq'

    def process(self, Node):
        if Node.pan_id is not None:
            seq = Node.nextSequenzNumber()
            response = Node.create_telegram('BeaconRsp', Node.node_id, self.origin, self.origin, seq, Node.create_hash(seq, self.origin, self.origin))
            response.data["PAN_ID"] = Node.pan_id
            response.data["Quality"] = random.randint(0, 14)
            yield from Node.send(response)



class BeaconRsp(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'BeaconRsp'

    def process(self, Node):
        if Node.env.now <= Node.pan_start + 20 * 1000:
            if Node.pan_quality > self.data["Quality"]:
                Node.pan_id = self.data["PAN_ID"]
                Node.pan_quality = self.data["Quality"]
        seq = Node.nextSequenzNumber()
        ack = Node.create_telegram('Ack', Node.node_id, self.origin, self.origin, seq, self.checksum)
        yield from Node.send(ack)



class Join(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'Join'

    def process(self, Node):
        print('3')

class JoinMsg1(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'JoinMsg1'

    def process(self, Node):
        print('4')

class JoinMsg2(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'JoinMsg2'

    def process(self, Node):
        print('5')

class JoinMsg3(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'JoinMsg3'

    def process(self, Node):
        print('6')

class JoinAccept(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'JoinAccept'

    def process(self, Node):
        print('7')

class JoinDecline(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'JoinDecline'

    def process(self, Node):
        print('8')

class RREQ(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'RREQ'

    def process(self, Node):
        print('9')

class RREP(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'RREP'

    def process(self, Node):
        print('10')

class RERR(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'RERR'

    def process(self, Node):
        print('11')

class RouteRepair(Telegram):
    def __init__(self, originator, destination, final_destination, sequenz_number, checksum):
        super().__init__(originator, destination, final_destination, sequenz_number, checksum)
        self.tel_type = 'RouteRepair'

    def process(self, Node):
        print('12')
