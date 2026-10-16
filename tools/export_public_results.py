# tools/export_public_results.py
# Builds the aggregate results shared in the online data repository.
# Only summary sheets are copied; sheets and columns that can contain report text,
# model rationales, or annotator comments are excluded.
# Run from the repository root after all analysis scripts:  python tools/export_public_results.py
import os, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import config  # noqa: E402

SITES = ["sleman", "yogya_full", "yogya_kesan"]
# (file name, sheets to copy)
PER_SITE = [
    (config.F_EVAL, ["Metrik_primer_macroF1", "Metrik_klinis_sens_spec",
                     "is_radiologi_deskriptif", "IAA_antar_anotator"]),
    ("Table_dataset_summary.xlsx", ["DatasetSummary"]),
    ("Analysis_explicit_implicit.xlsx", ["StrataCounts", "SensitivityByStratum"]),
    ("Analysis_rowlevel.xlsx", None),          # None = all sheets
    ("Determinism_check.xlsx", ["Summary", "Overall"]),
]
TEXT_LIKE = ("teks", "text", "alasan", "keterangan", "catatan", "rationale", "comment")


def clean(df):
    keep = [c for c in df.columns if not any(k in str(c).lower() for k in TEXT_LIKE)]
    return df[keep]


def copy_sheets(path, sheets, writer, prefix):
    if not os.path.exists(path):
        print("  missing (skipped):", path)
        return
    book = pd.read_excel(path, sheet_name=None)
    for name, df in book.items():
        if sheets is not None and name not in sheets:
            continue
        clean(df).to_excel(writer, sheet_name=f"{prefix}{name}"[:31], index=False)


out_dir = os.path.join(ROOT, "results")
os.makedirs(out_dir, exist_ok=True)

for site in SITES:
    out = os.path.join(out_dir, f"{site}_results.xlsx")
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        for fname, sheets in PER_SITE:
            short = {"Evaluasi_hasil.xlsx": "", "Table_dataset_summary.xlsx": "summ_",
                     "Analysis_explicit_implicit.xlsx": "expl_", "Analysis_rowlevel.xlsx": "row_",
                     "Determinism_check.xlsx": "det_"}.get(fname, "")
            copy_sheets(config.out_path(fname, site), sheets, w, short)
    print("written:", out)

contr = os.path.join(config.BASE_DIR, "comparison", "Paired_contrasts.xlsx")
out = os.path.join(out_dir, "paired_contrasts.xlsx")
with pd.ExcelWriter(out, engine="openpyxl") as w:
    copy_sheets(contr, ["AllContrasts", "PostHoc_TB_binary", "Notes"], w, "")
print("written:", out)
print("Open each file once before uploading and confirm that no report text is present.")
