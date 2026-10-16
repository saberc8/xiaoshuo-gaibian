import io
import zipfile
import pytest
from backend.app.config import Settings
from backend.app.demo import demo_epub
from backend.app.epub import EpubError, parse_epub
from backend.app.service import Studio, make_chunks

@pytest.fixture
def studio(tmp_path):
    return Studio(Settings(data_dir=tmp_path, _env_file=None))


@pytest.fixture
def book(studio):
    return studio.demo()


def archive_with(changes: dict[str, bytes | str]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(demo_epub())) as original, zipfile.ZipFile(output, "w") as result:
        for entry in original.infolist():
            result.writestr(entry, changes.get(entry.filename, original.read(entry.filename)))
        for name, content in changes.items():
            if name not in original.namelist():
                result.writestr(name, content)
    return output.getvalue()


def test_parsing_follows_spine_not_zip_order_and_ignores_nav():
    parsed = parse_epub(demo_epub(), 200 * 1024 * 1024)
    assert parsed["title"] == "雾港来信"
    assert len(parsed["chapters"]) == 8
    assert parsed["chapters"][0]["title"] == "第一章 · 雾中的来信"
    assert parsed["chapters"][-1]["path"] == "OEBPS/chapter8.xhtml"
    assert any("二少爷" in paragraph["text"] for paragraph in parsed["chapters"][0]["paragraphs"])


def test_long_paragraphs_are_chunked_without_losing_coverage():
    text = "沈砚沿着码头走去。" * 3000
    chunks = make_chunks([{"id": "ch0001", "title": "长段落", "paragraphs": [{"id": "p00001", "text": text}]}], ["ch0001"])
    assert len(chunks) > 1
    covered = set()
    for chunk in chunks:
        assert sum(len(p["text"]) for p in chunk["paragraphs"]) <= 10000
        for paragraph in chunk["paragraphs"]:
            covered.update(range(paragraph["start"], paragraph["start"] + len(paragraph["text"])))
    assert len(covered) == len(text)


@pytest.mark.parametrize("content", [b"not an epub", archive_with({"../escape.txt": "bad"}), archive_with({"mimetype": "wrong"})])
def test_invalid_archives_are_rejected(content):
    with pytest.raises(EpubError):
        parse_epub(content, 200 * 1024 * 1024)


def test_encrypted_body_is_rejected_but_encrypted_fonts_are_allowed():
    encrypted = '<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><EncryptedData xmlns="http://www.w3.org/2001/04/xmlenc#"><CipherData><CipherReference URI="OEBPS/chapter1.xhtml"/></CipherData></EncryptedData></encryption>'
    with pytest.raises(EpubError, match="加密"):
        parse_epub(archive_with({"META-INF/encryption.xml": encrypted}), 200 * 1024 * 1024)
    assert parse_epub(archive_with({"META-INF/encryption.xml": encrypted.replace("chapter1.xhtml", "font.ttf")}), 200 * 1024 * 1024)["chapters"]


def test_fragment_chapters_in_one_document_are_read_independently(studio):
    chapter = '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Three chapters</title></head><body><h1 id="first">第一章</h1><p>沈砚走进书店。</p><a id="second"/><h2>第二章</h2><p>沈砚走向码头。</p><section id="third"><h2>第三章</h2><p>沈砚回到家里。</p></section></body></html>'
    nav = '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>TOC</title></head><body><nav epub:type="toc"><ol><li><a href="chapter1.xhtml#first">第一章</a></li><li><a href="chapter1.xhtml#second">第二章</a></li><li><a href="chapter1.xhtml#third">第三章</a></li></ol></nav></body></html>'
    original = demo_epub()
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        opf = archive.read("OEBPS/content.opf").decode()
    import re
    opf = re.sub(r'<itemref idref="ch[2-8]"/>', '', opf)
    imported = studio.import_book(archive_with({"OEBPS/chapter1.xhtml": chapter, "OEBPS/nav.xhtml": nav, "OEBPS/content.opf": opf}), "fragment.epub")
    assert imported["chapter_count"] == 3
    for number, phrase in enumerate(['沈砚走进书店。', '沈砚走向码头。', '沈砚回到家里。'], 1):
        chapter = studio.read_chapter(imported['id'], f'ch{number:04d}')
        assert any(p['original'] == phrase for p in chapter['paragraphs'])



def test_mcp_configuration_preserves_unrelated_sections():
    from scripts.configure_mcp import merge
    existing = 'model = "custom"\n[mcp_servers.other]\ncommand = "other"\n[mcp_servers.novelstudio]\ncommand = "old"\n[mcp_servers.novelstudio.env]\nNOVEL_API_URL = "old"\n[unrelated]\nvalue = 1\n'
    result = merge(existing, '[mcp_servers.novelstudio]\ncommand = "new"\n')
    assert 'model = "custom"' in result
    assert '[mcp_servers.other]' in result
    assert '[unrelated]' in result
    assert 'command = "old"' not in result
    assert result.count('[mcp_servers.novelstudio]') == 1


