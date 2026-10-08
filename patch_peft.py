import pathlib, re
p = pathlib.Path("scripts/phase2/train_detection_lora.py")
s = p.read_text(encoding="utf-8")
start = s.index("trainer = SFTTrainer(")
end = s.index("\n    )\n", start)
block = s[start:end]
pat = re.compile(r"^[ \t]*peft_config[ \t]*=[^\n]*,[ \t]*\n", re.M)
found = pat.findall(block + "\n")
print("lines to remove:", found)
assert len(found) == 1, "expected exactly one single-line peft_config argument"
block = pat.sub("", block + "\n").rstrip("\n")
s = s[:start] + block + s[end:]
p.write_text(s, encoding="utf-8")
print("patched")
