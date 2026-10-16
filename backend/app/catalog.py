"""Reading/source leads, not a jurisdiction-independent copyright certification."""
from urllib.parse import quote

CATALOG = [
    {"id": "liaozhai", "title": "聊斋志异", "author": "蒲松龄", "language": "古汉语", "hook": "狐鬼情感、欲望反噬", "direction": "单元志怪 / 因果系统", "url": "https://zh.wikisource.org/wiki/聊齋志異", "edition_note": "选原典；现代白话改写、注释和插图需另看来源。"},
    {"id": "digong", "title": "狄公案（清代版本）", "author": "佚名", "language": "古汉语", "hook": "单案悬疑、有限角色与场景", "direction": "修真断案 / 宗门悬疑", "url": "https://zh.wikisource.org/wiki/狄公案", "edition_note": "选择清代原典；高罗佩创作的狄仁杰系列是另一组作品。"},
    {"id": "jinghuayuan", "title": "镜花缘", "author": "李汝珍", "language": "古汉语", "hook": "异国规则、群像冒险", "direction": "诸天秘境 / 规则闯关", "url": "https://zh.wikisource.org/wiki/鏡花緣", "edition_note": "建议先选一个奇异国度，控制试写范围。"},
    {"id": "jekyll", "title": "化身博士", "author": "Robert Louis Stevenson", "language": "English", "hook": "双重身份、变身失控", "direction": "心魔分身 / 禁术反噬", "url": "https://www.gutenberg.org/ebooks/43", "edition_note": "英文原文；中文译本单独记录译者和版本。"},
    {"id": "dorian", "title": "道连·格雷的画像", "author": "Oscar Wilde", "language": "English", "hook": "容貌不老、画像承受代价", "direction": "命魂画卷 / 寿元交易", "url": "https://www.gutenberg.org/ebooks/174", "edition_note": "英文原文；可保留“代价转移”的核心机制。"},
    {"id": "carmilla", "title": "卡米拉", "author": "Sheridan Le Fanu", "language": "English", "hook": "吸血鬼、危险的亲密关系", "direction": "血契 / 身份悬疑", "url": "https://www.gutenberg.org/ebooks/10007", "edition_note": "英文原文；人物年龄和关系在改编设定中明确。"},
    {"id": "white", "title": "白衣女人", "author": "Wilkie Collins", "language": "English", "hook": "身份替换、婚姻与财产骗局", "direction": "夺舍身份 / 宗族继承", "url": "https://www.gutenberg.org/ebooks/583", "edition_note": "长篇建议先选择一条身份骗局主线。"},
    {"id": "montecristo", "title": "基督山伯爵", "author": "Alexandre Dumas", "language": "French / English translation", "hook": "冤狱、换身份、复仇", "direction": "重返宗门 / 多线复仇", "url": "https://www.gutenberg.org/ebooks/1184", "edition_note": "此入口是英文译本，法文原作与各译本分别记录；建议压缩人物。"},
    {"id": "princess", "title": "小公主", "author": "Frances Hodgson Burnett", "language": "English", "hook": "身份跌落、受辱与逆转", "direction": "落魄世家 / 身份逆转", "url": "https://www.gutenberg.org/ebooks/146", "edition_note": "英文原文；保留人物尊严和清晰的情绪线。"},
    {"id": "monkey", "title": "猴爪", "author": "W. W. Jacobs", "language": "English", "hook": "三个愿望及其代价", "direction": "三愿因果系统 / 短篇试播", "url": "https://www.gutenberg.org/ebooks/12122", "edition_note": "短篇，适合首先验证分析、改编、审查、导出全流程。"},
]

PRESETS = [
    {"id": "custom", "name": "自由改编", "description": "按你的想法重设人物、情节与世界。"},
    {"id": "localize", "name": "中外本土化", "description": "统一姓名、别名、称谓、地名和文化语境，保留因果主线。"},
    {"id": "xianxia", "name": "修仙世界", "description": "将原作冲突迁入宗门与修炼体系，明确境界、晋升、代价与上限。"},
    {"id": "system", "name": "系统流", "description": "围绕能力触发、任务奖励、资源消耗和失败惩罚重构情节。"},
    {"id": "xianxia_system", "name": "修仙 × 系统", "description": "修炼与系统共同驱动剧情，能力不能绕过已约定的代价与限制。"},
    {"id": "suspense", "name": "悬疑重构", "description": "重排线索、误导与揭示时机，维护证据与身份逻辑。"},
    {"id": "revenge", "name": "复仇逆袭", "description": "压缩人物，重设冤屈、隐秘身份、反击与代价。"},
    {"id": "anthology", "name": "单元冒险", "description": "每个单元有独立规则、冲突、转折与收束。"},
]


def source_catalog():
    return {"works": [{**work, "url": quote(work["url"], safe=":/")} for work in CATALOG],
            "presets": PRESETS,
            "note": "这些是原作素材入口。公版状态与使用地区、具体版本有关；现代翻译、注释和插图单独记录。Gutenberg 的公版标注以美国为准。",
            "rights_reference": "https://www.gutenberg.org/policy/permission.html"}
