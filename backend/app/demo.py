import io
import zipfile
from html import escape

CHAPTERS = [
    ("第一章 · 雾中的来信", [
        "雾港的雨，已经下了整整三天。沿着青石路往里走，街角那间旧书店的灯还亮着。",
        "沈砚站在窗前，手里握着一封没有落款的信。信纸被雨水洇湿了一角，墨迹像夜色一样缓缓散开。",
        "“阿砚。”苏晚推开门，抖了抖伞上的水，“你也收到那封信了？”",
        "沈砚没有回答，只把信放在了桌上。她认得那个字迹，也认得信封上那枚蓝色的邮票。",
        "街对面的老人探进头来：“二少爷，沈家的船昨夜回港了。有人托我告诉你，千万别去旧码头。”",
        "苏晚看了沈砚一眼。雨声忽然大了起来，像有人在屋顶上轻轻敲门。",
        "陆辞的车停在门外。他没有下车，只隔着车窗，望向书店那盏昏黄的灯。",
        "这座城市藏了太多故事。而他们的故事，才刚刚开始。",
    ]),
    ("第二章 · 旧码头", ["天还没亮，沈砚已经走到了码头。", "苏晚从另一头赶来，低声说：“沈少爷，你还是来了。”", "陆辞靠在仓库门边，手里拿着一本账册。", "“陆先生，我们想知道昨夜那艘船的事。”苏晚说。", "远处传来汽笛声。二少爷望着沈家旧船的方向，捏紧了手中的信。"]),
    ("第三章 · 蓝色邮票", ["苏晚在报社翻了一下午的旧报纸。", "沈砚带来一杯热茶，放在她的手边。", "“阿砚，这枚邮票只在十年前发行过。”她指着泛黄的纸页。", "陆辞曾在那一年离开雾港。他的名字，出现在一张模糊的照片下面。"]),
    ("第四章 · 雨夜访客", ["书店打烊之后，苏小姐还坐在窗边。", "门铃响了，陆先生带着一身雨水走进来。", "“沈砚，有些事我一直没有告诉你。”陆辞说。", "“你说吧。”沈砚把门关上。", "苏晚抬起头，桌上的信纸被风吹得微微一动。"]),
    ("第五章 · 另一位少爷", ["陆家的二少爷从外地回来了。他是陆辞的弟弟，叫陆鸣。", "二少爷让佣人备好马车，说要先去见兄长。", "沈砚在街边看见那辆马车，想起了父亲从前说过的话。", "苏晚提醒他：“同样的称呼，未必是同一个人。”"]),
    ("第六章 · 尘封的账册", ["苏晚终于读懂了陆辞带来的账册。", "每一笔记录，都指向沈家十年前失踪的那艘船。", "“阿砚，我们应该去找那位船长。”苏晚合上账册。", "沈砚点了点头，第一次觉得雾港的雾没有那么浓了。"]),
    ("第七章 · 灯塔", ["沈砚和苏晚沿着海岸向灯塔走去。", "陆辞在灯塔下等他们，脸上带着疲惫的笑意。", "“沈少爷，你要的答案都在这里。”守塔人递来一本航海日志。", "苏小姐打开第一页，看见一行熟悉的字。"]),
    ("第八章 · 雾散以后", ["雾港终于迎来了一个晴天。", "苏晚将写好的报道放在沈砚桌上。", "陆辞在港口送别最后一班船，回头看见书店的门正开着。", "“阿砚，我们走吧。”苏晚说。", "沈砚把那封信收进抽屉，走进了阳光里。"]),
]


def demo_epub() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        items = ''.join(f'<item id="ch{i}" href="chapter{i}.xhtml" media-type="application/xhtml+xml"/>' for i in range(1, len(CHAPTERS) + 1))
        spine = ''.join(f'<itemref idref="ch{i}"/>' for i in range(1, len(CHAPTERS) + 1))
        archive.writestr("OEBPS/content.opf", f'<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="book-id">novel-studio-demo</dc:identifier><dc:title>雾港来信</dc:title><dc:creator>续章 · 示例作品</dc:creator><dc:language>zh-CN</dc:language><meta property="dcterms:modified">2026-10-10T00:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="css" href="style.css" media-type="text/css"/>{items}</manifest><spine>{spine}</spine></package>')
        links = ''.join(f'<li><a href="chapter{i}.xhtml">{escape(title)}</a></li>' for i, (title, _) in enumerate(CHAPTERS, 1))
        archive.writestr("OEBPS/nav.xhtml", f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>目录</title></head><body><nav epub:type="toc"><ol>{links}</ol></nav></body></html>')
        archive.writestr("OEBPS/style.css", "body { font-family: serif; line-height: 1.8; } p { text-indent: 2em; }")
        for i, (title, paragraphs) in enumerate(CHAPTERS, 1):
            content = ''.join(f'<p>{escape(p)}</p>' for p in paragraphs)
            archive.writestr(f"OEBPS/chapter{i}.xhtml", f'<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>{escape(title)}</title><link rel="stylesheet" href="style.css"/></head><body><h1>{escape(title)}</h1>{content}</body></html>')
    return buffer.getvalue()
