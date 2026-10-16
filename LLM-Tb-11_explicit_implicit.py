# ============================================================
# LLM-Tb-11_explicit_implicit.py  (analysis #4)
# Formalizes the explicit-vs-implicit distinction that is central to the study.
# For each finding label, every GT-positive text is tagged:
#   explicit -> a surface form of the term appears in the text
#   implicit -> GT-positive but no surface form present (inferred from context)
# Then per-system sensitivity is reported separately for the two strata.
# Hypothesis: systems agree on explicit findings and diverge on implicit ones,
# where only the language-adapted model approaches the radiologists' reading.
#
# This is a Sleman-defined framework. The keyword lists are FROZEN here and
# applied unchanged to Solo during external validation.
#
# NOTE: keyword tagging is a proxy. A radiologist should validate a sample of
# the "implicit" tags (the tags are exported for that purpose).
#
# CHANGES (Oct 2026):
#   - 'cardiomegali' (spelling variant) added to the cardiomegaly terms
#   - only texts with a radiologic reference label are analysed
#   - Tags_for_review exports the full text plus empty columns for
#     radiologist validation (tertulis_di_teks / disimpulkan_dari / catatan)
#
# HOW TO RUN: after LLM-Tb-09, set SITE in config.py, click Run.
# Output -> Analysis_explicit_implicit.xlsx in the site folder.
# ============================================================

import numpy as np
import pandas as pd

import config

OUT = config.out_path('Analysis_explicit_implicit.xlsx')

# Surface forms per finding label (frozen; reused across sites).
# Extend cautiously and never after seeing Solo.
SURFACE_FORMS = {
    'infiltrat':    ['infiltrat', 'infiltrate', 'infiltrasi'],
    'nodul':        ['nodul', 'nodule', 'noduler'],
    'kalsifikasi':  ['kalsifikasi', 'calcification', 'kalsifik'],
    'fibrotik':     ['fibrotik', 'fibrosis', 'fibro'],
    'kavitas':      ['kavitas', 'kaviti', 'cavitas', 'cavity', 'kaverne'],
    'kardiomegali': ['kardiomegali', 'cardiomegaly', 'cardiomegali', 'ctr',
                     'jantung membesar', 'pembesaran jantung'],
}
FINDING_LABELS = list(SURFACE_FORMS.keys())


def _norm(v):
    return np.nan if pd.isna(v) else str(v).strip().lower()


def main():
    eval_path = config.out_path(config.F_EVAL)
    gt = pd.read_excel(eval_path, sheet_name='GroundTruth').set_index('ID_unik')
    texts = pd.read_excel(config.out_path(config.F_UNIQUE)).set_index('ID_unik')['teks']
    zs = pd.read_excel(config.out_path(config.F_LLM_ZERO), sheet_name='Predictions')
    rule = pd.read_excel(config.out_path(config.F_RULE), sheet_name='PredUnik')

    rule_map = {'find_infiltrat': 'infiltrat', 'find_nodul': 'nodul',
                'find_kalsifikasi': 'kalsifikasi', 'find_fibrotik': 'fibrotik',
                'find_kavitas': 'kavitas', 'card_kardiomegali': 'kardiomegali'}
    rule = rule.rename(columns=rule_map).set_index('ID_unik')

    # assemble systems: rule_based + each zero-shot model
    systems = {'rule_based': rule}
    for m in sorted(zs['model'].unique()):
        systems[f'{m}_zs'] = zs[zs['model'] == m].set_index('ID_unik')

    def text_has(term_text, forms):
        t = str(term_text).lower()
        return any(f in t for f in forms)

    strata_rows, sens_rows, tag_rows = [], [], []
    for label in FINDING_LABELS:
        if label not in gt.columns:
            continue
        forms = SURFACE_FORMS[label]
        pos_ids = gt.index[(gt[label].map(_norm) == 'ada') &
                           (gt['is_radiologi'].map(_norm) == 'radiologi')]
        # tag each GT-positive text
        expl, impl = [], []
        for i in pos_ids:
            if i not in texts.index:
                continue
            (expl if text_has(texts[i], forms) else impl).append(i)
            tag_rows.append({'label': label, 'ID_unik': i,
                             'stratum': 'explicit' if text_has(texts[i], forms) else 'implicit',
                             'text': str(texts[i]),
                             'tertulis_di_teks': '', 'disimpulkan_dari': '', 'catatan': ''})
        strata_rows.append({'label': label, 'n_positive': len(pos_ids),
                            'n_explicit': len(expl), 'n_implicit': len(impl)})

        # per-system sensitivity within each stratum
        for sname, S in systems.items():
            col = label if label in S.columns else None
            for stratum, id_list in [('explicit', expl), ('implicit', impl)]:
                if not id_list:
                    continue
                common = [i for i in id_list if i in S.index]
                if col is None or not common:
                    sens = np.nan; tp = 0; n = len(common)
                else:
                    pred = S.loc[common, col].map(_norm)
                    tp = int((pred == 'ada').sum()); n = len(common)
                    sens = tp / n if n else np.nan
                sens_rows.append({'label': label, 'system': sname, 'stratum': stratum,
                                  'n': n, 'TP': tp,
                                  'sensitivity': round(sens, 3) if not np.isnan(sens) else np.nan})

    df_strata = pd.DataFrame(strata_rows)
    df_sens = pd.DataFrame(sens_rows)
    df_tags = pd.DataFrame(tag_rows)

    print('=' * 60)
    print(f'EXPLICIT vs IMPLICIT — site: {config.SITE}')
    print('=' * 60)
    print(df_strata.to_string(index=False))
    print('\nSensitivity by stratum (first rows):')
    print(df_sens.head(20).to_string(index=False))

    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        df_strata.to_excel(w, sheet_name='StrataCounts', index=False)
        df_sens.to_excel(w, sheet_name='SensitivityByStratum', index=False)
        df_tags.to_excel(w, sheet_name='Tags_for_review', index=False)
    print(f'\nSaved: {OUT}')
    print('Have a radiologist validate a sample of the "implicit" tags.')


if __name__ == '__main__':
    main()
