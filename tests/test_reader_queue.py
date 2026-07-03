import unittest

from rtt_gui4graph.core.reader import BatchQueue


class BatchQueueTest(unittest.TestCase):
    def test_batch_queue_drops_oldest_and_counts_drops(self):
        queue = BatchQueue(capacity=2)
        queue.push([1])
        queue.push([2])
        queue.push([3])
        self.assertEqual(queue.dropped_batches, 1)
        self.assertEqual(queue.drain(max_records=10), [2, 3])

    def test_batch_queue_respects_max_records(self):
        queue = BatchQueue(capacity=3)
        queue.push([1, 2])
        queue.push([3, 4])
        self.assertEqual(queue.drain(max_records=3), [1, 2, 3])
        self.assertEqual(queue.drain(max_records=10), [4])


if __name__ == "__main__":
    unittest.main()
