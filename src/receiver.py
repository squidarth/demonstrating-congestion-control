import sys
import json
import socket
import select
from typing import List, Dict, Tuple

READ_FLAGS = select.POLLIN | select.POLLPRI
WRITE_FLAGS = select.POLLOUT
ERR_FLAGS = select.POLLERR | select.POLLHUP | select.POLLNVAL
READ_ERR_FLAGS = READ_FLAGS | ERR_FLAGS
ALL_FLAGS = READ_FLAGS | WRITE_FLAGS | ERR_FLAGS

# This is set to a large enough value to
# accomodate any reasonable congestion window size.
RECEIVE_WINDOW = 100000

class Peer(object):
    def __init__(self, port: int, window_size: int) -> None:
        self.window_size = window_size
        self.port = port
        self.seq_num = -1
        self.attempts = 0
        self.previous_ack = None
        self.high_water_mark = -1
        self.window: List[Dict] = []

    def window_has_no_missing_segments(self):
        seq_nums = [seg['seq_num'] for seg in self.window]
        return all([seq_nums[i] + 1 ==  seq_nums[i+1] for i in range(len(seq_nums[:-1]))])

    def process_window(self):
        seq_nums = [seg['seq_num'] for seg in self.window]
        if self.window_has_no_missing_segments():
            self.high_water_mark = max(self.high_water_mark, self.window[-1]['seq_num'])
            self.window = self.window[-1:]
        elif len(self.window) == self.window_size:
            self.window = self.window[:-1]
            print("chopping window")

    def add_segment(self, ack: Dict):
        seq_num = ack['seq_num']

        if all([seq_num != item['seq_num'] for item in self.window]):
            self.window.append(ack)
        self.window.sort(key=lambda a: a['seq_num'])

        self.process_window()

    def next_ack(self):
        for i in range(len(self.window[:-1])):
            if self.window[i + 1]['seq_num'] > self.window[i]['seq_num'] + 1:
                return self.window[i]
        else:
            return self.window[-1]

class Receiver(object):
    def __init__(self, peers: List[Tuple[str, int]], window_size: int = RECEIVE_WINDOW) -> None:
        self.recv_window_size = window_size
        self.peers: Dict[Tuple, Peer] = {}
        for peer in peers:
            self.peers[peer] = Peer(peer[1], window_size)

        # UDP socket and poller
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.poller = select.poll()
        self.poller.register(self.sock, ALL_FLAGS)

    def cleanup(self):
        self.sock.close()

    def construct_ack(self, serialized_data: str):
        """Construct a serialized ACK that acks a serialized datagram."""
        data = json.loads(serialized_data)
        return {
          'seq_num': data['seq_num'],
          'send_ts': data['send_ts'],
          'ack_bytes': len(serialized_data)
        }

    def perform_handshakes(self):
        """Handshake with peer sender. Must be called before run()."""

        self.sock.setblocking(0)  # non-blocking UDP socket

        TIMEOUT = 1000  # ms

        retry_times = 0
        self.poller.modify(self.sock, READ_ERR_FLAGS)
        # Copy self.peers
        unconnected_peers = list(self.peers.keys())

        while len(unconnected_peers) > 0:
            for peer in unconnected_peers:
                self.sock.sendto(json.dumps({'handshake': True}).encode(), peer)

            events = self.poller.poll(TIMEOUT)

            if not events:  # timed out
                retry_times += 1
                if retry_times > 10:
                    sys.stderr.write(
                        '[receiver] Handshake failed after 10 retries\n')
                    return
                else:
                    sys.stderr.write(
                        '[receiver] Handshake timed out and retrying...\n')
                    continue

            for fd, flag in events:
                assert self.sock.fileno() == fd

                if flag & ERR_FLAGS:
                    sys.exit('Channel closed or error occurred')

                if flag & READ_FLAGS:
                    msg, addr = self.sock.recvfrom(1600)

                    if addr in unconnected_peers:
                        if json.loads(msg.decode()).get('handshake'):
                            unconnected_peers.remove(addr)

    def run(self):
        self.sock.setblocking(1)  # blocking UDP socket

        while True:
            serialized_data, addr = self.sock.recvfrom(1600)

            if addr in self.peers:
                peer = self.peers[addr]

                data = json.loads(serialized_data)
                seq_num = data['seq_num']
                if seq_num > peer.high_water_mark:
                    ack = self.construct_ack(serialized_data)
                    peer.add_segment(ack)
                    print(len(peer.window))

                    if peer.next_ack() is not None:
                        self.sock.sendto(json.dumps(peer.next_ack()).encode(), addr)
