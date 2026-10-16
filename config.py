# ============================================================
# config.py — Central configuration for the TB CXR extraction pipeline.
# Everything the numbered LLM-Tb-XX scripts need is defined ONCE here.
#
# DAY-TO-DAY USE (Option A): to run the pipeline you edit only TWO lines:
#     SITE          -> which dataset/site to process ("sleman" or "solo")
#     ACTIVE_MODEL  -> which model an LLM script should run (one tag)
# Then click Run on the numbered script. Change ACTIVE_MODEL, Run again, etc.
#
# The frozen prompt/schema below are IDENTICAL to the conference version.
# The asserts at the bottom fail loudly if a single character changes,
# so the reported PROMPT_HASH stays reproducible.
# ============================================================

import os
import json
import hashlib

# ---- 1. WHICH SITE ------------------------------------------------------
# Change this to switch between datasets. Everything else follows.
SITE = "yogya_kesan"            # "sleman"  or  "solo"

# ---- 2. WHICH MODEL (for the LLM scripts) -------------------------------
# One of the LLM tags defined in MODELS below. The rule-based script
# ignores this. Change it per model, then re-run the LLM script.
ACTIVE_MODEL = "gemma4_generik"

# ---- 3. PATHS -----------------------------------------------------------
# Base working directory. All inputs/outputs live under here.
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("TB_DATA_DIR", os.path.join(REPO_DIR, "data"))

# Raw report file per site (edit the filenames to match your files).
RAW_DATA_FILE = {
    "sleman": "Ro Data.xlsx",
    "yogya_full":   "Ro Data Yogya Full.xlsx",
    "yogya_kesan": "Ro Data Yogya Kesan.xlsx",
}

# Per-site output folder (created automatically). Keeps sites separate,
# which is what makes external validation clean.
def site_dir(site=None):
    site = site or SITE
    d = os.path.join(BASE_DIR, site)
    os.makedirs(d, exist_ok=True)
    return d

def out_path(filename, site=None):
    return os.path.join(site_dir(site), filename)

def raw_path(site=None):
    site = site or SITE
    return os.path.join(BASE_DIR, RAW_DATA_FILE[site])

# Shared intermediate/output filenames (live inside the per-site folder).
F_UNIQUE   = "TB_teks_unik.xlsx"          # unique texts (ID_unik, teks, n_baris)
F_MAP      = "TB_peta_baris.xlsx"         # row -> ID_unik map
F_FORM     = "Form_Anotasi_TB_CXR.xlsx"   # blank annotation form
F_RULE     = "RuleBased_pred.xlsx"        # rule-based predictions
F_ANNOT_A  = "Annotation A.xlsx"          # radiologist A (filled form)
F_ANNOT_B  = "Annotation B.xlsx"          # radiologist B (filled form)
F_CONSENSUS= "Form_anotasi_konsensus.xlsx"# consensus patch (long, disagreements)
F_LLM_ZERO = "LLM_predictions.xlsx"       # merged zero-shot predictions
F_LLM_ONE  = "LLM_predictions_oneshot.xlsx"
F_LLM_REP  = "LLM_predictions_repeat.xlsx"
F_EVAL     = "Evaluasi_hasil.xlsx"

def pred_file(condition, model_tag, site=None):
    """Per-model prediction file (checkpoint). condition: 'zeroshot'|'oneshot'|'repeat'."""
    return out_path(f"pred_{condition}_{model_tag}.xlsx", site)

# ---- 4. MODELS ----------------------------------------------------------
# tag -> settings. 'kind': 'rule' or 'llm'. 'ollama': model name to pull/run.
# Verify each LLM name is pullable in your Ollama before running.
# NOTE ON QWEN3.5: it defaults to "thinking mode" and a different
# architecture (MoE + vision). disable_thinking + a separate determinism
# check are flagged; interpret it as a "latest-generation" contrast, NOT
# as a same-generation peer of Gemma2/Llama3.
MODELS = {
    "rule_based":      {"kind": "rule"},
    # --- Gemma family ---
    "gemma2_generik":  {"kind": "llm", "ollama": "gemma2:9b-instruct-q4_K_M"},
    "sahabat_gemma":   {"kind": "llm", "ollama": "sahabatgemma-fix"},
    "gemma4_generik":  {"kind": "llm", "ollama": "gemma4:12b",
                        "disable_thinking": True, "verify_determinism": True},
    # --- Llama family ---
    "llama3_generik":  {"kind": "llm", "ollama": "llama3:8b-instruct-q4_K_M"},
    "sahabat_llama":   {"kind": "llm", "ollama": "sahabatllama-fix"},
    "llama31_generik": {"kind": "llm", "ollama": "llama3.1:8b"},
    # --- Qwen family ---
    "qwen25":          {"kind": "llm", "ollama": "qwen2.5:7b"},
    "qwen35":          {"kind": "llm", "ollama": "qwen3.5:9b",
                        "disable_thinking": True, "verify_determinism": True},
}

# LLM decoding parameters (identical for all models).
OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 4096}

# ---- 5. LABEL SCHEMA ----------------------------------------------------
FINDING_COLS = ["infiltrat", "nodul", "kalsifikasi", "fibrotik", "kavitas"]
LABEL_COLS   = ["is_radiologi", "imp_tb"] + FINDING_COLS + ["kardiomegali"]
# Pretty display names for figures/tables (tag -> label).
DISPLAY_NAMES = {
    "rule_based":      "Rule-based",
    "gemma2_generik":  "Gemma2-9B",
    "sahabat_gemma":   "Sahabat-Gemma2-9B",
    "gemma4_generik":  "Gemma4-12B",
    "llama3_generik":  "Llama3-8B",
    "sahabat_llama":   "Sahabat-Llama3-8B",
    "llama31_generik": "Llama3.1-8B",
    "qwen25":          "Qwen2.5-7B",
    "qwen35":          "Qwen3.5-9B",
}
# Paired contrasts: delta = model_a minus model_b, same texts.
CONTRASTS = [
    # (family, type,          model_a,           model_b)
    ("Gemma", "adaptation",  "sahabat_gemma",   "gemma2_generik"),
    ("Gemma", "version",     "gemma4_generik",  "gemma2_generik"),
    ("Gemma", "trade-off",   "sahabat_gemma",   "gemma4_generik"),
    ("Llama", "adaptation",  "sahabat_llama",   "llama3_generik"),
    ("Llama", "version",     "llama31_generik", "llama3_generik"),
    ("Llama", "trade-off",   "sahabat_llama",   "llama31_generik"),
    ("Qwen",  "version",     "qwen35",          "qwen25"),
]
# Indonesian label -> English term (for manuscript-facing tables/figures).
LABEL_EN = {
    "is_radiologi": "Report type",
    "imp_tb":       "TB impression",
    "infiltrat":    "Infiltrate",
    "nodul":        "Nodule",
    "kalsifikasi":  "Calcification",
    "fibrotik":     "Fibrosis",
    "kavitas":      "Cavitation",
    "kardiomegali": "Cardiomegaly",
}

POWER_THRESHOLD = 10      # minority class >= this -> CI reported; else descriptive
N_BOOT = 1000
SEED   = 42

# ---- 6. FROZEN PROMPT / SCHEMA (identical to conference) ----------------
SYSTEM_PROMPT = 'Anda mengekstraksi informasi terstruktur dari SATU catatan hasil skrining tuberkulosis (TB) berbahasa Indonesia. Nilai HANYA apa yang TERTULIS.\n\nPertama tentukan is_radiologi:\n- "radiologi": teks adalah bacaan/kesan foto toraks, TERMASUK bila hasilnya NORMAL atau tanpa kelainan. Hasil foto yang normal tetap sebuah bacaan radiologi (jadi "radiologi"), BUKAN artefak.\n- "artefak"  : teks sama sekali BUKAN deskripsi foto toraks, melainkan catatan non-radiologi seperti status/kondisi pasien, penolakan pemeriksaan, pemeriksaan tidak dilakukan, status pengobatan/terapi, atau catatan administratif.\nAturan: tandai "artefak" HANYA bila tidak ada deskripsi foto sama sekali. Jika ragu, pilih "radiologi".\nBila "artefak", isi semua field lain dengan nilai default ("tidak").\n\nBila "radiologi", isi:\n\nimp_tb (impresi TB, pilih SATU). Tentukan HANYA dari kata pada kalimat kesan/impresi. JANGAN menyimpulkan aktivitas dari pola atau lokasi temuan; bila kata aktivitas tidak tertulis, jangan mengarang.\n- "aktif"   : tertulis kata "aktif" (bila tertulis "aktif", pilih aktif walau ada kata "lama").\n- "suspek"  : TB dinyatakan ragu/kemungkinan (mis. suspek/curiga/DD TB).\n- "inaktif" : tertulis lama/bekas/post/scar TANPA kata "aktif".\n- "tidak"   : tidak ada pernyataan impresi TB, atau TB disingkirkan; termasuk bila hanya ada temuan tanpa pernyataan aktivitas TB.\n\nTemuan radiografik (masing-masing "ada"/"tidak"): infiltrat, nodul, kalsifikasi, fibrotik, kavitas.\n- "ada" jika disebut ada; "tidak" jika tidak disebut ATAU dinegasi ("tidak tampak nodul" -> nodul="tidak").\n- Temuan dinilai apa adanya; adanya temuan TIDAK otomatis berarti TB.\n\nkardiomegali ("ada"/"tidak"): "ada" bila jantung membesar / kardiomegali / CTR meningkat disebut.\n\nField "alasan": tulis SINGKAT kutipan/frasa dasar penilaian, SEBELUM label. Jawab HANYA JSON sesuai skema.'

USER_TEMPLATE = 'Catatan:\n"""\n{teks}\n"""'

SCHEMA = {
    "type": "object",
    "properties": {
        "alasan": {
            "type": "string"
        },
        "is_radiologi": {
            "type": "string",
            "enum": [
                "radiologi",
                "artefak"
            ]
        },
        "imp_tb": {
            "type": "string",
            "enum": [
                "aktif",
                "suspek",
                "inaktif",
                "tidak"
            ]
        },
        "infiltrat": {
            "type": "string",
            "enum": [
                "ada",
                "tidak"
            ]
        },
        "nodul": {
            "type": "string",
            "enum": [
                "ada",
                "tidak"
            ]
        },
        "kalsifikasi": {
            "type": "string",
            "enum": [
                "ada",
                "tidak"
            ]
        },
        "fibrotik": {
            "type": "string",
            "enum": [
                "ada",
                "tidak"
            ]
        },
        "kavitas": {
            "type": "string",
            "enum": [
                "ada",
                "tidak"
            ]
        },
        "kardiomegali": {
            "type": "string",
            "enum": [
                "ada",
                "tidak"
            ]
        }
    },
    "required": [
        "alasan",
        "is_radiologi",
        "imp_tb",
        "infiltrat",
        "nodul",
        "kalsifikasi",
        "fibrotik",
        "kavitas",
        "kardiomegali"
    ]
}

# One-shot example (synthetic, frozen, NOT from the evaluation corpus).
ONESHOT_TEXT = 'TB aktif. Tampak infiltrat dan nodul di apeks kanan, tanpa fibrosis maupun kavitas. Jantung normal.'
ONESHOT_JSON = {
    "alasan": "kesan menyebut 'TB aktif'; tampak infiltrat dan nodul; fibrosis dan kavitas dinegasi ('tanpa'); jantung normal",
    "is_radiologi": "radiologi",
    "imp_tb": "aktif",
    "infiltrat": "ada",
    "nodul": "ada",
    "kalsifikasi": "tidak",
    "fibrotik": "tidak",
    "kavitas": "tidak",
    "kardiomegali": "tidak"
}

# ---- 7. PROMPT HASHES (reproducibility fingerprint) --------------------
PROMPT_HASH_ZERO = hashlib.sha256(
    (SYSTEM_PROMPT + USER_TEMPLATE + json.dumps(SCHEMA, sort_keys=True)).encode()
).hexdigest()[:16]

PROMPT_HASH_ONESHOT = hashlib.sha256(
    (SYSTEM_PROMPT + USER_TEMPLATE + json.dumps(SCHEMA, sort_keys=True)
     + ONESHOT_TEXT + json.dumps(ONESHOT_JSON, sort_keys=True)).encode()
).hexdigest()[:16]

# Guard: these MUST match the frozen conference values. If an edit changes
# the prompt, these asserts fail so you notice before running.
assert PROMPT_HASH_ZERO == "1b432dfeb369b503", (
    f"Zero-shot prompt changed! hash={PROMPT_HASH_ZERO}, expected 1b432dfeb369b503")
assert PROMPT_HASH_ONESHOT == "195828bed5eab4c3", (
    f"One-shot prompt changed! hash={PROMPT_HASH_ONESHOT}, expected 195828bed5eab4c3")
