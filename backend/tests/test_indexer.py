import unittest

from services.indexer import _select_pending


class PartialIndexTests(unittest.TestCase):
    def test_sample_limits_only_new_files(self):
        files = [{"path": f"/{number}.jpg"} for number in range(1, 8)]

        pending, sample = _select_pending(files, {"/1.jpg", "/3.jpg"}, limit=3)

        self.assertEqual([item["path"] for item in pending], [
            "/2.jpg", "/4.jpg", "/5.jpg", "/6.jpg", "/7.jpg",
        ])
        self.assertEqual([item["path"] for item in sample], [
            "/2.jpg", "/4.jpg", "/5.jpg",
        ])

    def test_full_index_keeps_every_pending_file(self):
        files = [{"path": "/new-a.jpg"}, {"path": "/new-b.jpg"}]

        pending, selected = _select_pending(files, set())

        self.assertEqual(selected, pending)


if __name__ == "__main__":
    unittest.main()
