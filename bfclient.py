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

def estimate_costs():
    """ recalculate inter-node path costs using bellman ford algorithm """
    for no in nodes.keys():
        cost = float("inf")
        neighbors = get_neighbors() 
        for ne in neighbors.keys():
            # dist = direct cost to neighbor + cost from node to neighbor
            dist = neighbors[ne]['direct'] + nodes[no]['costs'][ne]
            if dist < cost:
                cost = dist
        nodes[no]['cost'] = cost

def join_network():
    """ add node to the network """
    inputs = [sock, sys.stdin]
    running = True
    while running:
        in_ready, out_ready, except_ready = select(inputs,[],[]) 
        for s in in_ready:
            if s == sys.stdin:
                cmd, args = parse_cmd(sys.stdin.readline())
                run_cmd(cmd, args)
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
            print "listening on {0}:{1}".format(host, port)
    except socket.error, msg:
        print "an error occured binding the server socket. \
               error code: {0}, msg:{1}".format(msg[0], msg[1])
        sys.exit()
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

def run_cmd(cmd, args):
    """ wrapper to run a pre-defined command """
    if cmd not in cmds:
        print "command '{0}' is not a valid command".format(cmd)
        return
    # lookup and call command via commands dict
    cmds[cmd](*args)

def parse_cmd(s):
    """ extract command name and args from string (likely from stdin) """
    s = s.split()
    cmd = s[0].lower()
    args = []
    if cmd == LINKDOWN or cmd == LINKUP:
        args = s[1:]
    return cmd, args

def linkdown(host, port):
    addr = get_addr(host, port)
    # error checks
    # TODO should we even check for node not in network?
    if addr not in nodes:
        print 'node {0} is not in the network'
        return
    node = nodes[addr]
    if not node['is_neighbor']:
        print 'node {0} is not a neighbor so no can be taken down'.format(addr)
        return
    # save direct distance to neighbor, then set to infinity
    node['saved'] = node['direct']
    node['direct'] = float("inf")
    node['is_neighbor'] = False
    # recalculate cost estimates
    estimate_costs()
    # TODO need to tell former neighbor that we aren't neighbors anymore!
    if DEBUG: print_nodes()

def linkup(host, port):
    addr = get_addr(host, port)
    if addr not in nodes:
        print 'node {0} is not in the network'
        return
    node = nodes[addr]
    if 'saved' not in node:
        print 'node {0} was not a previous neighbor'
        return
    # restore saved direct distance
    node['direct'] = node['saved']
    del node['saved']
    node['is_neighbor'] = True
    # TODO notify neighboring node of the linkup
    if DEBUG: print_nodes()

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
    sys.exit()

def get_addr(host, port):
    return "{host}:{port}".format(host=host, port=port)

def get_neighbors():
    """ return dict of all neighbors (does not include self) """
    return dict([d for d in nodes.items() if d[1]['is_neighbor']])

def get_costs():
    """ return dict mapping nodes to costs """
    return dict([ (no[0], no[1]['cost']) for no in nodes.items()] )

# map command name to function
LINKDOWN = "linkdown"
LINKUP = "linkup"
SHOWRT = "showrt"
CLOSE = "close"
cmds = {
    LINKDOWN: linkdown,
    LINKUP  : linkup,
    SHOWRT  : showrt,
    CLOSE   : close,
}

def print_nodes():
    print "nodes: "
    for node in nodes.items():
        pprint(node)

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
    # add node to network
    join_network()
