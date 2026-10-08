import pathlib
p = pathlib.Path("scripts/phase2/train_detection_lora.py")
s = p.read_text(encoding="utf-8")

old_len = '        max_seq_length=tr.get("max_seq_length", 512),\n'
assert s.count(old_len) == 1, "max_seq_length line not found exactly once"
s = s.replace(old_len, "")

assert "from trl import SFTTrainer" in s
s = s.replace("from trl import SFTTrainer", "from trl import SFTConfig, SFTTrainer", 1)

old_args = "    training_args = TrainingArguments(\n"
assert s.count(old_args) == 1, "TrainingArguments call not found exactly once"
s = s.replace(old_args,
    "    training_args = SFTConfig(\n"
    '        max_length=tr.get("max_seq_length", 512),\n', 1)

p.write_text(s, encoding="utf-8")
print("patched")
