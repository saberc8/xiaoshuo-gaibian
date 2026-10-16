"""Canonical EPUB creation for plain-text imports and independently rewritten books."""
import io
import re
import uuid
import zipfile
from datetime import datetime, timezone
from html import escape
from pathlib import Path


def build_epub(title: str, author: str, chapters: list[dict], language: str = "zh-CN") -> bytes:
    identifier = uuid.uuid4().hex
    manifest, spine, navigation = [], [], []
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        for index, chapter in enumerate(chapters, 1):
            filename = f"chapter{index}.xhtml"
            heading = escape(chapter["title"])
            paragraphs = "".join(f"<p>{escape(text)}</p>" for text in chapter["paragraphs"])
            archive.writestr(f"OEBPS/{filename}", f'<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{escape(language, quote=True)}"><head><title>{heading}</title><link rel="stylesheet" href="style.css"/></head><body><h1>{heading}</h1>{paragraphs}</body></html>')
            manifest.append(f'<item id="c{index}" href="{filename}" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="c{index}"/>')
            navigation.append(f'<li><a href="{filename}">{heading}</a></li>')
        archive.writestr("OEBPS/style.css", "body{line-height:1.9;font-family:serif}p{text-indent:2em;white-space:pre-wrap}h1{font-size:1.5em}")
        archive.writestr("OEBPS/nav.xhtml", f'<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>目录</title></head><body><nav epub:type="toc"><ol>{"".join(navigation)}</ol></nav></body></html>')
        modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        archive.writestr("OEBPS/content.opf", f'<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">urn:uuid:{identifier}</dc:identifier><dc:title>{escape(title)}</dc:title><dc:creator>{escape(author)}</dc:creator><dc:language>{escape(language)}</dc:language><meta property="dcterms:modified">{modified}</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="css" href="style.css" media-type="text/css"/>{"".join(manifest)}</manifest><spine>{"".join(spine)}</spine></package>')
    return output.getvalue()


HEADING = re.compile(r"^(?:第[零〇一二三四五六七八九十百千万两\d]+[章节回卷部集](?:\s|[、.．·：:]|[^零〇一二三四五六七八九十百千万两\d]).*|第[零〇一二三四五六七八九十百千万两\d]+[章节回卷部集]|(?:chapter|book|part)\s+(?:[IVXLCDM]+|\d+|one|two|three|four|five|six|seven|eight|nine|ten)(?:\b.*)|[IVXLCDM]+[.．]?)$", re.IGNORECASE)


def text_epub(content: bytes, filename: str) -> tuple[bytes, str]:
    text, encoding = None, ""
    # BOMs are explicit; a strict fallback avoids silently replacing source characters.
    candidates = ["utf-16"] if content.startswith((b"\xff\xfe", b"\xfe\xff")) else ["utf-8-sig", "gb18030"]
    for candidate in candidates:
        try:
            text = content.decode(candidate)
            encoding = candidate
            break
        except UnicodeDecodeError:
            continue
    if text is None or not text.strip() or any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        raise ValueError("TXT 需要使用 UTF-8、GB18030 或带 BOM 的 UTF-16 编码，且包含可读正文")
    title = Path(filename).stem
    chapters, paragraphs, heading = [], [], "正文"

    def flush():
        nonlocal paragraphs
        if paragraphs:
            chapters.append({"title": heading, "paragraphs": paragraphs})
            paragraphs = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if len(line) <= 100 and HEADING.fullmatch(line):
            flush()
            heading = line
        else:
            paragraphs.append(line)
    flush()
    if not chapters:
        raise ValueError("TXT 没有可读正文")
    if len(chapters) > 2000:
        raise ValueError("TXT 章节超过 2000，请拆分文件后导入")
    return build_epub(title, "作者未署名", chapters), encoding
