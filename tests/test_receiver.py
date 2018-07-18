import unittest
import time
from src.receiver import Peer

TEST_PORT = 8888
TEST_WINDOW_SIZE = 10

class TestPeer(unittest.TestCase):
    def test_first_segment(self):
        peer = Peer(TEST_PORT, TEST_WINDOW_SIZE)

        first_segment = {
          'seq_num': 0,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }
        peer.add_segment(first_segment)
        self.assertEqual(peer.next_ack()['seq_num'], 0)

    def test_out_of_order_segment(self):
        peer = Peer(TEST_PORT, TEST_WINDOW_SIZE)

        first_segment = {
          'seq_num': 0,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        second_segment = {
          'seq_num': 2,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }
        third_segment = {
          'seq_num': 3,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        peer.add_segment(first_segment)
        peer.add_segment(second_segment)
        peer.add_segment(third_segment)

        self.assertEqual(len(peer.window), 3)
        self.assertEqual(peer.next_ack()['seq_num'], 0)


    def test_recovery(self):
        peer = Peer(TEST_PORT, TEST_WINDOW_SIZE)

        first_segment = {
          'seq_num': 0,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        second_segment = {
          'seq_num': 2,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        third_segment = {
          'seq_num': 3,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        catchup_segment = {
          'seq_num': 1,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        peer.add_segment(first_segment)
        peer.add_segment(second_segment)
        peer.add_segment(third_segment)
        self.assertEqual(peer.next_ack()['seq_num'], 0)
        peer.add_segment(catchup_segment)
        self.assertEqual(peer.next_ack()['seq_num'], 3)

        # Clears out window upon catchup
        self.assertEqual(len(peer.window), 1)

    def test_clears_out_window(self):
        peer = Peer(TEST_PORT, 2)
        first_segment = {
          'seq_num': 0,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        second_segment = {
          'seq_num': 2,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        third_segment = {
          'seq_num': 3,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }
        catchup_segment = {
          'seq_num': 1,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        peer.add_segment(first_segment)
        peer.add_segment(second_segment)
        peer.add_segment(third_segment)
        peer.add_segment(catchup_segment)
        # Because of the window size, the segment with
        # seg_num gets thrown out. After catching up,
        # the last sequential acknowledgment is 1.

        self.assertEqual(peer.next_ack()['seq_num'], 1)

        # Clears out window upon catchup
        self.assertEqual(len(peer.window), 1)

