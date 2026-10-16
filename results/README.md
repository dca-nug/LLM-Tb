# Aggregate results

Created by `tools/export_public_results.py`. These files contain no report text and no annotator
comments; texts are identified only by the study identifier `ID_unik`.

| File | Contents |
|---|---|
| `<site>_results.xlsx` | macro F1 with 95% CI, sensitivity/specificity/PPV/NPV with TP, FP, FN, TN, report type counts, interrater agreement, reference label distribution, explicit/implicit strata, report-level analysis, repeated-run agreement |
| `paired_contrasts.xlsx` | all paired contrasts (zero-shot and one-shot, all labels) and the post hoc tuberculosis impression groupings |

Sites: `sleman` = site A; `yogya_full` = site B full reports; `yogya_kesan` = site B impression sections.
