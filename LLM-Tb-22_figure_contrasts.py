# ============================================================
# LLM-Tb-22_figure_contrasts.py
# Figure 3: paired differences in zero-shot macro-F1 at site A
# (model_a minus model_b, same texts) with paired bootstrap 95% CIs.
# Reads <BASE_DIR>/comparison/Paired_contrasts.xlsx (output of LLM-Tb-19).
# Filled marker = 95% CI excludes 0; open marker = CI includes 0.
# Output -> <BASE_DIR>/comparison/Figure3_contrasts.(png|pdf|tif)
# ============================================================
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import config

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5})
BLUE = "#3f7cb8"

ROWS = [  # (contrast type, family, y label)
    ("adaptation", "Gemma", "Sahabat-AI Gemma 2 vs Gemma 2"),
    ("adaptation", "Llama", "Sahabat-AI Llama 3 vs Llama 3"),
    ("version",    "Gemma", "Gemma 4 vs Gemma 2"),
    ("version",    "Llama", "Llama 3.1 vs Llama 3"),
    ("version",    "Qwen",  "Qwen3.5 vs Qwen2.5"),
    ("trade-off",  "Gemma", "Sahabat-AI Gemma 2 vs Gemma 4"),
    ("trade-off",  "Llama", "Sahabat-AI Llama 3 vs Llama 3.1"),
]
GROUP_TITLE = {"adaptation": "Language adaptation", "version": "Newer version",
               "trade-off": "Adapted vs newer generic"}
PANELS = [("infiltrat", "Infiltrate"), ("fibrotik", "Fibrosis"),
          ("kavitas", "Cavity"), ("kardiomegali", "Cardiomegaly")]


def main():
    path = os.path.join(config.BASE_DIR, "comparison", "Paired_contrasts.xlsx")
    d = pd.read_excel(path, sheet_name="AllContrasts")
    dall = d[(d.condition == "zs") & d.powered]
    d = dall[dall.site == "sleman"]
    dB = dall[(dall.site != "sleman") & (dall.label == "kardiomegali")]

    # y positions with a gap and a header row per contrast type
    ypos, headers, y, prev = {}, [], 0, None
    for ctype, fam, lab in ROWS:
        if ctype != prev:
            if prev is not None:
                y += 0.6
            headers.append((y, GROUP_TITLE[ctype])); y += 1
            prev = ctype
        ypos[(ctype, fam)] = y; y += 1

    fig, axes = plt.subplots(1, 5, figsize=(7.4, 4.3), sharey=True)
    for k, (lab, title) in enumerate(PANELS):
        ax = axes[k]
        sub = d[d.label == lab].set_index(["contrast", "family"])
        ax.axvline(0, color="0.55", lw=0.8, zorder=0)
        for (ctype, fam), yy in ypos.items():
            if (ctype, fam) not in sub.index:
                continue
            r = sub.loc[(ctype, fam)]
            lo, hi, dv = r.ci_low, r.ci_high, r.delta
            sig = (lo > 0) or (hi < 0)
            ax.plot([lo, hi], [yy, yy], color=BLUE, lw=1.3)
            ax.plot(dv, yy, "o", ms=5.5, mec=BLUE, mew=1.3, mfc=BLUE if sig else "white")
        ax.set_xlim(-0.5, 0.5)
        ax.set_xticks([-0.4, 0, 0.4]); ax.set_xticklabels(["\u22120.4", "0", "0.4"])
        ax.set_xticks([-0.2, 0.2], minor=True)
        ax.set_xlabel(title, fontsize=9, fontweight="bold", labelpad=6)
        ax.grid(axis="x", which="both", color="0.92", lw=0.5); ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0)

    # panel 5: cardiomegaly at site B, two report formats offset vertically
    ax = axes[4]
    ax.axvline(0, color="0.55", lw=0.8, zorder=0)
    for site, off, mk in (("yogya_full", -0.17, "o"), ("yogya_kesan", 0.17, "s")):
        sub = dB[dB.site == site].set_index(["contrast", "family"])
        for (ctype, fam), yy in ypos.items():
            if (ctype, fam) not in sub.index:
                continue
            r = sub.loc[(ctype, fam)]
            sig = (r.ci_low > 0) or (r.ci_high < 0)
            ax.plot([r.ci_low, r.ci_high], [yy + off] * 2, color=BLUE, lw=1.1)
            ax.plot(r.delta, yy + off, mk, ms=4.8, mec=BLUE, mew=1.2, mfc=BLUE if sig else "white")
    ax.set_xlim(-0.5, 0.5)
    ax.set_xticks([-0.4, 0, 0.4]); ax.set_xticklabels(["\u22120.4", "0", "0.4"])
    ax.set_xticks([-0.2, 0.2], minor=True)
    ax.grid(axis="x", which="both", color="0.92", lw=0.5); ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Cardiomegaly", fontsize=9, fontweight="bold", labelpad=6)

    ticks = [yy for (_, _), yy in ypos.items()]
    labels = [lab for _, _, lab in ROWS]
    axes[0].set_yticks(ticks + [h[0] for h in headers])
    axes[0].set_yticklabels(labels + [h[1] for h in headers])
    for t, (_, txt) in zip(axes[0].get_yticklabels()[len(labels):], headers):
        t.set_fontweight("bold")
    axes[0].invert_yaxis()

    h = [Line2D([], [], marker="o", color=BLUE, mfc=BLUE, ms=5.5, lw=1.3, label="95% CI excludes 0"),
         Line2D([], [], marker="o", color=BLUE, mfc="white", ms=5.5, lw=1.3, label="95% CI includes 0"),
         Line2D([], [], marker="o", color="0.35", mfc="0.35", ls="none", ms=4.8, label="Site B full reports"),
         Line2D([], [], marker="s", color="0.35", mfc="0.35", ls="none", ms=4.8, label="Site B impression sections")]
    fig.legend(handles=h, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.62, -0.02), fontsize=8)
    fig.tight_layout(rect=(0, 0.1, 1, 0.94), w_pad=0.6)
    # site headers above the panels
    a0, a3, a4 = axes[0].get_position(), axes[3].get_position(), axes[4].get_position()
    for x0, x1, txt in ((a0.x0, a3.x1, "Site A"), (a4.x0, a4.x1, "Site B")):
        fig.text((x0 + x1) / 2, 0.965, txt, ha="center", va="center", fontsize=9.5, fontweight="bold")
        fig.add_artist(Line2D([x0 + 0.005, x1 - 0.005], [0.945, 0.945], transform=fig.transFigure, color="0.4", lw=0.8))

    out = os.path.join(config.BASE_DIR, "comparison")
    fig.savefig(os.path.join(out, "Figure3_contrasts.png"), dpi=300)
    fig.savefig(os.path.join(out, "Figure3_contrasts.pdf"))
    fig.savefig(os.path.join(out, "Figure3_contrasts.tif"), dpi=1200, pil_kwargs={"compression": "tiff_lzw"})
    print("Saved to", out)


if __name__ == "__main__":
    main()
