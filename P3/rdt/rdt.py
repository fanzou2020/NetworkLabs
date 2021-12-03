import socket
import ipaddress
import random
import threading
import time
from datetime import datetime

from P3.example.python.packet import Packet


class PacketType:
    ACK = 0
    SYN = 1
    SYN_ACK = 2


class ConnectionState:
    ESTABLISHED = 1
    CLOSED = 0


class MyPacket:
    MIN_LEN = 15
    MAX_LEN = 1024

    def __init__(self, packet_type, seq_num, peer_ip_addr, peer_port, ack_num, payload: bytes):
        """
        Wrap the Packet class, add ack_num into the packet
        :param packet_type:
        :param seq_num:
        :param peer_ip_addr:
        :param peer_port:
        :param ack_num:
        :param payload: should be bytes
        """
        self.packet_type = int(packet_type)
        self.seq_num = int(seq_num)
        self.peer_ip_addr = peer_ip_addr
        self.peer_port = int(peer_port)
        self.ack_num = int(ack_num)
        self.payload = payload

        payload_to_router = self.ack_num.to_bytes(4, byteorder='big') + payload
        self.packet_to_router = Packet(packet_type=self.packet_type,
                                       seq_num=self.seq_num,
                                       peer_ip_addr=self.peer_ip_addr,
                                       peer_port=self.peer_port,
                                       payload=payload_to_router)

    def to_bytes(self):
        """
        to_raw returns a bytearray representation of the packet in big-endian order.
        :return:
        """
        return self.packet_to_router.to_bytes()

    def __repr__(self, *args, **kwargs):
        return "#%d, #%d, peer=%s:%s, size=%d" % \
               (self.seq_num, self.ack_num, self.peer_ip_addr, self.peer_port, len(self.payload))

    @staticmethod
    def from_bytes(raw):
        """
        From raw bytes creates a MyPacket instance
        :param raw:
        :return:
        """
        if len(raw) < MyPacket.MIN_LEN:
            raise ValueError("Packet is too short: {} bytes".format(len(raw)))
        if len(raw) > MyPacket.MAX_LEN:
            raise ValueError("Packet is exceeded max length: {} bytes".format(len(raw)))

        curr = [0, 0]

        def nbytes(n):
            curr[0], curr[1] = curr[1], curr[1] + n
            return raw[curr[0]: curr[1]]

        packet_type = int.from_bytes(nbytes(1), byteorder='big')
        seq_num = int.from_bytes(nbytes(4), byteorder='big')
        peer_addr = ipaddress.ip_address(nbytes(4))
        peer_port = int.from_bytes(nbytes(2), byteorder='big')
        ack_num = int.from_bytes(nbytes(4), byteorder='big')
        payload = raw[curr[1]:]

        return MyPacket(packet_type=packet_type,
                        seq_num=seq_num,
                        peer_ip_addr=peer_addr,
                        peer_port=peer_port,
                        ack_num=ack_num,
                        payload=payload)


class ReliableDT:
    def __init__(self, router_addr):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.router_addr = router_addr

        self.max_chunk_len = 2
        self.is_sending = False

        # for sender side
        self.peer_addr_of_sender = None

        self.timeout = 2

        self.wsz = 8             # sliding window size
        self.send_buffer = None  # sender buffer[wsz], allocate in runtime
        self.timers = None       # timers[wsz], timer for each packet in sliding window
        self.acks = None         # acks[wsz], received acks in sliding window
        self.send_base = None

        self._ack_number = None  # used to store last ack number sent by sender in 3-way handshake
        self._seq_number = None  # used to store last seq number sent by sender in 3-way handshake

        # for receiver side
        self.peer_addr_of_receiver = None
        self.recv_buffer = None
        self.recv_base = None
        self.bytearray_to_be_delivered = None  # data can already be delivered
        self.recv_resources_allocated = False


    def bind(self, addr):
        self.conn.bind(addr)

    def connect(self, addr):
        """
        Sender side three-way handshake connection to addr
        :param addr: destination address
        :return:
        """
        # send SYN message with seq=client_isn
        # client_isn = random.randint(0, 999)
        client_isn = 99
        syn_packet = MyPacket(packet_type=PacketType.SYN,
                              seq_num=client_isn,
                              peer_ip_addr=addr[0],
                              peer_port=addr[1],
                              ack_num=0,
                              payload="".encode("utf-8"))

        while True:
            try:
                self.conn.sendto(syn_packet.to_bytes(), self.router_addr)

                self.conn.settimeout(self.timeout)

                # after sending SYN, waiting fro SYN_ACK response
                print("In connect(), waiting for a SYN_ACK response")
                response, sender = self.conn.recvfrom(1024)
                response_packet = MyPacket.from_bytes(response)
                if response_packet.packet_type != PacketType.SYN_ACK:
                    continue
                if response_packet.ack_num != client_isn + 1:
                    continue

                server_isn = response_packet.seq_num
                break

            except socket.timeout:
                # if timeout occurs, resend SYN
                continue

        # received response correctly, send ACK
        ack_packet = MyPacket(packet_type=PacketType.ACK,
                              seq_num=client_isn + 1,
                              peer_ip_addr=addr[0],
                              peer_port=addr[1],
                              ack_num=server_isn + 1,
                              payload="".encode("utf-8"))

        self.conn.sendto(ack_packet.to_bytes(), self.router_addr)
        # self._ack_number = server_isn + 1
        # self._seq_number = client_isn + 1

        self.peer_addr_of_sender = addr
        print("Sender state -> ESTABLISHED")
        self.send_base = client_isn + 1
        self.recv_base = server_isn + 1

        # todo: if received duplicate SYN_ACK, meaning last ACK was lost, resend the last ACK
        # todo: corrected, no need to resend, the following data packet will have ACK anyway

    def accept(self):
        data, sender = None, None
        while True:
            try:
                data, sender = self.conn.recvfrom(1024)
                if sender or data:
                    break
            except socket.timeout:
                continue

        p = MyPacket.from_bytes(data)

        # received SYN, send SYN_ACK back
        if p.packet_type == PacketType.SYN:
            server_isn = 999

            ack_id = p.seq_num + 1
            self.recv_base = ack_id
            self.send_base = server_isn + 1

            addr = (p.peer_ip_addr, p.peer_port)
            self.peer_addr_of_sender = addr

            syn_ack_packet = MyPacket(packet_type=PacketType.SYN_ACK,
                                      seq_num=server_isn,
                                      peer_ip_addr=addr[0],
                                      peer_port=addr[1],
                                      ack_num=ack_id,
                                      payload="".encode('utf-8'))

            while True:
                try:
                    self.conn.sendto(syn_ack_packet.to_bytes(), self.router_addr)

                    self.conn.settimeout(self.timeout)

                    # after sending SYN_ACK, waiting for ACK response
                    print("In accept(), waiting for ACK response from sender")
                    response, sender = self.conn.recvfrom(1024)
                    response_packet = MyPacket.from_bytes(response)
                    if response_packet.packet_type != PacketType.ACK:
                        continue
                    if response_packet.ack_num != server_isn + 1:
                        continue
                    print("Server state -> ESTABLISHED")

                    # allocate resources for receiver
                    self.allocate_receiver_resources(response_packet)
                    return self

                except socket.timeout:
                    continue


    def sendall(self, data:bytes):
        # split data into chunks
        data_len, chunk_size = len(data), self.max_chunk_len
        chunks = [data[i:i+chunk_size] for i in range(0, data_len, chunk_size)]
        print(chunks)

        self.is_sending = True

        self.send_buffer = [None] * self.wsz
        self.timers = [None] * self.wsz
        self.acks = [False] * self.wsz

        initial_seq_num = self.send_base
        print("send_base is : " + str(self.send_base))
        end_seq_num = self.send_base + len(chunks)
        print("end of send base is : " + str(end_seq_num))

        # create a thread to monitor timers
        threading.Thread(target=self.timer_monitor, args=(end_seq_num, )).start()

        # create a thread to monitor received acks
        threading.Thread(target=self.ack_monitor_sender, args=(end_seq_num, )).start()

        # send each chunk
        for i, chunk in enumerate(chunks):
            while self.is_full(self.send_buffer):
                pass

            seq_num = initial_seq_num + i
            packet = MyPacket(packet_type=PacketType.ACK,
                              seq_num=seq_num,
                              peer_ip_addr=self.peer_addr_of_sender[0],
                              peer_port=self.peer_addr_of_sender[1],
                              ack_num=self.recv_base,
                              payload=chunk)

            buffer_index = seq_num - self.send_base
            self.send_buffer[buffer_index] = packet
            self.timers[buffer_index] = datetime.now()
            self.conn.sendto(packet.to_bytes(), self.router_addr)
            print(packet)



    # return all data
    def recvall(self):
        while self.is_sending:
            pass

        # if timeout_count > 5, meaning that sender finished sending
        max_timeout_count = 3
        timeout_count = 0
        while True:
            data, sender = None, None
            try:
                data, sender = self.conn.recvfrom(1024)
            except socket.timeout:
                timeout_count += 1
            if data is None or sender is None:
                if not self.recv_resources_allocated:
                    print(self.recv_resources_allocated)
                    continue
                elif timeout_count < max_timeout_count:
                    print(timeout_count)
                    continue
                else:
                    break

            timeout_count = 0
            packet = MyPacket.from_bytes(data)

            # if allocate_receiver_resources not have been called
            if not self.recv_resources_allocated:
                self.allocate_receiver_resources(packet)

            print(packet.payload)
            self.receiver_actions(packet)
            print(self.bytearray_to_be_delivered)
            # if len(packet.payload) < self.max_chunk_len:
            #     break

        print("recvall done")
        data = bytes(self.bytearray_to_be_delivered)
        self.bytearray_to_be_delivered = None
        self.recv_resources_allocated = False
        return data


    def allocate_receiver_resources(self, first_packet):
        print("recv base is: " + str(self.recv_base))

        self.peer_addr_of_receiver = (first_packet.peer_ip_addr, first_packet.peer_port)
        self.recv_buffer = [None] * self.wsz
        self.bytearray_to_be_delivered = bytearray()
        self.recv_resources_allocated = True

        # if first_packet contains payload, must response to sender
        if first_packet.payload:
            print("First packet contains payload is: ")
            print(first_packet.payload)
            self.receiver_actions(first_packet)
        return


    def receiver_actions(self, packet_recved:MyPacket):
        seq_num = packet_recved.seq_num
        if self.recv_base <= seq_num <= self.recv_base + self.wsz - 1:
            # return a selective ACK packet
            ack_packet = MyPacket(packet_type=PacketType.ACK,
                                  seq_num=seq_num,
                                  peer_ip_addr=self.peer_addr_of_receiver[0],
                                  peer_port=self.peer_addr_of_receiver[1],
                                  ack_num=seq_num,
                                  payload="".encode('utf-8'))
            self.conn.sendto(ack_packet.to_bytes(), self.router_addr)

            # if not previously received, buffer it
            buffer_index = seq_num - self.recv_base
            if self.recv_buffer[buffer_index] is None:
                self.recv_buffer[buffer_index] = packet_recved.payload

            # slide window, and delivered buffered consecutive blocks
            if seq_num == self.recv_base:
                num_slide = self.num_consecutive_buffers(self.recv_buffer)
                print("Slide recv buffer window by " + str(num_slide))

                # deliver to upper layer
                for i in range(num_slide):
                    self.bytearray_to_be_delivered.extend(bytearray(self.recv_buffer[i]))

                # slide window
                for j in range(num_slide):
                    self.recv_buffer.pop(0)
                    self.recv_buffer.append(None)
                    self.recv_base += 1

        elif self.recv_base-self.wsz <= seq_num <= self.recv_base-1:
            # return a selective ACK packet
            ack_packet = MyPacket(packet_type=PacketType.ACK,
                                  seq_num=seq_num,
                                  peer_ip_addr=self.peer_addr_of_receiver[0],
                                  peer_port=self.peer_addr_of_receiver[1],
                                  ack_num=seq_num,
                                  payload="".encode('utf-8'))
            self.conn.sendto(ack_packet.to_bytes(), self.router_addr)


    def timer_monitor(self, end_seq_num):
        while self.send_base < end_seq_num:
            for i in range(self.wsz):
                timer = self.timers[i]
                if timer and (datetime.now() - timer).total_seconds() > self.timeout:
                    # trigger timeout event
                    seq_num = i + self.send_base
                    packet = self.send_buffer[i]
                    if packet and seq_num != packet.seq_num:
                        print("Error, seq_num != packet.seq_num when timeout occurs")
                    else:
                        print("Resend packet # " + str(seq_num))
                        try:
                            self.conn.sendto(packet.to_bytes(), self.router_addr)  # resend packet
                        except Exception:
                            pass
                        self.timers[i] = datetime.now()   # reset timer


    def ack_monitor_sender(self, end_seq_num):
        data, sender = None, None
        while self.send_base < end_seq_num:
            try:
                data, sender = self.conn.recvfrom(1024)
            except socket.timeout:
                pass
            if data is None or sender is None:
                continue

            # received ack, trigger ack_received event
            packet = MyPacket.from_bytes(data)
            ack_num = packet.ack_num

            if self.send_base <= ack_num < self.send_base + self.wsz:
                acks_index = ack_num - self.send_base
                self.acks[acks_index] = True
                self.timers[acks_index] = None

                # slide window to the unacknowledged packet with smallest seq num
                if ack_num == self.send_base:
                    num_slided = self.num_consecutive_acks(self.acks)
                    print("Slide send buffer window by " + str(num_slided))

                    # slide window
                    for k in range(num_slided):
                        self.send_buffer.pop(0)
                        self.timers.pop(0)
                        self.acks.pop(0)
                        self.send_buffer.append(None)
                        self.timers.append(None)
                        self.acks.append(False)
                        self.send_base += 1
                    print("After sliding window, sendbase = " + str(self.send_base))
        time.sleep(self.timeout)
        self.is_sending = False
        print("finish sending")


    def is_full(self, array):
        return array.count(None) == 0


    def num_consecutive_buffers(self, array):
        n = self.wsz
        for i in range(self.wsz):
            if array[i] is None:
                n = i
                break
        return n

    def num_consecutive_acks(self, array):
        n = self.wsz
        for i in range(self.wsz):
            if array[i] is False:
                n = i
                break
        return n




