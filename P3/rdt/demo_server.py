import ipaddress
import socket
from P3.rdt.rdt import ReliableDT, MyPacket


def handle_client(rdt):
    data = rdt.recvall()
    print(b"Received data is : " + data)
    rdt.sendall("Data received successfully".encode('utf-8'))



server_addr = 'localhost'
server_port = 8007
router_addr = ('localhost', 3000)

conn = ReliableDT(router_addr)

try:
    conn.bind((server_addr, server_port))
    print("Server is listening at port 8007")
    while True:
        rdt = conn.accept()
        if rdt:
            handle_client(rdt)

finally:
    conn.conn.close()


