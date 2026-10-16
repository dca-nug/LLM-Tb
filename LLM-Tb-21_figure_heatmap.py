# ============================================================
# LLM-Tb-21_figure_heatmap.py
# Zero-shot macro-F1 per model and label at both sites (Figure 2).
# Reads Evaluasi_hasil.xlsx of sleman, yogya_full and yogya_kesan
# (output of LLM-Tb-09). Values rounded half-up to 2 decimals.
# Labels without CI (minority class < POWER_THRESHOLD) are marked with a
# dagger and set in italics.
# Palette: single-hue blue, light -> dark (readable with colour-vision
# deficiency and in greyscale).
# Output -> <BASE_DIR>/comparison/Figure2_heatmap.(png|pdf|tif)
# ============================================================
import os
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import config

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5})

SITES = {"A": "sleman", "B full": "yogya_full", "B impression": "yogya_kesan"}
MODELS = [("gemma2_generik", "Gemma 2 9B"), ("sahabat_gemma", "Sahabat-AI Gemma 2 9B"),
          ("gemma4_generik", "Gemma 4 12B"), ("llama3_generik", "Llama 3 8B"),
          ("sahabat_llama", "Sahabat-AI Llama 3 8B"), ("llama31_generik", "Llama 3.1 8B"),
          ("qwen25", "Qwen2.5 7B"), ("qwen35", "Qwen3.5 9B")]
COLS = [("A", "infiltrat", "Infiltrate"), ("A", "fibrotik", "Fibrosis"), ("A", "kavitas", "Cavity"),
        ("A", "kardiomegali", "Cardiomegaly"), ("A", "imp_tb", "Tuberculosis impression"),
        ("B full", "infiltrat", "Infiltrate"), ("B full", "kardiomegali", "Cardiomegaly"),
        ("B full", "imp_tb", "Tuberculosis impression"),
        ("B impression", "infiltrat", "Infiltrate"), ("B impression", "kardiomegali", "Cardiomegaly"),
        ("B impression", "imp_tb", "Tuberculosis impression")]
GROUPS = [(0, 4, "Site A"), (5, 7, "Site B\nfull reports"), (8, 10, "Site B\nimpression sections")]

CMAP = LinearSegmentedColormap.from_list("softblue", ["#fbfdff", "#dbe8f5", "#a9c8e6", "#76a5d3"])


def r2(x):
    return str(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def main():
    ev = {k: pd.read_excel(config.out_path(config.F_EVAL, s), sheet_name="Metrik_primer_macroF1")
          for k, s in SITES.items()}
    V = np.full((len(MODELS), len(COLS)), np.nan)
    P = np.zeros_like(V, dtype=bool)
    for j, (site, lab, _) in enumerate(COLS):
        m = ev[site]
        m = m[(m.label == lab) & m.sistem.str.endswith("_zs")].set_index("sistem")
        for i, (tag, _) in enumerate(MODELS):
            V[i, j] = m.loc[f"{tag}_zs", "macro_F1"]
            P[i, j] = bool(m.loc[f"{tag}_zs", "powered"])

    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    im = ax.imshow(V, cmap=CMAP, vmin=0, vmax=1, aspect="auto")
    for i in range(V.shape[0]):
        for j in range(V.shape[1]):
            txt = r2(V[i, j]) + ("" if P[i, j] else "\u2020")
            ax.text(j, i, txt, ha="center", va="center", fontsize=7.8,
                    color="#1a1a1a",
                    style="normal" if P[i, j] else "italic")

    ax.set_xticks(np.arange(-0.5, len(COLS)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(MODELS)), minor=True)
    ax.grid(which="minor", color="white", lw=0.8)
    for y in (2.5, 5.5):
        ax.axhline(y, color="white", lw=3)
    for x in (4.5, 7.5):
        ax.axvline(x, color="white", lw=3)

    ax.set_yticks(range(len(MODELS)))
    ax.set_yticklabels([d for _, d in MODELS])
    ax.set_xticks(range(len(COLS)))
    ax.set_xticklabels([c[2] for c in COLS], rotation=45, ha="right")
    for x0, x1, t in GROUPS:
        ax.text((x0 + x1) / 2, -0.7, t, ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    ax.tick_params(which="both", length=0)
    for s in ax.spines.values():
        s.set_visible(False)

    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Macro F1 score")
    cb.outline.set_visible(False)
    fig.tight_layout()

    out = os.path.join(config.BASE_DIR, "comparison")
    os.makedirs(out, exist_ok=True)
    fig.savefig(os.path.join(out, "Figure2_heatmap.png"), dpi=300)
    fig.savefig(os.path.join(out, "Figure2_heatmap.pdf"))
    fig.savefig(os.path.join(out, "Figure2_heatmap.tif"), dpi=1200,
                pil_kwargs={"compression": "tiff_lzw"})
    print("Saved to", out)


if __name__ == "__main__":
    main()
