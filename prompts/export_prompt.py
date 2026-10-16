# prompts/export_prompt.py
# Writes the frozen prompt components from config.py to plain files and
# re-computes the reproducibility hashes reported in the article.
# Run from the repository root:  python prompts/export_prompt.py
import os, sys, json, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import config  # noqa: E402

out = os.path.join(ROOT, "prompts")
files = {
    "system_prompt_id.txt": config.SYSTEM_PROMPT,
    "user_template_id.txt": config.USER_TEMPLATE,
    "oneshot_text_id.txt": config.ONESHOT_TEXT,
}
for name, text in files.items():
    with open(os.path.join(out, name), "w", encoding="utf-8") as f:
        f.write(text)
with open(os.path.join(out, "output_schema.json"), "w", encoding="utf-8") as f:
    json.dump(config.SCHEMA, f, ensure_ascii=False, indent=2)
with open(os.path.join(out, "oneshot_output.json"), "w", encoding="utf-8") as f:
    json.dump(config.ONESHOT_JSON, f, ensure_ascii=False, indent=2)

h_zero = hashlib.sha256((config.SYSTEM_PROMPT + config.USER_TEMPLATE
                         + json.dumps(config.SCHEMA, sort_keys=True)).encode()).hexdigest()[:16]
h_one = hashlib.sha256((config.SYSTEM_PROMPT + config.USER_TEMPLATE
                        + json.dumps(config.SCHEMA, sort_keys=True)
                        + config.ONESHOT_TEXT
                        + json.dumps(config.ONESHOT_JSON, sort_keys=True)).encode()).hexdigest()[:16]
print("zero-shot hash:", h_zero, "(expected 1b432dfeb369b503)")
print("one-shot hash :", h_one, "(expected 195828bed5eab4c3)")
assert h_zero == "1b432dfeb369b503" and h_one == "195828bed5eab4c3", "prompt differs from the article"
print("prompt files written to", out)
