import asyncio
import io
from pathlib import PurePosixPath
from typing import AsyncIterator
from webdav3.client import Client as WebDAVClient
from config import settings

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tiff", ".tif", ".raw", ".cr2", ".nef", ".arw"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp"}
MEDIA_EXTENSIONS = PHOTO_EXTENSIONS | VIDEO_EXTENSIONS


def _make_client() -> WebDAVClient:
    return WebDAVClient({
        "webdav_hostname": settings.nas_webdav_url,
        "webdav_login": settings.nas_username,
        "webdav_password": settings.nas_password,
        "webdav_timeout": 30,
        "webdav_verbose": False,
    })


def _list_recursive(client: WebDAVClient, path: str) -> list[dict]:
    results = []
    try:
        items = client.list(path, get_info=True)
    except Exception:
        return results

    for item in items:
        item_path = item.get("path", "")
        # webdavclient3 returns paths with /webdav prefix sometimes
        if not item_path or item_path.rstrip("/") == path.rstrip("/"):
            continue

        if item.get("isdir"):
            results.extend(_list_recursive(client, item_path))
        else:
            suffix = PurePosixPath(item_path).suffix.lower()
            if suffix in MEDIA_EXTENSIONS:
                results.append({
                    "path": item_path,
                    "filename": PurePosixPath(item_path).name,
                    "folder": str(PurePosixPath(item_path).parent),
                    "size": int(item.get("size", 0) or 0),
                    "is_video": suffix in VIDEO_EXTENSIONS,
                })
    return results


async def list_media_files(path: str | None = None) -> list[dict]:
    root = path or settings.nas_photos_path
    loop = asyncio.get_event_loop()
    client = _make_client()
    return await loop.run_in_executor(None, _list_recursive, client, root)


async def download_file(remote_path: str) -> bytes:
    loop = asyncio.get_event_loop()
    client = _make_client()

    def _download() -> bytes:
        buf = io.BytesIO()
        client.download_from(buf, remote_path)
        return buf.getvalue()

    return await loop.run_in_executor(None, _download)


async def list_folders(path: str | None = None) -> list[dict]:
    root = path or settings.nas_photos_path
    loop = asyncio.get_event_loop()
    client = _make_client()

    def _list() -> list[dict]:
        folders = []
        try:
            items = client.list(root, get_info=True)
        except Exception:
            return folders
        for item in items:
            if item.get("isdir") and item.get("path", "").rstrip("/") != root.rstrip("/"):
                folders.append({
                    "path": item["path"],
                    "name": PurePosixPath(item["path"].rstrip("/")).name,
                })
        return folders

    return await loop.run_in_executor(None, _list)


async def check_connection() -> bool:
    loop = asyncio.get_event_loop()
    client = _make_client()

    def _check() -> bool:
        try:
            client.list(settings.nas_photos_path)
            return True
        except Exception:
            return False

    return await loop.run_in_executor(None, _check)
