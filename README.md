simulated network-layer routing via the distributed bellman-ford algorithm, 
aka the [distance vector routing](http://en.wikipedia.org/wiki/Distance-vector_routing_protocol) with poison reverse

http://xkcd.com/69/

***

HOWTO

setup node in network (listening on localhost) with edges to other nodes 
defined through `port`, `distance`, `ip-address`.
```bash
python bfclient.py <port1> <distance1> <ip-address1> <port2> <distance2> <ip-address2> ...
```

start 2 node network with 1 edge:
```bash
python bfclient.py 20000 4 localhost 20001 25.0
```
```
python bfclient.py 20001 4 192.168.56.1 20000 25.0
```

*note: you can use 'localhost' instead of inputing the localhost ip.*

build up links gradually:
```bash
python bfclient.py 20000 4
python bfclient.py 20001 4 localhost 20000 25
python bfclient.py 20002 4 localhost 20000 5.6 localhost 20001 3.14
python bfclient.py 20003 4 192.168.56.1 20001 32.0 localhost 20000 5
```

***

available commands in active client:
```
neighbors
showrt
linkdown <neighbor-ip> <port>
linkup <neighbor-ip> <port>
linkchange <neighbor-ip> <port> <link-cost>
close
```

*note: timeouts should be the same value. if, say, one node's timeout 
is > 3x one of its neighbor's timeouts, then the node will close the 
link down, and then reactivate the link a moment later. this will 
keep happening over and over, thus it is important to set the timeouts 
to within 3x each other.*

