Simulated network-layer routing via the distributed Bellman-Ford algorithm, 
aka [distance vector routing](http://en.wikipedia.org/wiki/Distance-vector_routing_protocol) with poison reverse.

![alt text](http://imgs.xkcd.com/comics/pillow_talk.jpg "Maybe I should've tried Wexler?")

***

### Basics

Add a node to an existing network or, if this is the first node, create a new network.
```
python bfclient.py <listening-port> <timeout> <ip-address1 port1 distance1> <ip-address2 port2 distance2> ...
```
Nodes listen on `localhost`:`listening-port`. `timeout` is how frequently a node broadcasts its distance vector to its neighbors. Edges to other nodes in the network are defined through the `ip-address port distance` argument triples.

Timeouts should be within 3x each other, e.g. 1 second and 2.9 seconds. If, say, one node's timeout is 3x greater than a neighbor's timeout, then, as defined in code, the link will be closed. Because one node still believes the edge is active, the edge will be reactivated a moment later. This will continue to happen over and over. For this reason it is important to set the timeouts of connected nodes to within 3x each other.

### Examples

- Start a 2-node network with 1 edge. Run this on separate machines or terminal windows.
  ```bash
  python bfclient.py 20000 4 localhost 20001 25.0
  ```
  ```
  python bfclient.py 20001 4 192.168.56.1 20000 25.0
  ```
  In this example, `localhost` is `192.168.56.1`, ie. if running on the same machine, for convenience you can use `localhost` instead of inputing the IP. The first command will add node listening on `localhost:20000` with a timeout of `4` and one edge. The second command adds a node to the network listening on `localhost:20001` with the same timeout and edge.

- You can also build up links gradually instead of defining the entire network from the beginning. In this example we setup a 4-node network.
  ```
  python bfclient.py 20000 4
  ```
  ```
  python bfclient.py 20001 4 localhost 20000 25
  ```
  ```
  python bfclient.py 20002 4 localhost 20000 5.6 localhost 20001 3.14
  ```
  ```
  python bfclient.py 20003 4 192.168.56.1 20001 32.0 localhost 20000 5
  ```

***

### User Input

Available commands while client is active:
- `neighbors` output a node's neighbors
- `showrt` output routing table
- `linkdown <neighbor-ip> <port>` take down an network edge
- `linkup <neighbor-ip> <port>` restore a link that was previously taken down using `linkdown`
- `linkchange <neighbor-ip> <port> <link-cost>` change an edge's cost
- `close` remove node from network. simulates a node failure.
