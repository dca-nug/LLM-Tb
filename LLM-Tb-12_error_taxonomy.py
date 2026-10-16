# ============================================================
# LLM-Tb-12_error_taxonomy.py  (analysis #5)
# Extracts every case where a system disagrees with the consensus GT and
# pre-categorizes the error with simple heuristics, attaching the LLM's own
# 'alasan' (rationale) so a human can code the final category quickly.
#
# Heuristic categories (a starting point; confirm/adjust by reading):
#   literal_miss   -> GT positive, term present in text, system said absent
#   implicit_miss  -> GT positive, term NOT in text, system said absent
#   hallucination  -> GT absent, term NOT in text, system said present
#   other          -> anything else (review)
#
# The category is a SUGGESTION. Add a 'final_category' column when you read
# the cases; two coders + agreement is ideal.
#
# HOW TO RUN: after LLM-Tb-09, set SITE in config.py, click Run.
# Output -> Analysis_error_taxonomy.xlsx in the site folder.
# ============================================================

import numpy as np
import pandas as pd

import config

OUT = config.out_path('Analysis_error_taxonomy.xlsx')

SURFACE_FORMS = {
    'infiltrat':    ['infiltrat', 'infiltrate', 'infiltrasi'],
    'nodul':        ['nodul', 'nodule', 'noduler'],
    'kalsifikasi':  ['kalsifikasi', 'calcification', 'kalsifik'],
    'fibrotik':     ['fibrotik', 'fibrosis', 'fibro'],
    'kavitas':      ['kavitas', 'kaviti', 'cavitas', 'cavity', 'kaverne'],
    'kardiomegali': ['kardiomegali', 'cardiomegaly', 'ctr', 'jantung membesar'],
}


def _norm(v):
    return np.nan if pd.isna(v) else str(v).strip().lower()


def categorize(label, gt, pred, text):
    forms = SURFACE_FORMS.get(label, [])
    present = any(f in str(text).lower() for f in forms)
    if gt == 'ada' and pred != 'ada':
        return 'literal_miss' if present else 'implicit_miss'
    if gt != 'ada' and pred == 'ada':
        return 'hallucination' if not present else 'other'
    return 'other'


def main():
    eval_path = config.out_path(config.F_EVAL)
    gt = pd.read_excel(eval_path, sheet_name='GroundTruth').set_index('ID_unik')
    texts = pd.read_excel(config.out_path(config.F_UNIQUE)).set_index('ID_unik')['teks']
    zs = pd.read_excel(config.out_path(config.F_LLM_ZERO), sheet_name='Predictions')

    finding_labels = [l for l in SURFACE_FORMS if l in gt.columns]
    rows = []
    for m in sorted(zs['model'].unique()):
        S = zs[zs['model'] == m].set_index('ID_unik')
        alasan = S['alasan'] if 'alasan' in S.columns else pd.Series('', index=S.index)
        for label in finding_labels:
            if label not in S.columns:
                continue
            for i in gt.index:
                if i not in S.index or i not in texts.index:
                    continue
                g = _norm(gt.loc[i, label]); p = _norm(S.loc[i, label])
                if pd.isna(g) or pd.isna(p) or g == p:
                    continue
                rows.append({'model': m, 'label': label, 'ID_unik': i,
                             'GT': g, 'pred': p,
                             'suggested_category': categorize(label, g, p, texts[i]),
                             'rationale_alasan': str(alasan.get(i, ''))[:200],
                             'text': str(texts[i])[:150],
                             'final_category': ''})   # fill by hand
    df = pd.DataFrame(rows)

    print('=' * 60)
    print(f'ERROR TAXONOMY — site: {config.SITE}')
    print('=' * 60)
    if len(df):
        dist = df.groupby(['model', 'suggested_category']).size().reset_index(name='n')
        print(dist.to_string(index=False))
    else:
        print('No errors found (check inputs).')

    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        df.to_excel(w, sheet_name='ErrorCases', index=False)
        if len(df):
            df.groupby(['model', 'suggested_category']).size().reset_index(
                name='n').to_excel(w, sheet_name='Distribution', index=False)
    print(f'\nSaved: {OUT}  (add final_category by reading the cases)')


if __name__ == '__main__':
    main()
