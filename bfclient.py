import sys, socket, json, time
from select import select
from collections import defaultdict
from threading import Thread

DEBUG = True
if DEBUG:
    from pprint import pprint

SIZE = 1024
LINKDOWN = "linkdown"
LINKUP = "linkup"
SHOWRT = "showrt"
CLOSE = "close"
COSTSUPDATE= "costs-update"

class RepeatTimer(Thread):
    def __init__(self, interval, target):
        Thread.__init__(self)
        self.target = target
        self.interval = interval
        self.daemon = True
        self.stopped = False
    def run(self):
        while not self.stopped:
            self.target()
            time.sleep(self.interval)

nodes_example = {
    '127.0.0.0': {
        'cost': 0.0,
        'is_neighbor': False, # TODO not sure
    },
    '127.0.0.1': {
        'cost': 10.0,
        'is_neighbor': True,
        # vals below are present iff is_neighbor
        'direct' : 10.0,
        'costs': { 
            '127.0.0.0': 10.0,
            '127.0.0.2': 5.0,
            '127.0.0.3': 15.0,
        }
    },
    '127.0.0.2': {
        'cost': 15.0,
        'is_neighbor': True,
        'direct' : 100.0,
        'costs': { 
            '127.0.0.0': 16.0,
            '127.0.0.1': 5.0,
            '127.0.0.3': 1.0,
        }
    },
    '127.0.0.3': {
        'cost': 16.0, # 0 -> 1 -> 2 -> 3
        'is_neighbor': False,
        'direct': float("inf") # ? 
    },
}

def estimate_costs():
    """ recalculate inter-node path costs using bellman ford algorithm """
    for destination_addr, destination in nodes.iteritems():
        # we don't need to update the distance to ourselves
        if destination_addr != me:
            # iterate through neighbors and find cheapest route
            cost = float("inf")
            for neighbor_addr, neighbor in get_neighbors().iteritems():
                # distance = direct cost to neighbor + cost from destination to neighbor
                dist = neighbor['direct'] + destination['costs'][neighbor_addr]
                if dist < cost:
                    cost = dist
            # set new estimated cost to node in the network
            destination['cost'] = cost
    if DEBUG: print_nodes()

update_example = {
    'type': COSTSUPDATE,
    'payload': {
        'costs': {
            '127.0.0.0': 16.0,
            '127.0.0.1': 5.0,
            '127.0.0.3': 1.0,
        }
    }
}
update_example_two = {
    'type': LINKDOWN,
    'payload': {},
}

def update_costs(host, port, costs):
    """ update neighbor's costs """
    addr = get_addr(host, port)
    if not in_network(addr): return
    node = nodes[addr]
    if not node['is_neighbor']: 
        print 'node {0} is not a neighbor so cannot update costs\n'.format(addr)
        return
    node['costs'] = costs
    estimate_costs()

def broadcast_costs():
    """ send estimated path costs to neighbors """
    broadcast({
        'type': COSTSUPDATE,
        'payload': { 'costs': get_costs() }
    })

def broadcast(data):
    """ send json data to neighbors """
    data = json.dumps(data)
    for addr in get_neighbors().keys():
        host, port = addr.split(':')
        sock.sendto(data, (host, int(port)))

def setup_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        host = socket.gethostbyname(socket.gethostname())
        sock.bind((host, port))
        if DEBUG:
            print "listening on {0}:{1}\n".format(host, port)
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
        neighbors.append(get_addr(host=s[0], port=s[1]))
        costs.append(float(s[2]))
        del s[0:3]
    return port, timeout, neighbors, costs

def create_node(cost, is_neighbor=False, direct=None, costs=None):
    """ centralizes the pattern for creating new nodes """
    node = { 'cost': cost, 'is_neighbor': is_neighbor }
    direct = direct if direct != None else float("inf")
    costs  = costs  if costs  != None else defaultdict(lambda: float("inf"))
    node['direct'] = direct
    node['costs'] = costs
    return node

def linkdown(host, port):
    addr = get_addr(host, port)
    if not in_network(neighbor): return
    node = nodes[addr]
    if not node['is_neighbor']: 
        print 'node {0} is not a neighbor so no can be taken down\n'.format(addr)
        return
    # save direct distance to neighbor, then set to infinity
    node['saved'] = node['direct']
    node['direct'] = float("inf")
    node['is_neighbor'] = False
    # run bellman-ford
    estimate_costs()

def linkup(host, port):
    addr = get_addr(host, port)
    if not in_network(addr): return
    node = nodes[addr]
    if 'saved' not in node:
        print 'node {0} was not a previous neighbor\n'
        return
    # restore saved direct distance
    node['direct'] = node['saved']
    del node['saved']
    node['is_neighbor'] = True
    # run bellman-ford
    estimate_costs()

def showrt():
    '''
    TODO need to create dict/list as below.
    have yet to implement storing next-hop router!
    { 'addr' : {
        'cost': 20.0, # total estimated cost
        'route': '111.22.333.1',
    }, ...  }
    '''
    pass

def close():
    # notify neighbors that she's comin daaaahwn!
    broadcast({'type': LINKDOWN, 'payload': {}})
    sys.exit()

def in_network(addr):
    if addr not in nodes:
        print 'node {0} is not in the network\n'.format(addr)
        return False
    return True

def get_addr(host, port):
    return "{host}:{port}".format(host=host, port=port)

def get_neighbors():
    """ return dict of all neighbors (does not include self) """
    return dict([d for d in nodes.items() if d[1]['is_neighbor']])

def get_costs():
    """ return dict mapping nodes to costs """
    return dict([ (no[0], no[1]['cost']) for no in nodes.items()] )

def print_nodes():
    print "nodes: "
    for addr, node in nodes.iteritems():
        print addr
        for k,v in node.iteritems():
            print '---- ', k, '\t\t', v
    print

# map command/update names to functions
cmds = {
    LINKDOWN: linkdown,
    LINKUP  : linkup,
    SHOWRT  : showrt,
    CLOSE   : close,
}
updates = {
    LINKDOWN   : linkdown,
    LINKUP     : linkup,
    COSTSUPDATE: update_costs,
}

if __name__ == '__main__':
    port, timeout, neighbors, costs = parse_argv()
    # initialize dict of nodes to all neighbors
    nodes = defaultdict(lambda: { 'cost': float("inf"), 'is_neighbor': False })
    for neighbor, cost in zip(neighbors, costs):
        nodes[neighbor] = create_node(cost=cost, direct=cost, is_neighbor=True)
    # begin accepting UDP packets
    sock = setup_server()
    # set cost to myself to 0
    me = get_addr(*sock.getsockname())
    nodes[me] = create_node(cost=0.0, direct=0.0, is_neighbor=False)

    if DEBUG: print_nodes()

    # broadcast costs every timeout seconds
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
                if cmd not in cmds:
                    print "'{0}' is not a valid command".format(cmd)
                    continue
                args = [] 
                if cmd in [LINKDOWN, LINKUP]:
                    args = user_input[1:]
                    # notify neighbor that link is coming down or being restored
                    data = json.dumps({'type': cmd, 'payload': {}})
                    addr = (args[0], int(args[1]))
                    sock.sendto(data, addr)
                cmds[cmd](*args)
            else: 
                # update from another node
                data, sender = s.recvfrom(SIZE)
                loaded = json.loads(data)
                update = loaded['type']
                payload = loaded['payload']
                if update not in updates:
                    print "update '{0}' not defined".format(update)
                    continue
                updates[update](*sender, **payload)
    sock.close()

