# ============================================================
# LLM-Tb-08_merge_predictions.py — combine the per-model checkpoint files.
# Auto-scans the active site folder and merges:
#   pred_zeroshot_*.xlsx -> LLM_predictions.xlsx        (all models, zero-shot)
#   pred_oneshot_*.xlsx  -> LLM_predictions_oneshot.xlsx (all models, one-shot)
# LLM-Tb-09 (evaluation) reads these merged files.
#
# HOW TO RUN: after running LLM-Tb-04 (and optionally 05) for the models you
# want, set SITE in config.py and click Run.
# ============================================================

import glob
import os

import pandas as pd

import config


def merge(condition, out_name):
    pattern = config.out_path(f"pred_{condition}_*.xlsx")
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"No {condition} files found ({pattern}) — skipped.")
        return
    preds, metas = [], []
    for f in files:
        preds.append(pd.read_excel(f, sheet_name='Predictions'))
        try:
            metas.append(pd.read_excel(f, sheet_name='RunMetadata'))
        except Exception:
            pass
    df = pd.concat(preds, ignore_index=True)
    out = config.out_path(out_name)
    with pd.ExcelWriter(out, engine='openpyxl') as w:
        df.to_excel(w, sheet_name='Predictions', index=False)
        if metas:
            pd.concat(metas, ignore_index=True).to_excel(
                w, sheet_name='RunMetadata', index=False)
    models = sorted(df['model'].unique())
    print(f"{condition}: merged {len(files)} files, {len(df)} rows, "
          f"models={models}\n  -> {out}")


def main():
    print(f"Site: {config.SITE}")
    merge('zeroshot', config.F_LLM_ZERO)
    merge('oneshot', config.F_LLM_ONE)


if __name__ == '__main__':
    main()
