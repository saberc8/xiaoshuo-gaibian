import hashlib
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .adaptation_models import BookSource
from .bookio import text_epub
from .config import Settings
from .demo import demo_epub
from .epub import parse_epub
from .store import Store


def new_id() -> str:
    return uuid.uuid4().hex


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_chunks(chapters: list[dict], scope: list[str]) -> list[dict]:
    chunks = []
    for chapter in chapters:
        if chapter["id"] not in scope:
            continue
        group, size = [], 0

        def flush():
            nonlocal group, size
            if group:
                chunks.append({"id": f"chunk{len(chunks) + 1:05d}", "chapter_id": chapter["id"],
                               "chapter_title": chapter["title"], "paragraphs": group})
                group, size = [], 0

        for paragraph in chapter["paragraphs"]:
            offset = 0
            while offset < len(paragraph["text"]):
                part = paragraph["text"][offset:offset + 9000]
                if size + len(part) > 10000:
                    flush()
                group.append({"id": paragraph["id"], "text": part, "start": offset})
                size += len(part)
                if offset + len(part) == len(paragraph["text"]):
                    break
                flush()
                offset += 8700
        flush()
    return chunks


class Studio:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = Store(settings.data_dir, settings.database_url, settings.database_schema)

    def import_book(self, content: bytes, filename: str, is_demo=False) -> dict:
        if not content or len(content) > self.settings.max_upload_bytes:
            raise ValueError("请上传不超过 30 MB 的 EPUB / TXT 文件")
        extension = Path(filename).suffix.lower()
        if extension not in {".epub", ".equb", ".txt"}:
            raise ValueError("支持 EPUB 或 TXT 小说文件")
        encoding = ""
        canonical, encoding = text_epub(content, filename) if extension == ".txt" else (content, encoding)
        parsed = parse_epub(canonical, self.settings.max_archive_bytes)
        identifier = new_id()
        directory = self.store.directory / identifier
        directory.mkdir()
        try:
            (directory / "original.epub").write_bytes(canonical)
            if extension == ".txt":
                (directory / "original.txt").write_bytes(content)
            book = {"id": identifier, "created_at": now(), "filename": filename,
                    "source_format": "txt" if extension == ".txt" else "epub", "encoding": encoding,
                    "source_sha256": hashlib.sha256(content).hexdigest(),
                    "source": BookSource(rights_basis="own_work" if is_demo else "unknown").model_dump(),
                    "is_demo": is_demo, **parsed}
            self.store.put("book", book)
        except Exception:
            shutil.rmtree(directory)
            raise
        return self.book_summary(book)

    def demo(self) -> dict:
        for book in self.store.list("book"):
            if book.get("is_demo"):
                return self.book_summary(book)
        return self.import_book(demo_epub(), "雾港来信.epub", is_demo=True)

    def book_summary(self, book: dict) -> dict:
        return {key: value for key, value in book.items() if key not in {"chapters", "opf_path", "characters"}} | {
            "chapter_count": len(book["chapters"]),
            "chapters": [{key: chapter[key] for key in ("id", "index", "title", "word_count")} for chapter in book["chapters"]],
        }

    def list_books(self) -> list[dict]:
        return [self.book_summary(book) for book in self.store.list("book")]

    def book(self, book_id: str) -> dict:
        return self.book_summary(self.store.get("book", book_id))

    def set_source(self, book_id: str, source: dict) -> dict:
        def update(book):
            merged = BookSource.model_validate({**book.get("source", {}), **source}).model_dump()
            book["source"] = merged
            if merged["title"].strip():
                book["title"] = merged["title"].strip()
            if merged["author"].strip():
                book["author"] = merged["author"].strip()
        return self.book_summary(self.store.mutate("book", book_id, update))

    def original(self, book_id: str) -> tuple[bytes, str, str]:
        book = self.store.get("book", book_id)
        text = book.get("source_format") == "txt"
        path = self.store.directory / book_id / ("original.txt" if text else "original.epub")
        return path.read_bytes(), "text/plain" if text else "application/epub+zip", book["filename"]

    @staticmethod
    def scope(book: dict, chapter_ids: list[str]) -> list[str]:
        valid = {chapter["id"] for chapter in book["chapters"]}
        if not chapter_ids or not set(chapter_ids) <= valid:
            raise ValueError("请选择至少一个存在的章节")
        return [chapter["id"] for chapter in book["chapters"] if chapter["id"] in set(chapter_ids)]

    def read_chapter(self, book_id: str, chapter_id: str) -> dict:
        book = self.store.get("book", book_id)
        chapter = next((c for c in book["chapters"] if c["id"] == chapter_id), None)
        if chapter is None:
            raise KeyError("找不到原著章节")
        return {"chapter_id": chapter_id, "title": chapter["title"],
                "paragraphs": [{"id": p["id"], "original": p["text"]} for p in chapter["paragraphs"]]}
