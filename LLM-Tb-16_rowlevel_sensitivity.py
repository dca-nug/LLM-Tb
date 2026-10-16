# ============================================================
# LLM-Tb-16_rowlevel_sensitivity.py  (addresses reviewer concern that
# de-duplication distorts clinical prevalence.)
# Propagates the unique-text ground truth and system predictions back to ALL
# original report rows via TB_peta_baris.xlsx, then reports row-level
# prevalence and sensitivity. This reflects real-world frequency of each
# finding, complementing the primary unique-text analysis.
#
# Reported DESCRIPTIVELY. Rows are not independent (many map to one unique
# text), so no confidence intervals are given here; any inference must cluster
# at the unique-text level (as the primary analysis does).
#
# HOW TO RUN: after LLM-Tb-09, set SITE in config.py, click Run.
# Output -> Analysis_rowlevel.xlsx in the site folder.
# ============================================================

import numpy as np
import pandas as pd

import config

OUT = config.out_path('Analysis_rowlevel.xlsx')
POSITIVE = {**{l: 'ada' for l in config.FINDING_COLS}, 'kardiomegali': 'ada', 'imp_tb': 'aktif'}


def _norm(v):
    return np.nan if pd.isna(v) else str(v).strip().lower()


def main():
    peta = pd.read_excel(config.out_path(config.F_MAP))        # ID_unik, teks (per row)
    gt = pd.read_excel(config.out_path(config.F_EVAL), sheet_name='GroundTruth').set_index('ID_unik')
    zs = pd.read_excel(config.out_path(config.F_LLM_ZERO), sheet_name='Predictions')
    rule = pd.read_excel(config.out_path(config.F_RULE), sheet_name='PredUnik')
    rule = rule.rename(columns={'find_infiltrat': 'infiltrat', 'find_nodul': 'nodul',
                                'find_kalsifikasi': 'kalsifikasi', 'find_fibrotik': 'fibrotik',
                                'find_kavitas': 'kavitas', 'card_kardiomegali': 'kardiomegali'}
                       ).set_index('ID_unik')

    systems = {'rule_based': rule}
    for m in sorted(zs['model'].unique()):
        systems[f'{m}_zs'] = zs[zs['model'] == m].set_index('ID_unik')

    n_rows = len(peta)
    n_unique = peta['ID_unik'].nunique()

    # row-level prevalence (GT propagated)
    prev_rows = []
    eval_labels = [l for l in config.LABEL_COLS if l in gt.columns and l != 'is_radiologi']
    for label in eval_labels:
        gmap = gt[label].map(_norm)
        row_vals = peta['ID_unik'].map(gmap)
        pos = POSITIVE.get(label)
        n_valid = int(row_vals.notna().sum())
        n_pos = int((row_vals == pos).sum()) if pos else np.nan
        prev_rows.append({
            'label': config.LABEL_EN.get(label, label),
            'positive_class': pos,
            'n_rows_valid': n_valid,
            'n_positive_rows': n_pos,
            'row_level_prevalence': round(n_pos / n_valid, 3) if (pos and n_valid) else np.nan,
        })
    df_prev = pd.DataFrame(prev_rows)

    # row-level sensitivity per system (binarized to positive class)
    sens_rows = []
    for label in eval_labels:
        pos = POSITIVE.get(label)
        if not pos:
            continue
        gmap = gt[label].map(_norm)
        row_gt = peta['ID_unik'].map(gmap)
        pos_mask = row_gt == pos
        n_pos = int(pos_mask.sum())
        for sname, S in systems.items():
            if label not in S.columns:
                continue
            smap = S[label].map(_norm)
            row_pred = peta['ID_unik'].map(smap)
            tp = int(((row_pred == pos) & pos_mask).sum())
            sens = tp / n_pos if n_pos else np.nan
            sens_rows.append({
                'label': config.LABEL_EN.get(label, label), 'system': sname,
                'n_positive_rows': n_pos, 'TP_rows': tp,
                'row_level_sensitivity': round(sens, 3) if not np.isnan(sens) else np.nan,
            })
    df_sens = pd.DataFrame(sens_rows)

    print('=' * 60)
    print(f'ROW-LEVEL (sensitivity analysis) — site: {config.SITE}')
    print(f'Rows: {n_rows:,} mapped to {n_unique} unique texts')
    print('=' * 60)
    print(df_prev.to_string(index=False))

    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        df_prev.to_excel(w, sheet_name='RowLevelPrevalence', index=False)
        df_sens.to_excel(w, sheet_name='RowLevelSensitivity', index=False)
        pd.DataFrame([
            {'note': f'{n_rows} rows mapped to {n_unique} unique texts.'},
            {'note': 'Descriptive only; rows are not independent, so no CIs. '
                     'Primary inferential analysis is at the unique-text level.'},
        ]).to_excel(w, sheet_name='Notes', index=False)
    print(f'\nSaved: {OUT}')


if __name__ == '__main__':
    main()
