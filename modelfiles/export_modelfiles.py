# modelfiles/export_modelfiles.py
# Exports the Modelfiles of the two locally created Sahabat-AI models so they can be
# shared. The FROM line (a local path to the GGUF blob) is replaced by a placeholder;
# edit it to your own GGUF path before running `ollama create`.
# Run from the repository root:  python modelfiles/export_modelfiles.py
import os, re, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = {
    "sahabatgemma-fix": "Sahabat-AI Gemma 2 9B GGUF (Q4_K_M)",
    "sahabatllama-fix": "Sahabat-AI Llama 3 8B GGUF (Q5_K_M)",
}
for name, gguf in MODELS.items():
    text = subprocess.check_output(["ollama", "show", name, "--modelfile"], text=True, encoding="utf-8")
    text = re.sub(r"(?m)^# .*\n", "", text)                      # drop auto-generated comments
    text = re.sub(r"(?m)^FROM .*$", f"FROM ./path/to/{name}.gguf   # {gguf}", text, count=1)
    path = os.path.join(ROOT, "modelfiles", f"{name}.Modelfile")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("written:", path)
print("Check each file: the TEMPLATE must contain the base-model chat template with a system slot.")
