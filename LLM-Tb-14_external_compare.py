# ============================================================
# LLM-Tb-14_external_compare.py — compare results across several sites.
# Puts macro-F1 and clinical metrics side by side for every site in SITES,
# with deltas against a reference (development) site. Also computes one
# within-site contrast (FORMAT_CONTRAST): the same external site run on two
# input formats.
#
# Reads each site's Evaluasi_hasil.xlsx (output of LLM-Tb-09). Does NOT re-run
# anything. A site without Evaluasi_hasil.xlsx is SKIPPED with a message,
# not a crash. This matters for yogya_kesan: 09 can only run there if the
# unique KESAN texts were annotated separately. Without that annotation,
# the KESAN-vs-full comparison is done by LLM-Tb-18 (paired, same reports,
# labels from the full-report annotation), not here.
#
# NOTE ON PAIRING: this script compares AGGREGATE metrics, each site with its
# own unit of analysis and its own ground truth. yogya_kesan and yogya_full
# are de-duplicated separately, so their ID_unik values do not refer to the
# same reports. Per-report pairing is in LLM-Tb-18.
#
# HOW TO RUN: check SITES / REFERENCE / FORMAT_CONTRAST below, then click Run
# (config.SITE is ignored). Output -> <BASE_DIR>/comparison/External_comparison.xlsx
# ============================================================

import os

import pandas as pd

import config

# Site keys = folder names under data/ (as used by config.SITE).
SITES = ['sleman', 'yogya_full', 'yogya_kesan']
REFERENCE = 'sleman'                               # development site
FORMAT_CONTRAST = ('yogya_kesan', 'yogya_full')    # (condition A, condition B), same site

OUT_DIR = os.path.join(config.BASE_DIR, 'comparison')


def eval_path(site):
    return os.path.join(config.BASE_DIR, site, config.F_EVAL)


def load_primary(site):
    df = pd.read_excel(eval_path(site), sheet_name='Metrik_primer_macroF1')
    keep = ['label', 'sistem', 'n_eval', 'macro_F1', 'macroF1_CI95', 'powered']
    df = df[[c for c in keep if c in df.columns]].copy()
    df.insert(0, 'site', site)
    return df


def load_clinical(site):
    df = pd.read_excel(eval_path(site), sheet_name='Metrik_klinis_sens_spec')
    keep = ['label', 'sistem', 'n_positif_GT', 'sens', 'spec', 'ppv', 'npv']
    df = df[[c for c in keep if c in df.columns]].copy()
    df.insert(0, 'site', site)
    return df


def wide(df_long, value_cols):
    """One row per (label, system); columns <value>_<site>."""
    w = df_long.pivot_table(index=['label', 'sistem'], columns='site',
                            values=value_cols, aggfunc='first')
    w.columns = [f'{v}_{s}' for v, s in w.columns]
    return w.reset_index()


def add_deltas(w, metric, ref, others):
    for s in others:
        a, b = f'{metric}_{ref}', f'{metric}_{s}'
        if a in w.columns and b in w.columns:
            w[f'delta_{metric}_{s}_vs_{ref}'] = (w[b] - w[a]).round(3)
    return w


def main():
    present, skipped = [], []
    for s in SITES:
        (present if os.path.exists(eval_path(s)) else skipped).append(s)
    for s in skipped:
        print(f"[skip] {s}: {eval_path(s)} not found (run 09 for this site first).")
    if REFERENCE not in present:
        raise SystemExit(f"Reference site '{REFERENCE}' has no {config.F_EVAL}. Run 09 for it first.")
    if len(present) < 2:
        raise SystemExit('Need at least two sites with Evaluasi_hasil.xlsx to compare.')
    os.makedirs(OUT_DIR, exist_ok=True)
    others = [s for s in present if s != REFERENCE]

    prim_long = pd.concat([load_primary(s) for s in present], ignore_index=True)
    clin_long = pd.concat([load_clinical(s) for s in present], ignore_index=True)

    # macro-F1 across sites + deltas vs reference
    prim_w = wide(prim_long, ['macro_F1', 'macroF1_CI95', 'n_eval', 'powered'])
    prim_w = add_deltas(prim_w, 'macro_F1', REFERENCE, others)

    # clinical sensitivity/specificity across sites + deltas vs reference
    clin_w = wide(clin_long, ['sens', 'spec', 'n_positif_GT'])
    clin_w = add_deltas(clin_w, 'sens', REFERENCE, others)
    clin_w = add_deltas(clin_w, 'spec', REFERENCE, others)

    # within-site format contrast, only if both conditions were evaluated
    a, b = FORMAT_CONTRAST
    fmt = None
    if a in present and b in present:
        fmt = prim_w[['label', 'sistem', f'macro_F1_{a}', f'macro_F1_{b}']].copy()
        fmt[f'delta_macro_F1_{b}_vs_{a}'] = (fmt[f'macro_F1_{b}'] - fmt[f'macro_F1_{a}']).round(3)
        fmt_note = f'{b} vs {a} (same site, aggregate, each with its own ground truth)'
    else:
        fmt_note = (f'not computed: {", ".join(x for x in (a, b) if x not in present)} '
                    f'has no evaluation. Use LLM-Tb-18 for the paired KESAN-vs-full comparison.')

    out = os.path.join(OUT_DIR, 'External_comparison.xlsx')
    with pd.ExcelWriter(out, engine='openpyxl') as w:
        prim_w.to_excel(w, sheet_name='macroF1_by_site', index=False)
        clin_w.to_excel(w, sheet_name='clinical_by_site', index=False)
        if fmt is not None:
            fmt.to_excel(w, sheet_name='format_contrast', index=False)
        prim_long.to_excel(w, sheet_name='macroF1_long', index=False)   # for plotting
        clin_long.to_excel(w, sheet_name='clinical_long', index=False)
        pd.DataFrame([
            {'item': 'sites compared', 'value': ', '.join(present)},
            {'item': 'sites skipped (no Evaluasi_hasil)', 'value': ', '.join(skipped) or '(none)'},
            {'item': 'reference (development) site', 'value': REFERENCE},
            {'item': 'format contrast', 'value': fmt_note},
            {'item': 'note', 'value': 'Aggregate comparison only. Per-report pairing is in LLM-Tb-18.'},
        ]).to_excel(w, sheet_name='RunInfo', index=False)

    print('=' * 60)
    print(f'CROSS-SITE COMPARISON: {present} (reference = {REFERENCE})')
    print('=' * 60)
    show = ['label', 'sistem'] + [f'macro_F1_{s}' for s in present]
    print(prim_w[[c for c in show if c in prim_w.columns]].to_string(index=False))
    print(f'\nFormat contrast: {fmt_note}')
    if fmt is not None:
        print(fmt.to_string(index=False))
    print(f'\nSaved: {out}')


if __name__ == '__main__':
    main()