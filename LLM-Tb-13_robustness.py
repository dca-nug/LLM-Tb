# ============================================================
# LLM-Tb-13_robustness.py  (analysis #2)
# Tests whether systems are stable under meaning-preserving text variation.
# Directly probes the "rule-based is brittle, LLM is flexible" theme.
#
# TWO STEPS:
#   MODE = "generate": makes perturbed variants of the unique texts (typos,
#          synonyms, sentence reorder) that keep the clinical meaning, and
#          writes them as a parallel unique-texts file. A radiologist should
#          confirm the variants keep the same meaning before use.
#   MODE = "compare": after you have predictions for BOTH the original and the
#          perturbed texts, computes the flip rate (share of label decisions
#          that changed) per system. Higher flip rate = less robust.
#
# Because the perturbed set is synthetic, treat this as a controlled robustness
# probe, not a clinical result.
#
# HOW TO RUN (generate): set MODE="generate", SITE in config, click Run.
#   -> writes TB_teks_unik_perturbed.xlsx. Then run the rule-based and LLM
#      arms on it (see note printed at the end), saving predictions with a
#      "_pert" filename.
# HOW TO RUN (compare): set MODE="compare", click Run.
# ============================================================

import glob
import os
import re

import numpy as np
import pandas as pd

import config

MODE = "generate"        # "generate" or "compare"
N_SAMPLE = 40            # how many texts to perturb (subset keeps it cheap)
SEED = 42

OUT_PERT = config.out_path('TB_teks_unik_perturbed.xlsx')

# meaning-preserving synonym swaps (surface form -> alternative spelling)
SYNONYMS = [('kavitas', 'cavity'), ('infiltrat', 'infiltrate'),
            ('fibrosis', 'fibrotik'), ('nodul', 'nodule'),
            ('kardiomegali', 'cardiomegaly'), ('kalsifikasi', 'calcification')]
# common typos (insert once)
TYPO = [('infiltrat', 'infiltart'), ('kardiomegali', 'kardiomegly'),
        ('kalsifikasi', 'kalsifiaksi'), ('fibrosis', 'fibrossis')]


def perturb(text, rng):
    t = str(text)
    kind = rng.choice(['synonym', 'typo', 'reorder'])
    if kind == 'synonym':
        for a, b in SYNONYMS:
            if a in t.lower():
                t = re.sub(a, b, t, flags=re.IGNORECASE); break
    elif kind == 'typo':
        for a, b in TYPO:
            if a in t.lower():
                t = re.sub(a, b, t, flags=re.IGNORECASE); break
    else:  # reorder sentences/clauses split on commas
        parts = [p.strip() for p in t.split(',') if p.strip()]
        if len(parts) > 1:
            rng.shuffle(parts); t = ', '.join(parts)
    return t, kind


def do_generate():
    u = pd.read_excel(config.out_path(config.F_UNIQUE))
    rng = np.random.default_rng(SEED)
    sample = u.sample(min(N_SAMPLE, len(u)), random_state=SEED).reset_index(drop=True)
    out = []
    for _, r in sample.iterrows():
        new_text, kind = perturb(r['teks'], rng)
        out.append({'ID_unik': r['ID_unik'], 'ID_orig': r['ID_unik'],
                    'teks': new_text, 'perturbation': kind,
                    'teks_original': r['teks'], 'n_baris': r.get('n_baris', 1)})
    df = pd.DataFrame(out)
    df.to_excel(OUT_PERT, index=False)
    print(f'Wrote {len(df)} perturbed texts -> {OUT_PERT}')
    print('NEXT: run the rule-based and LLM arms on this file, saving predictions')
    print('  as pred_zeroshot_<model>_pert.xlsx and RuleBased_pred_pert.xlsx')
    print('  (point the arms at TB_teks_unik_perturbed.xlsx). Then set MODE="compare".')
    print('Have a radiologist confirm the variants keep the same meaning first.')


def _norm(v):
    return np.nan if pd.isna(v) else str(v).strip().lower()


def do_compare():
    # original predictions
    orig = pd.read_excel(config.out_path(config.F_LLM_ZERO), sheet_name='Predictions')
    # perturbed predictions (files ending _pert)
    pert_files = glob.glob(config.out_path('pred_zeroshot_*_pert.xlsx'))
    if not pert_files:
        raise SystemExit('No *_pert prediction files. Generate + run the arms first.')
    pert = pd.concat([pd.read_excel(f, sheet_name='Predictions') for f in pert_files],
                     ignore_index=True)

    rows = []
    for m in sorted(set(orig['model']) & set(pert['model'])):
        o = orig[orig['model'] == m].set_index('ID_unik')
        p = pert[pert['model'] == m].set_index('ID_unik')
        ids = o.index.intersection(p.index)
        total = flips = 0
        for l in config.LABEL_COLS:
            if l in o.columns and l in p.columns:
                a = o.loc[ids, l].map(_norm); b = p.loc[ids, l].map(_norm)
                total += len(ids); flips += int((a.values != b.values).sum())
        rows.append({'system': f'{m}_zs', 'cells': total, 'flips': flips,
                     'flip_rate': round(flips / total, 3) if total else np.nan})
    df = pd.DataFrame(rows)
    out = config.out_path('Analysis_robustness.xlsx')
    df.to_excel(out, index=False)
    print('=' * 50)
    print(f'ROBUSTNESS (flip rate) — site: {config.SITE}')
    print('=' * 50)
    print(df.to_string(index=False))
    print(f'\nSaved: {out}  (higher flip_rate = less robust)')


def main():
    if MODE == 'generate':
        do_generate()
    elif MODE == 'compare':
        do_compare()
    else:
        raise SystemExit('Set MODE to "generate" or "compare".')


if __name__ == '__main__':
    main()
