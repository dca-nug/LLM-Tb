# ============================================================
# LLM-Tb-01_extract_unique.py
# Single source of truth for de-duplication.
# Reads the raw report file for the active SITE and produces:
#   1. TB_teks_unik.xlsx  -> unique texts (ID_unik, teks, n_baris)
#   2. TB_peta_baris.xlsx -> row -> ID_unik map (to propagate labels back
#                            to all original rows for the sensitivity analysis)
#
# The normalization below defines what counts as a "unique" text. It must
# stay identical across sites so Sleman and Solo are de-duplicated the same
# way. Do not change norm() between runs.
#
# HOW TO RUN: set SITE in config.py, then click Run.
# ============================================================

import re
import pandas as pd
import config

RAW = config.raw_path()
OUT_UNIQUE = config.out_path(config.F_UNIQUE)
OUT_MAP    = config.out_path(config.F_MAP)


def norm(t):
    """Normalize a report text for de-duplication.
    Lowercase, turn newlines and -/bullet into spaces, collapse whitespace.
    IDENTICAL rule across sites."""
    t = str(t).lower()
    t = t.replace('\\n', ' ').replace('\n', ' ')
    t = re.sub(r'[-\u2022]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def main():
    # --- load, keep first column as the report text, drop empties ---
    df = pd.read_excel(RAW)
    text_col = df.columns[0]
    df = df[[text_col]].copy()
    df.columns = ['teks_asli']

    s = df['teks_asli'].astype(str)
    empty = ['', '-', 'nan', 'none', 'null']
    keep = df['teks_asli'].notna() & ~s.str.strip().str.lower().isin(empty)
    df = df[keep].reset_index(drop=True)
    df['_key'] = df['teks_asli'].apply(norm)

    print(f'Site               : {config.SITE}')
    print(f'Rows with text     : {len(df):,}')
    print(f'Unique texts       : {df["_key"].nunique():,}')

    # --- build the unique list ---
    # Representative of each group = the most frequent raw spelling.
    grp = df.groupby('_key')
    representative = grp['teks_asli'].agg(lambda x: x.value_counts().index[0])
    n_rows = grp.size()
    unique = pd.DataFrame({
        'teks': representative,
        'n_baris': n_rows,
    }).reset_index()

    # Order by how many rows each unique text represents (most impactful first).
    unique = unique.sort_values('n_baris', ascending=False).reset_index(drop=True)
    unique['ID_unik'] = [f'U{i+1:03d}' for i in range(len(unique))]

    # --- file 1: unique texts (consumed by every downstream arm) ---
    out_unique = unique[['ID_unik', 'teks', 'n_baris']].copy()
    out_unique.to_excel(OUT_UNIQUE, index=False)

    # --- file 2: row -> ID_unik map (for row-level sensitivity analysis) ---
    mapping = df.merge(unique[['_key', 'ID_unik']], on='_key', how='left')
    mapping = mapping[['ID_unik', 'teks_asli']].copy()
    mapping.columns = ['ID_unik', 'teks']
    mapping.to_excel(OUT_MAP, index=False)

    print('\n' + '=' * 55)
    print(f'Unique texts for annotation : {len(unique):,}')
    print(f'Total rows mapped           : {mapping["ID_unik"].notna().sum():,}')
    print(f'Saved: {OUT_UNIQUE}')
    print(f'Saved: {OUT_MAP}')


if __name__ == '__main__':
    main()
