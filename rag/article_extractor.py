"""从 reference 文本中解析 law_name 和 article_num。"""
import re
import hashlib

_LAW_RE = re.compile(r'《([^》]+)》')
# 只匹配开头的主条文标识，避免提取正文内交叉引用
_MAIN_ART_RE = re.compile(r'^[^第]*第([零一二三四五六七八九十百千\d]+)条')


def extract_articles(ref_text: str, fallback_id: str) -> list[dict]:
    law_names = _LAW_RE.findall(ref_text)
    law_name = law_names[0] if law_names else ""

    m = _MAIN_ART_RE.search(ref_text)
    article_num = m.group(1) if m else ""

    if not law_name and not article_num:
        return [{"id": fallback_id, "law_name": "", "article_num": "",
                 "text": ref_text, "source_doc_id": fallback_id}]

    art_id = _make_id(law_name, article_num) if (law_name or article_num) else fallback_id
    return [{"id": art_id, "law_name": law_name,
             "article_num": f"第{article_num}条" if article_num else "",
             "text": ref_text, "source_doc_id": fallback_id}]


def _make_id(law_name: str, article_num: str) -> str:
    return hashlib.md5(f"{law_name}_{article_num}".encode()).hexdigest()[:16]
