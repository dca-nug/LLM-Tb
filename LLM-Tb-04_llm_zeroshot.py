# ============================================================
# LLM-Tb-04_llm_zeroshot.py — LLM arm, ZERO-SHOT condition.
# Runs ONE model at a time (config.ACTIVE_MODEL) and writes its own
# prediction file. This "checkpoint per model" design means a long run
# can be done step by step: run one model, come back later for the next.
#
# HOW TO RUN:
#   1. In config.py set SITE and ACTIVE_MODEL (one LLM tag).
#   2. Click Run. Output -> pred_zeroshot_<model>.xlsx in the site folder.
#   3. Change ACTIVE_MODEL, Run again for the next model.
# If the output file for a model already exists, it is skipped (so re-running
# does not repeat work). Delete the file to force a re-run.
#
# The prompt/schema come from config (frozen, hashed). Every model uses the
# SAME prompt, so the comparison is fair. Requires the Ollama app running.
# ============================================================

import os
import json
import time
import platform
import subprocess
from datetime import datetime

import pandas as pd
import ollama

import config

MODEL_TAG = config.ACTIVE_MODEL
MODEL_CFG = config.MODELS[MODEL_TAG]
OUT_FILE  = config.pred_file('zeroshot', MODEL_TAG)


def ollama_version():
    try:
        return subprocess.check_output(['ollama', '--version'], text=True).strip()
    except Exception as e:
        return f'unknown ({e})'


def model_digest(name):
    try:
        info = ollama.show(name)
        d = info.get('details', {})
        return {'family': d.get('family', ''),
                'param_size': d.get('parameter_size', ''),
                'quant': d.get('quantization_level', '')}
    except Exception as e:
        return {'family': f'unknown ({e})', 'param_size': '', 'quant': ''}


def build_options():
    """Decoding options. Qwen3.5 needs thinking mode disabled for determinism."""
    opts = dict(config.OPTIONS)
    if MODEL_CFG.get('disable_thinking'):
        # Qwen3.5 uses a <think> reasoning trace by default; turn it off so the
        # output is a direct JSON answer and closer to deterministic.
        opts['think'] = False
    return opts


def infer(name, teks, options):
    t0 = time.perf_counter()
    resp = ollama.chat(
        model=name,
        messages=[{'role': 'system', 'content': config.SYSTEM_PROMPT},
                  {'role': 'user', 'content': config.USER_TEMPLATE.format(teks=teks)}],
        format=config.SCHEMA, options=options)
    latency = time.perf_counter() - t0
    raw = resp['message']['content']
    try:
        parsed, ok = json.loads(raw), True
    except Exception:
        parsed, ok = {}, False
    return parsed, raw, ok, latency


def derive_dx(row):
    if row.get('is_radiologi') == 'artefak':
        return 'artefak'
    imp = row.get('imp_tb', 'tidak')
    if imp == 'aktif':   return 'tb_aktif'
    if imp == 'suspek':  return 'tb_suspek'
    if imp == 'inaktif': return 'tb_inaktif'
    any_abn = (any(row.get(c) == 'ada' for c in config.FINDING_COLS)
               or row.get('kardiomegali') == 'ada')
    return 'non_tb_abnormal' if any_abn else 'normal'


def main():
    if MODEL_CFG.get('kind') != 'llm':
        raise SystemExit(f"ACTIVE_MODEL '{MODEL_TAG}' is not an LLM. "
                         f"Set config.ACTIVE_MODEL to an LLM tag.")

    if os.path.exists(OUT_FILE):
        print(f"Already done: {OUT_FILE}\n(Delete the file to force a re-run.)")
        return

    name = MODEL_CFG['ollama']
    options = build_options()

    src = pd.read_excel(config.out_path(config.F_UNIQUE))   # ID_unik, teks, n_baris
    src['teks'] = src['teks'].astype(str).str.strip()
    src = src[src['teks'] != ''].reset_index(drop=True)
    print(f'Site: {config.SITE} | Model: {MODEL_TAG} ({name}) | '
          f'Texts: {len(src)} | Prompt hash: {config.PROMPT_HASH_ZERO}')

    records = []
    for pos, r in src.iterrows():
        parsed, raw, ok, latency = infer(name, r['teks'], options)
        rec = {'ID_unik': r['ID_unik'], 'model': MODEL_TAG, 'condition': 'zeroshot',
               'repeat': 1, 'teks': r['teks'], 'json_valid': ok,
               'latency_s': round(latency, 3), 'alasan': parsed.get('alasan', ''),
               'raw': raw}
        for c in config.LABEL_COLS:
            rec[c] = parsed.get(c, None)
        rec['dx_category'] = derive_dx(rec) if ok else None
        records.append(rec)
        if (pos + 1) % 20 == 0:
            print(f'  {pos + 1}/{len(src)}')

    df = pd.DataFrame(records)
    meta = {'timestamp': datetime.now().isoformat(timespec='seconds'),
            'site': config.SITE, 'model_tag': MODEL_TAG, 'ollama_name': name,
            'ollama_version': ollama_version(), 'host': platform.node(),
            'options': json.dumps(options), 'prompt_hash': config.PROMPT_HASH_ZERO,
            'digest': json.dumps(model_digest(name)), 'n_texts': len(src)}
    df_meta = pd.DataFrame(list(meta.items()), columns=['key', 'value'])

    print(f'Done. Rows: {len(df)} | invalid JSON: {int((~df["json_valid"]).sum())} | '
          f'mean latency: {df["latency_s"].mean():.2f}s')
    with pd.ExcelWriter(OUT_FILE, engine='openpyxl') as w:
        df.to_excel(w, sheet_name='Predictions', index=False)
        df_meta.to_excel(w, sheet_name='RunMetadata', index=False)
    print(f'Saved: {OUT_FILE}')


if __name__ == '__main__':
    main()
