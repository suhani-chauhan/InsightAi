# Insight Studio — the Data Science workflow

Insight Studio is InsightAI's Data Science workspace. It turns a tabular
dataset into a guided pipeline: **Dataset → Quality → Clean → Explore → ML →
Report**, with an **Ask InsightAI** panel at every step.

Everything numeric is computed in Python (`pandas` / `numpy` / `scikit-learn`).
The LLM only *explains* values that have already been computed — it never
calculates statistics or invents figures. If no LLM credential is configured,
the narration degrades gracefully and the computed analysis stays accurate.

---

## 1. Getting a dataset in

Open **Insight Studio** from the sidebar. Four sources:

| Source | How |
|--------|-----|
| **Query result** | Run a question in **Chat**, then click **Analyze Dataset** on the result. The rows + columns are handed to Insight Studio (via `sessionStorage`, so it survives the navigation). |
| **File upload** | Landing screen → **Upload a file**. CSV, TSV, or `.xlsx`, up to 12 MB / 100k rows. The browser reads the file and posts its text (or base64 for xlsx); pandas parses it server-side. |
| **Database table** | Landing screen → **From a database table** → pick a connection and table. Runs `SELECT * FROM "schema"."table" LIMIT n` through the existing query engine (read-only, statement timeout, connection-scope checks, 20k-row cap). |
| **Demo dataset** | Landing screen → **Use the demo dataset**. An employee-attrition table seeded with missing values, duplicates, inconsistent category labels, and salary outliers so every step has something to show. |

A session is a **bounded in-memory analysis copy** — scoped to the owning
user, capped at 8 per user with a 3-hour TTL. The source database is never
written to or mutated. Sessions don't survive a server restart.

---

## 2. Dataset

Shows row/column counts, inferred column kinds (numeric / categorical /
datetime / boolean / text), a per-column stat table (missing %, unique, mean /
median / mode, min, max), and sample rows.

`POST /api/data-science/sessions/{id}/profile` → full dataset- and
column-level statistics (quantiles, IQR, outlier counts, skew, histograms).

---

## 3. Quality

`POST /api/data-science/sessions/{id}/quality`

Seven deterministic issue detectors:

- **Missing values** — per column, with severity by percentage
- **Duplicates** — exact duplicate rows, non-unique identifier columns
- **Data types** — numbers stored as text, dates stored as text
- **Categorical consistency** — labels that differ only by case/whitespace
  (`India` / `india` / `INDIA`); flagged, never auto-merged
- **Outliers** — IQR fences + modified z-score
- **Constant / near-zero-variance columns**
- **Potential target leakage** — columns whose names suggest post-outcome data

The **Data Quality Score** (0–100) is a deterministic function of the issues:
each of seven dimensions starts at 100 and loses points per issue, weighted by
severity (`info` −2, `low` −6, `medium` −16, `high` −34). The overall score is
the mean of the dimension scores.

---

## 4. Clean

`POST .../cleaning/recommendations` → each quality issue becomes a concrete
operation with **problem / solution / reason / expected impact**.

Two modes:

- **Recommendation mode** — tick the operations you want, then **Preview**
  (dry run: before/after row/missing/duplicate counts + a column-level diff),
  then **Apply**.
- **Smart Clean** — **Apply N safe fixes** applies the low-risk operations
  (trim whitespace, standardise obvious category case, convert numeric strings,
  remove exact duplicates) without individual confirmation.

Eleven operations: `trim_whitespace`, `standardize_categories`, `to_numeric`,
`to_datetime`, `drop_duplicates`, `drop_column`, `drop_rows_missing`,
`impute_missing` (mean / median / mode / constant / KNN — auto-selected from
the column's distribution), `handle_outliers` (keep / remove / cap / flag),
`group_rare_categories`, `map_categories`.

History is exact: **Undo last step**, **Reset to original**. Applying a step
recomputes the quality score, so you see e.g. *72 → 91 after removing
duplicates and imputing Age*.

---

## 5. Explore (EDA)

`POST .../eda` (optionally with a `target` column)

- Numeric summary (mean, median, std, quartiles, IQR, skew, kurtosis)
- Categorical frequency tables
- Correlation matrix + heatmap, ranked top pairs
- Seven chart types: histogram, box, bar, pie, scatter, line, correlation heatmap
- **Auto-insights** — skew, class imbalance, strong correlations, group
  differences by target — every number lifted from the computations above.
  Phrasing is "associated with", never "causes".

---

## 6. ML

`POST .../ml/detect-task` → classification vs regression (override in the UI).

`POST .../ml/train` with `{target, task?, models?, test_size?, primary_metric?,
cross_validation?}`:

1. Features are prepared: datetime columns expanded to year/month/day-of-week,
   free-text dropped, obvious identifier columns auto-excluded.
2. **Train/test split happens first.** All preprocessing (imputers, scalers,
   one-hot encoders) lives inside a `Pipeline` + `ColumnTransformer` and is
   fitted on the **training fold only** — the test set never influences
   training.
3. Models trained and compared:
   - Classification: Logistic Regression, Decision Tree, Random Forest, KNN,
     Gradient Boosting
   - Regression: Linear, Ridge, Lasso, Decision Tree, Random Forest,
     Gradient Boosting
4. Stratified split for classification; 5-fold cross-validation when the data
   is large enough.
5. Metrics: accuracy / precision / recall / F1 / ROC-AUC / confusion matrix
   (classification); R² / MAE / MSE / RMSE (regression).
6. The **best model** is chosen by the task-appropriate primary metric
   (F1 for imbalanced classification, accuracy otherwise; R² for regression) —
   not always the highest accuracy.
7. **Feature importance** — native for tree/linear models, permutation
   otherwise; one-hot columns collapsed back to their source feature.

**Make a prediction** — a form generated from the feature schema, pre-filled
from a real test-set row, run back through the exact fitted pipeline.

**Download model** — `GET .../ml/model` streams the fitted `Pipeline` +
metadata as a `.joblib` artifact. The app only ever *writes* artifacts; it
never loads a user-supplied model file.

---

## 7. Report

`POST .../report` assembles the computed artifacts into an executive summary
plus sections for dataset overview, data quality, cleaning operations
(before/after), EDA findings, ML comparison + best model + feature importance,
and recommendations. Exportable as standalone HTML from the UI.

---

## Ask InsightAI

`POST .../ask` with `{question}`. Answers are grounded strictly in the
session's computed artifacts (dataset overview, quality report, cleaning
history, EDA statistics, model results). Example questions: *"What are the
biggest data quality problems?"*, *"What should I clean first?"*, *"Which model
performed best and why?"*, *"Should I use classification or regression?"*.

---

## Pinning to dashboards

The quality-score breakdown, model comparison, feature importance, and EDA
numeric summary each have a **Pin to dashboard** button that writes a native
widget (via the existing `addDashboardWidget` API) to any dashboard — so
Data Science metrics live alongside your BI charts, with the same drag-and-drop
grid and chart switching.

---

## Guarantees

- The connected/source database is **read-only** for the workspace and is
  never modified.
- Every statistic, quality score, cleaning impact, model metric, and feature
  importance is a deterministic Python computation — no LLM math, no random
  numbers, no hardcoded values.
- Preprocessing is fitted on the training split only; no data leakage.
- Analysis sessions are owner-scoped and held in memory only.
