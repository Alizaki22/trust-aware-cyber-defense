import pathlib, re

METHOD = '''
    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, v):
        if isinstance(v, (int, float)):
            if v >= 0.75:
                return "high"
            if v >= 0.4:
                return "medium"
            if v > 0:
                return "low"
            return "none"
        return v
'''

for p in pathlib.Path("src").rglob("*.py"):
    s = p.read_text(encoding="utf-8")
    m = re.search(r"^class DetectionModelOutput\b.*:[ \t]*$", s, re.M)
    if not m:
        continue
    if "_coerce_confidence" in s:
        print("already patched:", p)
        break
    s = s[:m.end()] + METHOD + s[m.end():]
    imp = "from pydantic import field_validator\n"
    fut = re.search(r"^from __future__ import .*\n", s, re.M)
    if fut:
        s = s[:fut.end()] + imp + s[fut.end():]
    else:
        s = imp + s
    p.write_text(s, encoding="utf-8")
    print("patched:", p)
    break
else:
    print("DetectionModelOutput not found")
