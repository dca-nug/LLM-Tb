# Offline LLM extraction of structured labels from Indonesian tuberculosis screening chest radiograph reports

Code for the study *"Effect of Indonesian Language Adaptation and Newer Model Versions on Structured
Information Extraction from Tuberculosis Screening Chest Radiograph Reports by Locally Deployed Large
Language Models"* ([authors withheld for review]).

The pipeline compares Indonesian-adapted open-weight large language models (Sahabat-AI) with their
generic base models and with newer generic versions of the same families. All models run offline
through [Ollama](https://ollama.com) on a single 12-GB graphics card. No patient data are included
in this repository.

## Repository structure

```
config.py                         central configuration (site, model, paths, frozen prompt and schema)
LLM-Tb-01 ... LLM-Tb-22           numbered pipeline scripts (run order below; 17, 18, and 20 are not used)
prompts/                          frozen prompt files exported from config.py (+ export script)
modelfiles/                       Ollama Modelfiles for the two Sahabat-AI models (+ export script)
tools/export_public_results.py    builds the de-identified aggregate results in results/
results/                          aggregate results (no report text)
data/                             expected input layout only; data are not shared
requirements.txt                  Python packages
```

## Requirements

* Python 3.11.4 with the packages in `requirements.txt` (`pip install -r requirements.txt`)
* Ollama 0.40.3
* A graphics card with at least 12 GB of memory (the study used a GeForce RTX 3060, 12 GB)

## Models

| Tag in `config.py` | Model | Role | Ollama model |
|---|---|---|---|
| `gemma2_generik` | Gemma 2 9B | base | `gemma2:9b-instruct-q4_K_M` |
| `sahabat_gemma` | Sahabat-AI Gemma 2 9B | adapted | `sahabatgemma-fix` (local Modelfile) |
| `gemma4_generik` | Gemma 4 12B | newer version | `gemma4:12b` |
| `llama3_generik` | Llama 3 8B | base | `llama3:8b-instruct-q4_K_M` |
| `sahabat_llama` | Sahabat-AI Llama 3 8B | adapted | `sahabatllama-fix` (local Modelfile) |
| `llama31_generik` | Llama 3.1 8B | newer version | `llama3.1:8b` |
| `qwen25` | Qwen2.5 7B | earlier version | `qwen2.5:7b` |
| `qwen35` | Qwen3.5 9B | newer version | `qwen3.5:9b` |

Generic models: `ollama pull <Ollama model>`.
Sahabat-AI models: download the GGUF files from Hugging Face ([repository names]), set the `FROM`
line in `modelfiles/*.Modelfile` to the local GGUF path, then
`ollama create sahabatgemma-fix -f modelfiles/sahabatgemma-fix.Modelfile` (same for Llama).
The Modelfiles replace the distributed chat template, which did not pass the system prompt to the model,
with the chat template of the base model.

Thinking mode is disabled for Gemma 4 and Qwen3.5 (`"disable_thinking": True` in `config.py`);
use the `_Qwen3_5` variants of scripts 04-06 for these two models.

## Configuration

Edit two lines in `config.py` before each run:

* `SITE` - `"sleman"` (site A), `"yogya_full"` (site B, full reports), or `"yogya_kesan"` (site B, impression sections)
* `ACTIVE_MODEL` - one model tag from the table above (LLM scripts only)

Data are read from `data/<site>/` (or from the folder in the environment variable `TB_DATA_DIR`).
Do not rename files inside the site folders; the scripts expect the names in `config.py`.

## Run order

| Step | Script | Run per | Output |
|---|---|---|---|
| 1 | `LLM-Tb-01_extract_unique.py` | site | unique texts and row map |
| 2 | `LLM-Tb-02_build_form.py` | site | blank annotation form |
| 3 | `LLM-Tb-03_rule_based.py` | site | rule-based predictions (reference system, not reported) |
| 4 | `LLM-Tb-04_llm_zeroshot*.py` | site x model | zero-shot predictions |
| 5 | `LLM-Tb-05_llm_oneshot*.py` | site x model | one-shot predictions |
| 6 | `LLM-Tb-06_llm_repeat*.py` | site x model | repeated zero-shot run |
| 7 | `LLM-Tb-07_determinism.py` | site | agreement between repeated runs |
| 8 | `LLM-Tb-08_merge_predictions.py` | site | merged predictions |
| 9 | `LLM-Tb-09_evaluate.py` | site | reference standard, interrater agreement, macro F1 with 95% CI, clinical metrics |
| 10 | `LLM-Tb-11_explicit_implicit.py` | site | explicit vs implicit labels (Supplementary File S2) |
| 11 | `LLM-Tb-12_error_taxonomy.py` | site | error cases (exploratory) |
| 12 | `LLM-Tb-13_robustness.py` | site | perturbation analysis (exploratory, not reported) |
| 13 | `LLM-Tb-15_dataset_summary.py` | site | reference label distribution and kappa (Table 1) |
| 14 | `LLM-Tb-16_rowlevel_sensitivity.py` | site | report-level analysis |
| 15 | `LLM-Tb-14_external_compare.py` | once | macro F1 across sites |
| 16 | `LLM-Tb-19_paired_contrasts.py` | once | paired contrasts and post hoc analysis (Figure 3, Supplementary File S7) |
| 17 | `LLM-Tb-21_figure_heatmap.py` | once | Figure 2 |
| 18 | `LLM-Tb-22_figure_contrasts.py` | once | Figure 3 |
| 19 | `tools/export_public_results.py` | once | `results/` |

`LLM-Tb-10_figure_forest.py` produces an earlier figure that is not used in the article. Site B full reports and
impression sections are processed as two separate sites (`yogya_full`, `yogya_kesan`), each from its own export.

## Reproducibility

* Decoding: temperature 0, seed 42, context window 4096 tokens; responses constrained to a JSON schema.
* The prompt, schema, and one-shot example are frozen in `config.py`; `config.py` stops with an error
  if they change. SHA-256 (first 16 characters): zero-shot `1b432dfeb369b503`, one-shot `195828bed5eab4c3`.
  `prompts/export_prompt.py` writes the exact texts to `prompts/` and re-checks both hashes.
* Bootstrap: 1000 resamples of unique texts for CIs; 10 000 paired resamples for contrasts; seed 42.
* Six models gave identical labels in repeated runs; Gemma 4 and Qwen3.5 changed a small number of labels.

## Data

Radiology report texts and reference labels are not included (data-use agreements and terms of ethical
approval). `data/README.md` describes the expected input layout so the pipeline can be run on other data.
Aggregate results without report text are in `results/`.

## License

Code: MIT License (see `LICENSE`). Aggregate results in `results/`: CC BY 4.0.

## Citation

[Citation withheld for review]
