import json
import time
import unittest
from src.strategies import TahoeStrategy, FixedWindowStrategy


class TestTahoeStrategy(unittest.TestCase):
    def test_segments_received_in_order(self):
        strategy = TahoeStrategy(3, 1)
        first_segment = strategy.next_packet_to_send()
        self.assertEqual(json.loads(first_segment)['seq_num'], 0)
        self.assertEqual(strategy.unacknowledged_packets[0]['seq_num'], 0)
        # Window starts at 1, so window is full at this point
        self.assertIsNone(strategy.next_packet_to_send())
        ack_1 = {
          'seq_num': 0,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }
        strategy.process_ack(json.dumps(ack_1))
        # Processing this ack increases window size to 2
        self.assertEqual(strategy.cwnd, 2)

        # Now that window size is 2, we can send two segments
        second_segment = strategy.next_packet_to_send()

        self.assertEqual(json.loads(second_segment)['seq_num'], 1)
        third_segment = strategy.next_packet_to_send()

        self.assertEqual(json.loads(third_segment)['seq_num'], 2)
        self.assertIsNone(strategy.next_packet_to_send())

        ack_2 = {
          'seq_num': 1,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        strategy.process_ack(json.dumps(ack_2))

        self.assertEqual(strategy.cwnd, 3)
        ack_3 = {
          'seq_num': 2,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        strategy.process_ack(json.dumps(ack_3))
        self.assertEqual(strategy.cwnd, 4)
        ack_4 = {
          'seq_num': 3,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        strategy.process_ack(json.dumps(ack_4))
        # We've moved into congestion avoidance now,
        # so the window won't increase until the whole
        # current window has been acknowledged

        self.assertEqual(strategy.cwnd, 4)

    def test_retransmitting_packets(self):
        strategy = TahoeStrategy(3, 1)
        first_segment = strategy.next_packet_to_send()
        ack_1 = {
          'seq_num': 0,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }
        strategy.process_ack(json.dumps(ack_1))

        self.assertEquals(strategy.cwnd, 2)
        second_segment = strategy.next_packet_to_send()
        third_segment = strategy.next_packet_to_send()
        duplicate_ack = {
          'seq_num': 0,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        strategy.process_ack(json.dumps(duplicate_ack))
        self.assertIsNone(strategy.next_packet_to_send())
        strategy.process_ack(json.dumps(duplicate_ack))
        self.assertIsNone(strategy.next_packet_to_send())
        strategy.process_ack(json.dumps(duplicate_ack))
        # 3 duplicate acks, cwnd becomes 1, retransmit packet
        self.assertEquals(strategy.cwnd, 1)
        retransmit_segment = strategy.next_packet_to_send()
        self.assertEquals(json.loads(retransmit_segment)['seq_num'], 1)
        recovery_ack = {
          'seq_num': 2,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        strategy.process_ack(json.dumps(recovery_ack))

        # Window goes back up to 2, and is empty
        self.assertEquals(strategy.cwnd, 2)
        self.assertIsNotNone(strategy.next_packet_to_send())
        self.assertIsNotNone(strategy.next_packet_to_send())

    def test_partial_ack(self):
        strategy = TahoeStrategy(3, 1)
        first_segment = strategy.next_packet_to_send()
        ack_1 = {
          'seq_num': 0,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        strategy.process_ack(json.dumps(ack_1))
        self.assertEquals(strategy.cwnd, 2)
        second_segment = strategy.next_packet_to_send()
        third_segment = strategy.next_packet_to_send()
        duplicate_ack = {
          'seq_num': 0,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        strategy.process_ack(json.dumps(duplicate_ack))
        self.assertIsNone(strategy.next_packet_to_send())
        strategy.process_ack(json.dumps(duplicate_ack))
        self.assertIsNone(strategy.next_packet_to_send())
        strategy.process_ack(json.dumps(duplicate_ack))
        self.assertEquals(strategy.cwnd, 1)
        retransmit_segment = strategy.next_packet_to_send()
        self.assertEquals(json.loads(retransmit_segment)['seq_num'], 1)
        # Sequence number #2 is still unacknowledged
        recovery_ack = {
          'seq_num': 1,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }
        self.assertIsNone(strategy.next_packet_to_send())
        # TODO: Implement timeouts, so that after the timeout, we can send back
        # seq # 2. Given current implementation, we'll just get stuck at this point.

class TestRenoSender(unittest.TestCase):
    def test_segments_received_in_order(self):
        strategy = TahoeStrategy(3, 1)
        first_segment = strategy.next_packet_to_send()
        self.assertEqual(json.loads(first_segment)['seq_num'], 0)
        self.assertEqual(strategy.unacknowledged_packets[0]['seq_num'], 0)
        # Window starts at 1, so window is full at this point
        self.assertIsNone(strategy.next_packet_to_send())
        ack_1 = {
          'seq_num': 0,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }
        strategy.process_ack(json.dumps(ack_1))
        # Processing this ack increases window size to 2
        self.assertEqual(strategy.cwnd, 2)

        # Now that window size is 2, we can send two segments
        second_segment = strategy.next_packet_to_send()

        self.assertEqual(json.loads(second_segment)['seq_num'], 1)
        third_segment = strategy.next_packet_to_send()

        self.assertEqual(json.loads(third_segment)['seq_num'], 2)
        self.assertIsNone(strategy.next_packet_to_send())

        ack_2 = {
          'seq_num': 1,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        strategy.process_ack(json.dumps(ack_2))

        self.assertEqual(strategy.cwnd, 3)
        ack_3 = {
          'seq_num': 2,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        strategy.process_ack(json.dumps(ack_3))
        self.assertEqual(strategy.cwnd, 4)
        ack_4 = {
          'seq_num': 3,
          'send_ts': time.time(),
          'sent_bytes': 10,
          'ack_bytes': 10
        }

        strategy.process_ack(json.dumps(ack_4))
        # We've moved into congestion avoidance now,
        # so the window won't increase until the whole
        # current window has been acknowledged

        self.assertEqual(strategy.cwnd, 4)


class TestFixedWindowSender(unittest.TestCase):
    pass
