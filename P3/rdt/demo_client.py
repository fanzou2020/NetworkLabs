import ipaddress
import socket
from P3.rdt.rdt import ReliableDT, MyPacket

server_addr = 'localhost'
server_port = 8007
router_addr = ('localhost', 3000)

# client initiate connection
peer_ip = ipaddress.ip_address(socket.gethostbyname(server_addr))

rdt_conn = ReliableDT(router_addr)
rdt_conn.connect((peer_ip, server_port))

data = bytearray()
for i in range(0, 21):
    data.extend(bytearray("{:02d}".format(i).encode("utf-8")))

rdt_conn.sendall(bytes(data))

recv_data = rdt_conn.recvall()


