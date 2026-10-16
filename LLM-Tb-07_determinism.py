# ============================================================
# LLM-Tb-07_determinism.py — determinism check (repeat 1 vs repeat 2).
# Scans every pred_repeat_<model>.xlsx in the active site folder and, for
# each model, compares the label predictions of repeat 1 vs repeat 2.
# This measures output stability only; it never touches the ground truth.
#
# HOW TO RUN: after running LLM-Tb-06 for the models you want, set SITE in
# config.py and click Run. Output -> Determinism_check.xlsx in the site folder.
# ============================================================

import glob
import os

import numpy as np
import pandas as pd

import config

OUT = config.out_path("Determinism_check.xlsx")


def _norm(v):
    return np.nan if pd.isna(v) else str(v).strip().lower()


def main():
    pattern = config.out_path("pred_repeat_*.xlsx")
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"No repeat files found: {pattern}\nRun LLM-Tb-06 first.")

    summary_rows, changed_rows = [], []
    for f in files:
        df = pd.read_excel(f, sheet_name='Predictions')
        for l in config.LABEL_COLS:
            if l in df.columns:
                df[l] = df[l].map(_norm)
        reps = sorted(df['repeat'].unique())
        if len(reps) < 2:
            print(f"Skip {os.path.basename(f)} (only {len(reps)} repeat).")
            continue
        r1, r2 = reps[0], reps[1]
        model = df['model'].iloc[0]
        d1 = df[df['repeat'] == r1].set_index('ID_unik')
        d2 = df[df['repeat'] == r2].set_index('ID_unik')
        ids = d1.index.intersection(d2.index)

        total = same = 0
        for l in config.LABEL_COLS:
            if l not in d1.columns or l not in d2.columns:
                continue
            a = d1.loc[ids, l]; b = d2.loc[ids, l]
            eq = (a.values == b.values) | (a.isna().values & b.isna().values)
            total += len(ids); same += int(eq.sum())
            for i, e in zip(ids, eq):
                if not e:
                    changed_rows.append({'model': model, 'ID_unik': i, 'label': l,
                                         f'repeat{r1}': d1.loc[i, l],
                                         f'repeat{r2}': d2.loc[i, l]})
        pct = round(100 * same / total, 2) if total else np.nan
        summary_rows.append({'model': model, 'n_texts': len(ids),
                             'cells_compared': total, 'identical': same,
                             'changed': total - same, 'percent_identical': pct})

    df_sum = pd.DataFrame(summary_rows)
    df_chg = pd.DataFrame(changed_rows) if changed_rows else pd.DataFrame(
        columns=['model', 'ID_unik', 'label', 'repeat1', 'repeat2'])

    tot = df_sum['cells_compared'].sum(); sm = df_sum['identical'].sum()
    overall = round(100 * sm / tot, 2) if tot else np.nan

    print('=' * 60)
    print(f'DETERMINISM CHECK — site: {config.SITE}')
    print('=' * 60)
    print(df_sum.to_string(index=False))
    print(f'\nOVERALL: {sm}/{tot} cells identical = {overall}%')
    print('All identical.' if not len(df_chg) else f'{len(df_chg)} cells changed.')

    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        df_sum.to_excel(w, sheet_name='Summary', index=False)
        df_chg.to_excel(w, sheet_name='ChangedCells', index=False)
        pd.DataFrame([{'metric': 'overall_percent_identical', 'value': overall},
                     {'metric': 'total_cells', 'value': int(tot)}]
                     ).to_excel(w, sheet_name='Overall', index=False)
    print(f'Saved: {OUT}')


if __name__ == '__main__':
    main()
