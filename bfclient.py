import sys, socket
from select import select
from collections import defaultdict

DEBUG = True
if DEBUG:
    from pprint import pprint

SIZE = 1024

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


def update_neighbor(addr, costs):
    """ update costs given costs received from a neighboring node """
    # will help with debugging bc this should never happen
    assert nodes[addr]['is_neighbor']
    # first, save neighbor's new dist vector
    nodes[addr]['costs'] = costs
    # update every node's cost
    for no in nodes.keys():
        mini = float("inf")
        neighbors = get_neighbors() 
        for ne in neighbors.keys():
            # dist = direct cost to neighbor + cost from node to neighbor
            dist = neighbors[ne]['direct'] + nodes[no]['costs'][ne]
            if dist < mini:
                mini = dist
        nodes[no]['cost'] = dist

def join_network():
    """ add node to the distributed bellman ford algorithm network """
    inputs = [sock, sys.stdin]
    running = True
    while running:
        in_ready, out_ready, except_ready = select(inputs,[],[]) 
        for s in in_ready:
            if s == sys.stdin:
                print 'stdin: {0}'.format(sys.stdin.readline())
                # TODO run command given user input
            else:
                print 's == sock'
                data, addr = s.recvfrom(SIZE)
                # TODO update routing tables
    sock.close()

def setup_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        host = socket.gethostbyname(socket.gethostname())
        sock.bind((host, port))
        if DEBUG:
            print "listening on {0}:{1}".format(host,port)
    except socket.error, msg:
        print "an error occured binding the server socket. \
               error code: {0}, msg:{1}".format(msg[0], msg[1])
        sys.exit()
    return sock

def parse_args(args):
    port = int(args.pop(0))
    timeout = float(args.pop(0))
    neighbors = {}
    while len(args):
        address = get_addr(ip=args[0], port=args[1])
        distance = float(args[2])
        neighbors[address] = node(cost=distance, direct=distance, is_neighbor=True)
        del args[0:3]
    return port, timeout, neighbors

def node(cost, direct, is_neighbor=False, costs=None):
    """ centralizes the pattern for creating new nodes """
    if costs == None:
        costs = defaultdict(lambda c: float("inf"))
    return {
        'cost'       : cost,
        'direct'     : direct,
        'is_neighbor': is_neighbor,
        'costs'      : defaultdict(lambda c: float("inf")),
    }

def get_addr(ip, port):
    return "{ip}:{port}".format(ip=ip, port=port)

def get_neighbors():
    """ return dict of all neighbors (does not include self) """
    return dict([d for d in nodes.items() if d[1]['is_neighbor']])

def get_costs():
    """ return dict mapping nodes to costs; returns own distance vector """
    return dict([ (no[0], no[1]['cost']) for no in nodes.items()] )

if __name__ == '__main__':
    port, timeout, nodes = parse_args(sys.argv[1:])
    sock = setup_server()
    # set distance to self to 0
    me = get_addr(*sock.getsockname())
    nodes[me] = { 'cost': 0.0, 'direct': 0.0, 'is_neighbor': False }
    if DEBUG:
        print "nodes: "
        pprint(nodes)
    # add node to network
    join_network()
