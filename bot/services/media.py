from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock

from aiogram.types import FSInputFile, Message

from bot.config import ROOT_DIR

logger = logging.getLogger(__name__)

_CACHE_PATH = ROOT_DIR / "data" / "media_ids.json"
_lock = Lock()
_cache: dict[str, dict] | None = None


def _fingerprint(path: Path) -> str:
    st = path.stat()
    return f"{st.st_size}:{int(st.st_mtime)}:{path.name}"


def _load() -> dict[str, dict]:
    global _cache
    if _cache is not None:
        return _cache
    if _CACHE_PATH.exists():
        try:
            data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            _cache = data if isinstance(data, dict) else {}
        except Exception:
            logger.exception("Failed to read media cache %s", _CACHE_PATH)
            _cache = {}
    else:
        _cache = {}
    return _cache


def _save() -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _CACHE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(_load(), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_CACHE_PATH)


def get_file_id(key: str, path: Path) -> str | None:
    entry = _load().get(key)
    if not isinstance(entry, dict):
        return None
    if entry.get("fp") != _fingerprint(path):
        return None
    file_id = entry.get("file_id")
    return file_id if isinstance(file_id, str) and file_id else None


def set_file_id(key: str, path: Path, file_id: str) -> None:
    with _lock:
        cache = _load()
        cache[key] = {
            "file_id": file_id,
            "fp": _fingerprint(path),
            "name": path.name,
        }
        _save()


def has_cached(key: str, path: Path) -> bool:
    return get_file_id(key, path) is not None


async def send_cached_video(
    message: Message,
    *,
    key: str,
    path: Path,
    caption: str | None,
) -> Message:
    file_id = get_file_id(key, path)
    if file_id:
        try:
            return await message.answer_video(
                file_id,
                caption=caption,
                supports_streaming=True,
            )
        except Exception:
            logger.warning("Cached video id expired for %s, re-uploading", key)

    sent = await message.answer_video(
        FSInputFile(path),
        caption=caption,
        supports_streaming=True,
    )
    if sent.video and sent.video.file_id:
        set_file_id(key, path, sent.video.file_id)
        logger.info("Cached video file_id for %s", key)
    return sent


async def send_cached_document(
    message: Message,
    *,
    key: str,
    path: Path,
    caption: str | None,
) -> Message:
    file_id = get_file_id(key, path)
    if file_id:
        try:
            return await message.answer_document(file_id, caption=caption)
        except Exception:
            logger.warning("Cached document id expired for %s, re-uploading", key)

    sent = await message.answer_document(
        FSInputFile(path, filename=path.name),
        caption=caption,
    )
    if sent.document and sent.document.file_id:
        set_file_id(key, path, sent.document.file_id)
        logger.info("Cached document file_id for %s", key)
    return sent
