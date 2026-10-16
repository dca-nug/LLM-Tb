# ============================================================
# LLM-Tb-10_figure_forest.py — forest plot of macro-F1 (zero-shot systems).
# Reads Evaluasi_hasil.xlsx for the active SITE and plots macro-F1 with 95%
# CI for the labels that have a CI (powered), one row per zero-shot system.
# No title. Legend outside the plot. Value + CI printed at each point.
# Output -> Figure_macroF1.png / .pdf in the site folder.
#
# HOW TO RUN: after LLM-Tb-09, set SITE in config.py and click Run.
# Only zero-shot systems (<model>_zs) are shown, matching the main text.
# For a 5/6-arm supplementary version, change the SUFFIX filter below.
# ============================================================

import re

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import config

SUFFIX = '_zs'            # which systems to show: '_zs' (zero-shot) or '_os'
OUT_PNG = config.out_path('Figure_macroF1.png')
OUT_PDF = config.out_path('Figure_macroF1.pdf')

# All macro-F1 labels in display order (underpowered ones are marked, not dropped).
# is_radiologi (the gate) is descriptive and reported in its own table.
LABEL_ORDER = ['imp_tb', 'infiltrat', 'nodul', 'kalsifikasi', 'fibrotik', 'kavitas', 'kardiomegali']

PALETTE = ['#333333', '#1f77b4', '#d62728', '#2ca02c', '#9467bd',
           '#8c564b', '#e377c2', '#ff7f0e', '#17becf']
MARKERS = ['o', 's', 'D', '^', 'v', 'P', 'X', 'h', '*']


def parse_ci(x):
    if not isinstance(x, str) or not x.strip().startswith('['):
        return (np.nan, np.nan)
    m = re.findall(r'-?\d+\.?\d*', x)
    return (float(m[0]), float(m[1])) if len(m) >= 2 else (np.nan, np.nan)


def system_display(tag):
    base = tag[:-len(SUFFIX)] if tag.endswith(SUFFIX) else tag
    return config.DISPLAY_NAMES.get(base, base)


def main():
    df = pd.read_excel(config.out_path(config.F_EVAL), sheet_name='Metrik_primer_macroF1')
    df['ci_lo'], df['ci_hi'] = zip(*df['macroF1_CI95'].map(parse_ci))

    systems = [s for s in df['sistem'].unique() if s.endswith(SUFFIX)]
    # keep a stable, sensible order: rule first if present, then by name
    systems = sorted(systems, key=lambda s: (not s.startswith('rule'), s))
    # rule_based has no suffix, add it explicitly at the front if present
    if 'rule_based' in df['sistem'].unique():
        systems = ['rule_based'] + [s for s in systems if s != 'rule_based']

    present = set(df['label'].unique())
    labels = [l for l in LABEL_ORDER if l in present]

    style = {s: dict(color=PALETTE[i % len(PALETTE)], marker=MARKERS[i % len(MARKERS)])
             for i, s in enumerate(systems)}

    n_sys = len(systems)
    row_gap, group_gap = 1.0, 1.4
    y, group_centers, cursor = {}, {}, 0.0
    for l in labels:
        ys = []
        for s in systems:
            y[(l, s)] = cursor; ys.append(cursor); cursor -= row_gap
        group_centers[l] = float(np.mean(ys)); cursor -= (group_gap - row_gap)

    fig_h = max(3.0, 0.42 * n_sys * len(labels) + 1.2)
    fig, ax = plt.subplots(figsize=(7.6, fig_h))

    for l in labels:
        for s in systems:
            r = df[(df['label'] == l) & (df['sistem'] == s)]
            if r.empty:
                continue
            r = r.iloc[0]; est = r['macro_F1']; lo, hi = r['ci_lo'], r['ci_hi']
            yy = y[(l, s)]; st = style[s]
            has_ci = (not np.isnan(lo)) and (not np.isnan(hi))
            if has_ci:
                ax.plot([lo, hi], [yy, yy], '-', color=st['color'], lw=1.4, zorder=2)
                lab = f'{est:.2f} ({lo:.2f}\u2013{hi:.2f})'
                ax.plot(est, yy, st['marker'], color=st['color'], markersize=6,
                        markeredgecolor='white', markeredgewidth=0.6, zorder=3)
            else:
                # underpowered: hollow marker, no whisker, descriptive value only
                lab = f'{est:.2f}*' if not pd.isna(est) else ''
                ax.plot(est, yy, st['marker'], markerfacecolor='none',
                        markeredgecolor=st['color'], markeredgewidth=1.2,
                        markersize=6, zorder=3)
            ax.annotate(lab, xy=(est, yy), xytext=(0, 6), textcoords='offset points',
                        ha='center', va='bottom', fontsize=7.5, color='#222222', zorder=4)

    for l in labels:
        ax.text(-0.02, group_centers[l], config.LABEL_EN.get(l, l), ha='right',
                va='center', fontsize=11, fontweight='bold',
                transform=ax.get_yaxis_transform())

    ax.set_xlim(0, 1.06)
    ax.set_xlabel('Macro-F1 (95% CI). Hollow markers (*) = descriptive, '
                  'minority class < ' + str(config.POWER_THRESHOLD) + ', no CI.',
                  fontsize=9, fontweight='normal')
    ax.set_xticks(np.arange(0, 1.01, 0.2))
    ax.set_yticks([])
    ax.set_ylim(cursor + (group_gap - row_gap) - 0.5, 0.5)
    for sp in ['top', 'right', 'left']:
        ax.spines[sp].set_visible(False)
    ax.grid(axis='x', ls=':', color='#cccccc', zorder=0)
    ax.tick_params(axis='y', length=0)

    handles = [Line2D([0], [0], color=style[s]['color'], marker=style[s]['marker'],
                      linestyle='-', markersize=6, markeredgecolor='white',
                      markeredgewidth=0.6, label=system_display(s)) for s in systems]
    ncol = min(3, len(systems))
    ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -0.12),
              ncol=ncol, frameon=False, fontsize=9, handletextpad=0.5, columnspacing=1.4)

    fig.savefig(OUT_PNG, dpi=300, bbox_inches='tight')
    fig.savefig(OUT_PDF, bbox_inches='tight')
    print(f'Systems: {[system_display(s) for s in systems]}')
    print(f'Labels: {[config.LABEL_EN.get(l, l) for l in labels]}')
    print(f'Saved: {OUT_PNG}, {OUT_PDF}')


if __name__ == '__main__':
    main()
