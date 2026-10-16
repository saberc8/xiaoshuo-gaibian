import io
import posixpath
import zipfile
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from lxml import etree

BLOCKS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "div", "section", "article", "blockquote", "pre", "td"}
SKIP = {"script", "style", "svg", "rt", "rp", "noscript"}


class EpubError(ValueError):
    pass


def local_name(element) -> str:
    return etree.QName(element).localname.lower() if isinstance(element.tag, str) else ""


def xml(data: bytes) -> etree._ElementTree:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
    try:
        return etree.parse(io.BytesIO(data), parser)
    except etree.XMLSyntaxError as exc:
        raise EpubError("EPUB 内的 XML / XHTML 格式不完整，无法可靠解析") from exc


def member_path(base: str, href: str) -> str:
    parts = urlsplit(href)
    if parts.scheme or parts.netloc or parts.path.startswith("/"):
        raise EpubError("EPUB 引用了不支持的外部或绝对路径")
    path = posixpath.normpath(posixpath.join(posixpath.dirname(base), unquote(parts.path)))
    if path.startswith("../") or path == ".." or "\\" in path:
        raise EpubError("EPUB 的资源路径超出了书籍目录")
    return path


def validate_archive(data: bytes, max_bytes: int) -> zipfile.ZipFile:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise EpubError("文件不是有效的 EPUB（ZIP 容器）") from exc
    entries = archive.infolist()
    if len(entries) > 4000 or sum(item.file_size for item in entries) > max_bytes:
        raise EpubError("EPUB 解压体积或资源数量超过限制")
    names = [entry.filename for entry in entries]
    if len(names) != len(set(names)):
        raise EpubError("EPUB 内存在重复资源路径")
    for entry in entries:
        path = PurePosixPath(entry.filename)
        if path.is_absolute() or ".." in path.parts or "\\" in entry.filename:
            raise EpubError("EPUB 内存在不安全的资源路径")
        if entry.flag_bits & 1:
            raise EpubError("不支持加密的 EPUB")
        if entry.file_size > 1024 * 1024 and entry.file_size / max(entry.compress_size, 1) > 250:
            raise EpubError("EPUB 的压缩比异常")
    try:
        if archive.read("mimetype").strip() != b"application/epub+zip":
            raise EpubError("文件缺少有效的 EPUB 类型声明")
    except KeyError as exc:
        raise EpubError("文件缺少 EPUB 类型声明") from exc
    return archive


def extract_paragraphs(tree: etree._ElementTree) -> list[dict]:
    """Keep exact text and the XML text-node coordinates, including inline spans."""
    bodies = tree.xpath("//*[local-name()='body']")
    if not bodies:
        return []
    paragraphs, pending, anchors = [], [], {}

    def add(element, slot: str):
        text = getattr(element, slot)
        if text:
            pending.append({"xpath": tree.getpath(element), "slot": slot, "text": text})

    def flush():
        nonlocal pending
        raw = "".join(item["text"] for item in pending)
        clean = raw.strip()
        if clean:
            left = len(raw) - len(raw.lstrip())
            right = left + len(clean)
            spans, cursor = [], 0
            for item in pending:
                end = cursor + len(item["text"])
                a, b = max(cursor, left), min(end, right)
                if a < b:
                    spans.append({
                        "xpath": item["xpath"], "slot": item["slot"],
                        "start": a - left, "end": b - left, "node_start": a - cursor,
                    })
                cursor = end
            paragraphs.append({"id": f"p{len(paragraphs) + 1:05d}", "text": clean, "spans": spans})
        pending = []

    def walk(element):
        tag = local_name(element)
        if tag in SKIP or not tag:
            return
        if tag in BLOCKS or tag == "br":
            flush()
        identifier = element.get("id") or element.get("{http://www.w3.org/XML/1998/namespace}id")
        if identifier:
            anchors[identifier] = len(paragraphs)
        add(element, "text")
        for child in element:
            walk(child)
            add(child, "tail")
        if tag in BLOCKS:
            flush()

    walk(bodies[0])
    flush()
    for identifier, index in anchors.items():
        if index < len(paragraphs):
            paragraphs[index].setdefault("anchors", []).append(identifier)
    return paragraphs


def parse_epub(data: bytes, max_bytes: int) -> dict:
    try:
        with validate_archive(data, max_bytes) as archive:
            container = xml(archive.read("META-INF/container.xml"))
            roots = container.xpath("//*[local-name()='rootfile']/@full-path")
            if not roots:
                raise EpubError("EPUB 缺少 OPF 书籍清单")
            opf_path = member_path("", roots[0])
            opf = xml(archive.read(opf_path))
            titles = opf.xpath("//*[local-name()='metadata']/*[local-name()='title']/text()")
            authors = opf.xpath("//*[local-name()='metadata']/*[local-name()='creator']/text()")
            manifest = {
                item.get("id"): {
                    "path": member_path(opf_path, item.get("href", "")),
                    "type": item.get("media-type"), "properties": item.get("properties", "").split(),
                }
                for item in opf.xpath("//*[local-name()='manifest']/*[local-name()='item']")
            }
            nav_entries, ncx_entries = [], []
            for item in manifest.values():
                if "nav" in item["properties"]:
                    nav = xml(archive.read(item["path"]))
                    navigations = nav.xpath("//*[local-name()='nav']")
                    toc = next((element for element in navigations if "toc" in element.get("{http://www.idpf.org/2007/ops}type", "").split()), None)
                    if toc is None:
                        toc = navigations[0] if navigations else nav.getroot()
                    for link in toc.xpath(".//*[local-name()='a'][@href]"):
                        parent = link.getparent()
                        if parent is not None and parent.xpath("./*[local-name()='ol' or local-name()='ul']"):
                            continue
                        href = link.get("href")
                        nav_entries.append({"path": member_path(item["path"], href),
                                            "fragment": unquote(urlsplit(href).fragment),
                                            "title": "".join(link.itertext()).strip()})
                elif item["type"] == "application/x-dtbncx+xml":
                    ncx = xml(archive.read(item["path"]))
                    for point in ncx.xpath("//*[local-name()='navPoint']"):
                        if point.xpath("./*[local-name()='navPoint']"):
                            continue
                        paths = point.xpath("./*[local-name()='content']/@src")
                        texts = point.xpath("./*[local-name()='navLabel']/*[local-name()='text']/text()")
                        if paths and texts:
                            ncx_entries.append({"path": member_path(item["path"], paths[0]),
                                                "fragment": unquote(urlsplit(paths[0]).fragment), "title": texts[0].strip()})
            toc_entries = nav_entries or ncx_entries
            encrypted = set()
            if "META-INF/encryption.xml" in archive.namelist():
                encrypted = set(xml(archive.read("META-INF/encryption.xml")).xpath("//*[local-name()='CipherReference']/@URI"))
            chapters, seen = [], set()
            for ref in opf.xpath("//*[local-name()='spine']/*[local-name()='itemref']"):
                item = manifest.get(ref.get("idref"))
                if not item:
                    raise EpubError("阅读顺序引用了不存在的章节")
                if ref.get("linear") == "no" or "nav" in item["properties"] or item["type"] not in {"application/xhtml+xml", "text/html"}:
                    continue
                path = item["path"]
                if path in seen:
                    continue
                if path in encrypted:
                    raise EpubError("这本 EPUB 的正文受加密保护，无法解析")
                seen.add(path)
                tree = xml(archive.read(path))
                paragraphs = extract_paragraphs(tree)
                if not paragraphs:
                    continue
                headings = tree.xpath("//*[local-name()='h1' or local-name()='h2']")
                heading = "".join(headings[0].itertext()).strip() if headings else ""
                entries = [entry for entry in toc_entries if entry["path"] == path]
                anchors = {anchor: index for index, paragraph in enumerate(paragraphs) for anchor in paragraph.get("anchors", [])}
                starts = {}
                for entry in entries:
                    position = anchors.get(entry["fragment"]) if entry["fragment"] else 0
                    if position is not None:
                        starts.setdefault(position, entry)
                fallback = {"title": heading or f"第 {len(chapters) + 1} 章", "fragment": ""}
                if not starts:
                    starts[0] = entries[0] if entries else fallback
                elif 0 not in starts:
                    starts[0] = fallback
                boundaries = sorted(starts)
                for i, start in enumerate(boundaries):
                    end = boundaries[i + 1] if i + 1 < len(boundaries) else len(paragraphs)
                    part = paragraphs[start:end]
                    if not part:
                        continue
                    entry = starts[start]
                    chapters.append({
                        "id": f"ch{len(chapters) + 1:04d}", "index": len(chapters) + 1,
                        "title": entry["title"] or fallback["title"], "fragment": entry.get("fragment", ""),
                        "path": path, "paragraphs": part,
                        "word_count": sum(len(p["text"].strip()) for p in part),
                    })
            if not chapters:
                raise EpubError("没有找到可阅读的正文，请确认 EPUB 包含未加密的 XHTML 章节")
            return {
                "title": titles[0].strip() if titles else "未命名小说",
                "author": "、".join(authors) or "作者未署名", "opf_path": opf_path,
                "chapters": chapters, "word_count": sum(ch["word_count"] for ch in chapters),
            }
    except (KeyError, zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise EpubError("EPUB 缺少必要资源或资源无法读取") from exc
