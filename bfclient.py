import sys, socket, select

DEBUG = True
if DEBUG:
    from pprint import pprint

SIZE = 1024

def join_network():
    """ add node to the distributed bellman ford algorithm network """
    inputs = [sock, sys.stdin]
    running = True
    while running:
        in_ready, out_ready, except_ready = select.select(inputs,[],[]) 
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
        # neighbors[address] = distance
        neighbors[args[0]+":"+args[1]] = float(args[2])
        del args[0:3]
    if DEBUG:
        print "neighbors: "
        pprint(neighbors)
    return port, timeout, neighbors

if __name__ == '__main__':
    port, timeout, neighbors = parse_args(sys.argv[1:])
    sock = setup_server()
    join_network()
