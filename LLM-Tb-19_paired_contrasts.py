# ============================================================
# LLM-Tb-19_paired_contrasts.py
# Paired comparison of two models on the SAME texts:
#   delta = macro-F1(model_a) - macro-F1(model_b)
# with a paired percentile bootstrap 95% CI and a two-sided bootstrap P value.
#
# Uses the same metric definitions as LLM-Tb-09 (macro-F1 over classes,
# classes absent from both reference and prediction are dropped, missing
# predictions counted as wrong, labels other than report type evaluated on
# texts with a radiologic reference label).
#
# A CI/P value is reported only when the label is "powered" at that site
# (>= 2 classes in the reference and minority class >= POWER_THRESHOLD).
# Otherwise the point estimate of delta is reported as descriptive.
#
# Contrasts come from config.CONTRASTS (family, type, model_a, model_b).
#
# HOW TO RUN: after LLM-Tb-09 has been run for every site, click Run
# (config.SITE is ignored). Output -> <BASE_DIR>/comparison/Paired_contrasts.xlsx
# ============================================================

import os
import numpy as np
import pandas as pd

import config

SITES = ["sleman", "yogya_full", "yogya_kesan"]
CONDITIONS = {"zs": config.F_LLM_ZERO, "os": config.F_LLM_ONE}
LABELS = ["imp_tb", "infiltrat", "nodul", "kalsifikasi", "fibrotik", "kavitas", "kardiomegali"]
CLASSES = {"imp_tb": ["aktif", "suspek", "inaktif", "tidak"]}   # others: ada/tidak
N_BOOT = 10000          # more resamples than LLM-Tb-09 so P < .001 can be resolved
SEED = getattr(config, "SEED", 42)
POWER_THRESHOLD = getattr(config, "POWER_THRESHOLD", 10)

DEFAULT_CONTRASTS = [
    ("Gemma", "adaptation", "sahabat_gemma",   "gemma2_generik"),
    ("Gemma", "version",    "gemma4_generik",  "gemma2_generik"),
    ("Gemma", "trade-off",  "sahabat_gemma",   "gemma4_generik"),
    ("Llama", "adaptation", "sahabat_llama",   "llama3_generik"),
    ("Llama", "version",    "llama31_generik", "llama3_generik"),
    ("Llama", "trade-off",  "sahabat_llama",   "llama31_generik"),
    ("Qwen",  "version",    "qwen35",          "qwen25"),
]
CONTRASTS = getattr(config, "CONTRASTS", DEFAULT_CONTRASTS)


def _norm(v):
    return np.nan if pd.isna(v) else str(v).strip().lower()


# ---- metrics: identical logic to LLM-Tb-09 ----
def f1_per_class(gt, pred, cls):
    tp = np.sum((gt == cls) & (pred == cls))
    fp = np.sum((gt != cls) & (pred == cls))
    fn = np.sum((gt == cls) & (pred != cls))
    if tp == 0 and (fp > 0 or fn > 0):
        return 0.0
    if tp == 0 and fp == 0 and fn == 0:
        return np.nan                      # class absent from both
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0


def macro_f1(gt, pred, classes):
    fs = [f1_per_class(gt, pred, c) for c in classes]
    fs = [f for f in fs if not np.isnan(f)]
    return float(np.mean(fs)) if fs else np.nan


def load_gt(site):
    gt = pd.read_excel(config.out_path(config.F_EVAL, site), sheet_name="GroundTruth")
    gt = gt.set_index("ID_unik")
    for c in gt.columns:
        gt[c] = gt[c].map(_norm)
    return gt


def load_pred(site, fname):
    path = config.out_path(fname, site)
    if not os.path.exists(path):
        raise SystemExit(f"STOP: {path} not found. Run LLM-Tb-08 first.")
    d = pd.read_excel(path, sheet_name="Predictions")
    for c in LABELS:
        if c in d.columns:
            d[c] = d[c].map(_norm)
    return d


def model_frame(pred, model):
    d = pred[pred["model"] == model]
    if d.empty:
        return None
    return d.drop_duplicates("ID_unik").set_index("ID_unik")


def _macro_f1_matrix(G, P, classes):
    """Vectorised macro-F1 for a (resamples x n) matrix; same rules as macro_f1()."""
    fs = []
    for c in classes:
        g, p = (G == c), (P == c)
        tp = (g & p).sum(1); fp = (~g & p).sum(1); fn = (g & ~p).sum(1)
        prec = np.divide(tp, tp + fp, out=np.zeros(len(tp)), where=(tp + fp) > 0)
        rec = np.divide(tp, tp + fn, out=np.zeros(len(tp)), where=(tp + fn) > 0)
        f = np.divide(2 * prec * rec, prec + rec, out=np.zeros(len(tp)), where=(prec + rec) > 0)
        f = np.where((tp == 0) & (fp == 0) & (fn == 0), np.nan, f)   # class absent from both
        fs.append(f)
    return np.nanmean(np.vstack(fs), axis=0)


def paired_delta(gt, pa, pb, classes, rng):
    d_obs = macro_f1(gt, pa, classes) - macro_f1(gt, pb, classes)
    n = len(gt)
    idx = rng.integers(0, n, (N_BOOT, n))      # same resamples for both models
    deltas = _macro_f1_matrix(gt[idx], pa[idx], classes) - _macro_f1_matrix(gt[idx], pb[idx], classes)
    deltas = deltas[~np.isnan(deltas)]
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    p = 2 * min(np.mean(deltas <= 0), np.mean(deltas >= 0))
    return d_obs, lo, hi, min(p, 1.0)


# Post hoc: tuberculosis impression grouped into two classes (two groupings, both reported)
TB_BINARY = {
    "active_or_suspected_vs_rest": ({"aktif", "suspek"}, {"inaktif", "tidak"}),
    "active_vs_rest":              ({"aktif"}, {"suspek", "inaktif", "tidak"}),
}


def _binarize(series, pos, neg):
    return series.map(lambda v: "pos" if v in pos else ("neg" if v in neg else "__NOPRED__"))


def tb_binary_rows(site, cond, gt_all, rad, pred):
    out = []
    for grouping, (pos, neg) in TB_BINARY.items():
        g = _binarize(gt_all.loc[rad, "imp_tb"].dropna(), pos, neg)
        ids = g.index
        gt = np.asarray(g.to_numpy(), dtype=object)
        for family, ctype, ma, mb in CONTRASTS:
            A, B = model_frame(pred, ma), model_frame(pred, mb)
            if A is None or B is None:
                continue
            pa = np.asarray(_binarize(A["imp_tb"].reindex(ids), pos, neg).to_numpy(), dtype=object)
            pb = np.asarray(_binarize(B["imp_tb"].reindex(ids), pos, neg).to_numpy(), dtype=object)
            minority = int(min(np.sum(gt == "pos"), np.sum(gt == "neg")))
            powered = minority >= POWER_THRESHOLD
            f_a, f_b = macro_f1(gt, pa, ["pos", "neg"]), macro_f1(gt, pb, ["pos", "neg"])
            rec = dict(site=site, condition=cond, grouping=grouping, family=family, contrast=ctype,
                       model_a=ma, model_b=mb, n=len(gt), n_positive=int(np.sum(gt == "pos")),
                       minority_n=minority, powered=powered,
                       macroF1_a=round(f_a, 3), macroF1_b=round(f_b, 3), delta=round(f_a - f_b, 3),
                       ci_low=np.nan, ci_high=np.nan, p_value=np.nan)
            if powered:
                d, lo, hi, p = paired_delta(gt, pa, pb, ["pos", "neg"], np.random.default_rng(SEED))
                rec.update(ci_low=round(lo, 3), ci_high=round(hi, 3), p_value=round(p, 3))
            out.append(rec)
    return out


def main():
    rows, tb_rows = [], []
    for site in SITES:
        gt_all = load_gt(site)
        rad = gt_all.index[gt_all["is_radiologi"] == "radiologi"]
        for cond, fname in CONDITIONS.items():
            pred = load_pred(site, fname)
            tb_rows += tb_binary_rows(site, cond, gt_all, rad, pred)
            for family, ctype, ma, mb in CONTRASTS:
                A, B = model_frame(pred, ma), model_frame(pred, mb)
                if A is None or B is None:
                    print(f"skip {site}/{cond}: {ma} or {mb} not in predictions")
                    continue
                for label in LABELS:
                    classes = CLASSES.get(label, ["ada", "tidak"])
                    g = gt_all.loc[rad, label].dropna()
                    ids = g.index
                    gt = np.asarray(g.to_numpy(), dtype=object)
                    pa = np.asarray(A[label].reindex(ids).fillna("__NOPRED__").to_numpy(), dtype=object)
                    pb = np.asarray(B[label].reindex(ids).fillna("__NOPRED__").to_numpy(), dtype=object)

                    present = [c for c in classes if np.sum(gt == c) > 0]
                    minority = min([int(np.sum(gt == c)) for c in present], default=0)
                    evaluable = len(present) >= 2
                    powered = evaluable and minority >= POWER_THRESHOLD

                    f_a = macro_f1(gt, pa, classes) if evaluable else np.nan
                    f_b = macro_f1(gt, pb, classes) if evaluable else np.nan
                    rec = dict(site=site, condition=cond, family=family, contrast=ctype,
                               model_a=ma, model_b=mb, label=label, n=len(gt),
                               minority_n=minority, evaluable=evaluable, powered=powered,
                               macroF1_a=round(f_a, 3) if evaluable else np.nan,
                               macroF1_b=round(f_b, 3) if evaluable else np.nan,
                               delta=round(f_a - f_b, 3) if evaluable else np.nan,
                               ci_low=np.nan, ci_high=np.nan, p_value=np.nan,
                               n_texts_differ=int(np.sum(pa != pb)))
                    if powered:
                        rng = np.random.default_rng(SEED)
                        d, lo, hi, p = paired_delta(gt, pa, pb, classes, rng)
                        rec.update(ci_low=round(lo, 3), ci_high=round(hi, 3), p_value=round(p, 3))
                    rows.append(rec)

    df = pd.DataFrame(rows)
    out_dir = os.path.join(config.BASE_DIR, "comparison")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "Paired_contrasts.xlsx")
    hyp = df[(df.contrast == "adaptation") & (df.condition == "zs") & df.powered]
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="AllContrasts", index=False)
        hyp.to_excel(w, sheet_name="Hypothesis_adaptation_zs", index=False)
        pd.DataFrame(tb_rows).to_excel(w, sheet_name="PostHoc_TB_binary", index=False)
        pd.DataFrame([
            {"item": "delta", "value": "macro-F1(model_a) - macro-F1(model_b), same texts"},
            {"item": "bootstrap", "value": f"paired percentile, {N_BOOT} resamples of unique texts, seed {SEED}"},
            {"item": "P value", "value": "2 x min(share of deltas <= 0, share >= 0)"},
            {"item": "powered", "value": f">= 2 reference classes and minority class >= {POWER_THRESHOLD}"},
            {"item": "texts", "value": "texts with a radiologic reference label"},
            {"item": "PostHoc_TB_binary", "value": "post hoc; tuberculosis impression grouped two ways "
                                                   "(active or suspected vs inactive or none; active vs all others)"},
        ]).to_excel(w, sheet_name="Notes", index=False)
    print(df[df.powered].to_string(index=False))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
