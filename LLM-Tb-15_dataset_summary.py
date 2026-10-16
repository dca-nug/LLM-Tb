# ============================================================
# LLM-Tb-15_dataset_summary.py  (addresses reviewer request for a
# consolidated dataset table: sample size, class distribution, prevalence,
# and statistical power per label.)
# Reads the consensus ground truth exported by LLM-Tb-09.
#
# HOW TO RUN: after LLM-Tb-09, set SITE in config.py, click Run.
# Output -> Table_dataset_summary.xlsx in the site folder.
# ============================================================

import numpy as np
import pandas as pd

import config

OUT = config.out_path('Table_dataset_summary.xlsx')

NOMINAL = {
    'is_radiologi': ['radiologi', 'artefak'],
    'imp_tb':       ['aktif', 'suspek', 'inaktif', 'tidak'],
}
POSITIVE = {**{l: 'ada' for l in config.FINDING_COLS}, 'kardiomegali': 'ada', 'imp_tb': 'aktif'}


def _norm(v):
    return np.nan if pd.isna(v) else str(v).strip().lower()


def main():
    gt = pd.read_excel(config.out_path(config.F_EVAL), sheet_name='GroundTruth').set_index('ID_unik')
    iaa = (pd.read_excel(config.out_path(config.F_EVAL), sheet_name='IAA_antar_anotator')
             .set_index('label')['kappa'])

    # labels other than report type are evaluated on radiologic texts only (same as LLM-Tb-09)
    rad = gt.index[gt['is_radiologi'].map(_norm) == 'radiologi'] if 'is_radiologi' in gt.columns else gt.index

    rows = []
    for label in config.LABEL_COLS:
        if label not in gt.columns:
            continue
        src = gt[label] if label == 'is_radiologi' else gt.loc[rad, label]
        col = src.map(_norm).dropna()
        n = len(col)
        classes = NOMINAL.get(label, ['ada', 'tidak'])
        counts = {c: int((col == c).sum()) for c in classes}
        present = [v for v in counts.values() if v > 0]
        evaluable = len(present) >= 2
        minority = min(present) if present else 0
        powered = evaluable and minority >= config.POWER_THRESHOLD
        status = ('yes' if powered else
                  'not evaluable (single class)' if not evaluable else 'no (descriptive)')

        pos = POSITIVE.get(label)
        prevalence = round(counts.get(pos, 0) / n, 3) if (pos and n) else np.nan
        k = iaa.get(label, np.nan)

        rows.append({
            'label': config.LABEL_EN.get(label, label),
            'label_internal': label,
            'n_evaluated': n,
            'class_distribution': '; '.join(f'{c}={counts[c]}' for c in classes),
            'positive_class': pos if pos else '',
            'n_positive': counts.get(pos, '') if pos else '',
            'prevalence': prevalence,
            'minority_class_n': minority,
            'powered_for_CI': status,
            'kappa_before_consensus': round(k, 2) if pd.notna(k) else 'not calculable',
        })

    df = pd.DataFrame(rows)
    print('=' * 70)
    print(f'DATASET SUMMARY — site: {config.SITE}')
    print('=' * 70)
    print(df.to_string(index=False))

    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        df.to_excel(w, sheet_name='DatasetSummary', index=False)
        pd.DataFrame([
            {'note': f'Power threshold (minority class) = {config.POWER_THRESHOLD}'},
            {'note': 'is_radiologi evaluated on all texts; other labels on '
                     'texts with a radiologic reference label.'},
            {'note': 'prevalence = positive class / n_evaluated.'},
            {'note': 'A label with only one class in the reference is not evaluable.'},
        ]).to_excel(w, sheet_name='Notes', index=False)
    print(f'\nSaved: {OUT}')


if __name__ == '__main__':
    main()
