import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from routers import media
from services.indexer import _process_sync


class _Database:
    async def get(self, _model, _photo_id):
        return SimpleNamespace(
            id=1,
            path="/reels/clip.mp4",
            filename="clip.mp4",
            media_type="video",
        )


class MediaTests(unittest.IsolatedAsyncioTestCase):
    def test_indexer_marks_videos_without_downloading_them(self):
        result = _process_sync({
            "path": "/reels/clip.mp4",
            "filename": "clip.mp4",
            "folder": "/reels",
            "is_video": True,
        })

        self.assertEqual(result["media_type"], "video")
        self.assertNotIn("_error", result)

    async def test_full_endpoint_uses_a_video_content_type(self):
        with patch.object(media.nas_client, "download_file", AsyncMock(return_value=b"video")):
            response = await media.full_image(1, _Database())

        self.assertEqual(response.media_type, "video/mp4")
        self.assertEqual(response.headers["accept-ranges"], "bytes")
        self.assertEqual(response.body, b"video")


if __name__ == "__main__":
    unittest.main()
