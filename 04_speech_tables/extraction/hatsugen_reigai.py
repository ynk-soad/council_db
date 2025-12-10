import re
from pathlib import Path

pat = re.compile(
    r'([○◯◆◎])\s*[0-9０-９]+\s*番\s*[（(]\s*([^;；（）()\n]+?)\s*(?:[;；])?\s*[）)]'
)

def normalize_numbered_speaker(text: str) -> str:
    return pat.sub(r'\1\2;', text)

base = Path("/Users/ynkhiru09/Downloads/munakata/改善")  # ←処理したいフォルダに変更
for p in base.rglob("*.txt"):
    s = p.read_text(encoding="utf-8", errors="ignore")
    out = normalize_numbered_speaker(s)
    out_path = p.with_name(p.stem + "_norm" + p.suffix)
    out_path.write_text(out, encoding="utf-8")
