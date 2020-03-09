class Telegram():
    def __init__(self, originator, destination, final_destination):
        self.origin = originator
        self.dest = destination
        self.final_dest = final_destination

    def process(self, Node):
        raise NotImplementedError
        # yield Node.env.timeout(10)

class BeaconReq(Telegram):
    def process(self, Node):
        yield Node.env.timeout(5)

class BeaconRsp(Telegram):
    def process(self, Node):
        print('2')

class Join(Telegram):
    def process(self, Node):
        print('3')

class JoinMsg1(Telegram):
    def process(self, Node):
        print('4')

class JoinMsg2(Telegram):
    def process(self, Node):
        print('5')

class JoinMsg3(Telegram):
    def process(self, Node):
        print('6')

class JoinAccept(Telegram):
    def process(self, Node):
        print('7')

class JoinDecline(Telegram):
    def process(self, Node):
        print('8')

class RREQ(Telegram):
    def process(self, Node):
        print('9')

class RREP(Telegram):
    def process(self, Node):
        print('10')

class RERR(Telegram):
    def process(self, Node):
        print('11')

class RouteRepair(Telegram):
    def process(self, Node):
        print('12')
