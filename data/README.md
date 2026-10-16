# Data (not included)

Radiology report texts and reference labels are not shared because of data-use agreements and the
terms of ethical approval. To run the pipeline on your own data, create one folder per site:

```
data/
  sleman/        site A (impressions from screening program registers)
  yogya_full/    site B, full reports (findings + impression)
  yogya_kesan/   site B, impression sections only
```

Each folder starts with the raw export named in `config.RAW_DATA_FILE` (one row per screened
individual, one free-text field with the radiograph reading). Script 01 creates the unique texts
(`TB_teks_unik.xlsx`, columns `ID_unik`, `teks`, `n_baris`) and the row map. Script 02 creates the
annotation form; the two completed forms are saved as `Annotation A.xlsx` and `Annotation B.xlsx`,
and the consensus decisions as `Form_anotasi_konsensus.xlsx`. All later files are created by the scripts.

Labels: `is_radiologi` (radiologi / artefak), `imp_tb` (aktif / suspek / inaktif / tidak), and
`infiltrat`, `nodul`, `kalsifikasi`, `fibrotik`, `kavitas`, `kardiomegali` (ada / tidak).
Annotation instructions are given in Supplementary File S1 of the article.
