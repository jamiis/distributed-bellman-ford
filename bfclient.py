import sys, socket, json, time
from select import select
from collections import defaultdict
from threading import Thread, Timer
from datetime import datetime
from copy import deepcopy

SIZE = 4096
LINKDOWN = "linkdown"
LINKUP = "linkup"
SHOWRT = "showrt"
CLOSE = "close"
COSTSUPDATE= "costs-update"
SHOWNEIGHBORS = "neighbors"

class RepeatTimer(Thread):
    """ thread that will call a function every interval seconds """
    def __init__(self, interval, target):
        Thread.__init__(self)
        self.target = target
        self.interval = interval
        self.daemon = True
        self.stopped = False
    def run(self):
        while not self.stopped:
            time.sleep(self.interval)
            self.target()

class ResettableTimer():
    def __init__(self, interval, func, args=None):
        if args != None: assert type(args) is list
        self.interval = interval
        self.func = func
        self.args = args
        self.countdown = self.create_timer()
    def start(self):
        self.countdown.start()
    def reset(self):
        self.countdown.cancel()
        self.countdown = self.create_timer()
        self.start()
    def create_timer(self):
        t = Timer(self.interval, self.func, self.args)
        t.daemon = True
        return t
    def cancel(self):
        self.countdown.cancel()

def estimate_costs():
    """ recalculate inter-node path costs using bellman ford algorithm """
    for destination_addr, destination in nodes.iteritems():
        # we don't need to update the distance to ourselves
        if destination_addr != me:
            # iterate through neighbors and find cheapest route
            cost = float("inf")
            nexthop = ''
            for neighbor_addr, neighbor in get_neighbors().iteritems():
                # distance = direct cost to neighbor + cost from neighbor to destination
                if destination_addr in neighbor['costs']:
                    dist = neighbor['direct'] + neighbor['costs'][destination_addr]
                    if dist < cost:
                        cost = dist
                        nexthop = neighbor_addr
            # set new estimated cost to node in the network
            destination['cost'] = cost
            destination['route'] = nexthop

def update_costs(host, port, **kwargs):
    """ update neighbor's costs """
    costs = kwargs['costs']
    addr = addr2key(host, port)
    # if a node listed in costs is not in our list of nodes...
    for node in costs:
        if node not in nodes:
            # ... create a new node
            nodes[node] = default_node()
    # if node not a neighbor ...
    if not nodes[addr]['is_neighbor']: 
        # ... make it your neighbor!
        print 'making new neighbor {0}\n'.format(addr)
        del nodes[addr]
        nodes[addr] = create_node(
                cost        = nodes[addr]['cost'], 
                is_neighbor = True,
                direct      = kwargs['neighbor']['direct'],
                costs       = costs,
                addr        = addr)
    else:
        # otherwise just update node costs
        node = nodes[addr]
        node['costs'] = costs
        # restart silence monitor
        node['silence_monitor'].reset()
    # run bellman ford
    estimate_costs()

def broadcast_costs():
    """ send estimated path costs to each neighbor """
    costs = { addr: node['cost'] for addr, node in nodes.iteritems() }
    data = { 'type': COSTSUPDATE }
    for neighbor_addr, neighbor in get_neighbors().iteritems():
        # poison reverse!!! muhuhhahaha
        poisoned_costs = deepcopy(costs)
        for dest_addr, cost in costs.iteritems():
            # only do poisoned reverse if destination not me or neighbor
            if dest_addr not in [me, neighbor_addr]:
                # if we route through neighbor to get to destination ...
                if nodes[dest_addr]['route'] == neighbor_addr:
                    # ... tell neighbor distance to destination is infinty!
                    poisoned_costs[dest_addr] = float("inf")
        data['payload'] = { 'costs': poisoned_costs }
        data['payload']['neighbor'] = { 'direct': neighbor['direct'] }
        # send (potentially 'poisoned') costs to neighbor
        sock.sendto(json.dumps(data), key2addr(neighbor_addr))

def setup_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((localhost, port))
        print "listening on {0}:{1}\n".format(localhost, port)
    except socket.error, msg:
        print "an error occured binding the server socket. \
               error code: {0}, msg:{1}\n".format(msg[0], msg[1])
        sys.exit(1)
    return sock

def parse_argv():
    """ pythonicize bflient command args """
    s = sys.argv[1:]
    port = int(s.pop(0))
    timeout = float(s.pop(0))
    # iterate through s extracting neighbors and costs along the way
    neighbors = []
    costs = []
    while len(s):
        host = get_host(s[0].lower())
        neighbors.append(addr2key(host=host, port=s[1]))
        costs.append(float(s[2]))
        del s[0:3]
    return port, timeout, neighbors, costs

def default_node():
    return { 'cost': float("inf"), 'is_neighbor': False, 'route': '' }

def create_node(cost, is_neighbor, direct=None, costs=None, addr=None):
    """ centralizes the pattern for creating new nodes """
    node = default_node()
    node['cost'] = cost
    node['is_neighbor'] = is_neighbor
    node['direct'] = direct if direct != None else float("inf")
    node['costs']  = costs  if costs  != None else defaultdict(lambda: float("inf"))
    if is_neighbor:
        node['route'] = addr
        # ensure neighbor is transmitting cost updates using a resettable timer
        monitor = ResettableTimer(
            interval = 3*timeout, 
            func = linkdown,
            args = list(key2addr(addr)))
        monitor.start()
        node['silence_monitor'] = monitor
    return node

def linkdown(host, port, **kwargs):
    addr = addr2key(get_host(host), port)
    if not in_network(neighbor): return
    node = nodes[addr]
    if not node['is_neighbor']: 
        print "node {0} is not a neighbor so it can't be taken down\n".format(addr)
        return
    # save direct distance to neighbor, then set to infinity
    node['saved'] = node['direct']
    node['direct'] = float("inf")
    node['is_neighbor'] = False
    node['silence_monitor'].cancel()
    # run bellman-ford
    estimate_costs()

def linkup(host, port):
    addr = addr2key(get_host(host), port)
    if not in_network(addr): return
    node = nodes[addr]
    if 'saved' not in node:
        print "{0} wasn't a previous neighbor\n".format(addr)
        return
    # restore saved direct distance
    node['direct'] = node['saved']
    del node['saved']
    node['is_neighbor'] = True
    # run bellman-ford
    estimate_costs()

def formatted_now():
    return datetime.now().strftime("%b-%d-%Y, %I:%M %p, %S seconds")

def show_neighbors():
    """ show active neighbors """
    print formatted_now()
    print "Neighbors: "
    for addr, neighbor in get_neighbors().iteritems():
        print "{addr}, cost:{cost}, direct:{direct}".format(
                addr   = addr, 
                cost   = neighbor['cost'],
                direct = neighbor['direct'])
    print # extra line

def showrt():
    """ display routing info: cost to destination; route to take """
    print formatted_now()
    print "Distance vector list is:"
    for addr, node in nodes.iteritems():
        if addr != me:
            print ("Destination = {destination}, "
                   "Cost = {cost}, "
                   "Link = ({nexthop})").format(
                        destination = addr,
                        cost        = node['cost'],
                        nexthop     = node['route'])
    print # extra line

def close():
    """ notify all neighbors that she's a comin daaaahwn! then close process"""
    data = {'type': LINKDOWN, 'payload': {}}
    for neighbor_addr, neighbor in get_neighbors().iteritems():
        sock.sendto(json.dumps(data), key2addr(neighbor_addr))
    sys.exit()

def in_network(addr):
    if addr not in nodes:
        print 'node {0} is not in the network\n'.format(addr)
        return False
    return True

def key2addr(key):
    host, port = key.split(':')
    return host, int(port)

def addr2key(host, port):
    return "{host}:{port}".format(host=host, port=port)

def get_host(host):
    """ translate host into ip address """
    return localhost if host == 'localhost' else host

def get_neighbors():
    """ return dict of all neighbors (does not include self) """
    return dict([d for d in nodes.iteritems() if d[1]['is_neighbor']])

def print_nodes():
    print "nodes: "
    for addr, node in nodes.iteritems():
        print addr
        for k,v in node.iteritems():
            print '---- ', k, '\t\t', v
    print # extra line

# map command/update names to functions
user_cmds = {
    LINKDOWN: linkdown,
    LINKUP  : linkup,
    SHOWRT  : showrt,
    CLOSE   : close,
    SHOWNEIGHBORS : show_neighbors,
}
updates = {
    LINKDOWN   : linkdown,
    LINKUP     : linkup,
    COSTSUPDATE: update_costs,
}

if __name__ == '__main__':
    localhost = socket.gethostbyname(socket.gethostname())
    port, timeout, neighbors, costs = parse_argv()
    # initialize dict of nodes to all neighbors
    nodes = defaultdict(lambda: default_node())
    for neighbor, cost in zip(neighbors, costs):
        nodes[neighbor] = create_node(
                cost=cost, direct=cost, is_neighbor=True, addr=neighbor)
    # begin accepting UDP packets
    sock = setup_server()
    # set cost to myself to 0
    me = addr2key(*sock.getsockname())
    nodes[me] = create_node(cost=0.0, direct=0.0, is_neighbor=False, addr=me)
    # broadcast costs every timeout seconds
    broadcast_costs()
    RepeatTimer(timeout, broadcast_costs).start()

    # listen for updates from other nodes and user input
    inputs = [sock, sys.stdin]
    running = True
    while running:
        in_ready, out_ready, except_ready = select(inputs,[],[]) 
        for s in in_ready:
            if s == sys.stdin:
                # input from user
                user_input = sys.stdin.readline().split()
                if not len(user_input): continue
                cmd = user_input[0].lower()
                if cmd not in user_cmds:
                    print "'{0}' is not a valid command\n".format(cmd)
                    continue
                args = [] 
                if cmd in [LINKDOWN, LINKUP]:
                    args = user_input[1:]
                    if len(args) != 2:
                        print "'{0}' cmd requires host and port args\n".format(cmd)
                        continue
                    # notify neighbor that link is coming down or being restored
                    data = json.dumps({'type': cmd, 'payload': {}})
                    addr = (get_host(args[0]), int(args[1]))
                    sock.sendto(data, addr)
                user_cmds[cmd](*args)
            else: 
                # update from another node
                data, sender = s.recvfrom(SIZE)
                loaded = json.loads(data)
                update = loaded['type']
                payload = loaded['payload']
                if update not in updates:
                    print "'{0}' is not in the update protocol\n".format(update)
                    continue
                updates[update](*sender, **payload)
    sock.close()
