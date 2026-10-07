# Data Quality Log: Netflix Originals Dataset

**Project:** Netflix Originals Analytics Portfolio Upgrade  
**Source Dataset:** `NetflixOriginals.csv` (584 records, 6 columns, read with `encoding='latin-1'`)  
**Audit Date:** September 2026  
**Auditor / Analyst:** Data Strategy & Analytics  

---

## 1. Summary of Ingestion & Integrity Checks

- **Total Ingested Rows:** 584 titles
- **Total Missing / Null Cells:** 0 across all columns (`Title`, `Genre`, `Premiere`, `Runtime`, `IMDB Score`, `Language`)
- **Primary Key Uniqueness:** All 584 `Title` values are distinct (100% unique).
- **Date Coverage:** December 13, 2014 to May 27, 2021.
- **IMDb Score Range:** 2.5 to 9.0 (perceived quality proxy only; no viewership/financial data).
- **Runtime Range:** 4 to 209 minutes.

---

## 2. Identified Issues, Decisions, and Impact Log

| Issue ID | Data Field / Element | Observed Data Issue | Business & Analytical Impact | Decision & Remediation Strategy | Rows Affected |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **DQ-01** | `Premiere` | 5 records contain period delimiters instead of commas (e.g., `"October 16. 2019"`, `"September 15. 2017"`, `"July 15. 2016"`). | Breaks strict datetime parsing libraries (`datetime.strptime` with fixed format) and causes ingestion crashes. | Replace periods with commas (`.replace('.', ',')`) before parsing via `pd.to_datetime`. Construct a dedicated date dimension table (`dim_date`) with date key, year, quarter, month, weekday, and flags. | 5 records |
| **DQ-02** | `Premiere` / `Year` | Extreme temporal sparsity and partial year coverage:<br>• **2014:** 1 title (Dec 13)<br>• **2015:** 9 titles (May–Dec)<br>• **2021:** 71 titles (Jan–May 27) | Comparing 2014–2015 or partial 2021 against mature full years creates highly distorted Year-over-Year (YoY) growth calculations. | Engineer boolean flag `is_full_year` (`1` for 2016–2020, `0` for 2014, 2015, and 2021). Restrict all YoY calculations strictly to full years (2016–2020: 503 titles). | 81 records (1 in 2014, 9 in 2015, 71 in 2021) |
| **DQ-03** | `Genre` | Compound genre values separated by slashes in 51 records (e.g., `"Anime / Short"`, `"Action/Science fiction"`), producing 115 distinct raw labels. | Inflates genre count, fragments sample sizes, and masks underlying relationships. | 1. Split compound genres by `/` into a normalized `bridge_title_genre` table.<br>2. Assign the first listed genre as `primary_genre`.<br>3. Map all 115 raw genres to 8 standardized `genre_groups` via `data/external/genre_group_map.csv`. | 51 compound rows (All 584 mapped to 8 groups) |
| **DQ-04** | `Language` | Compound language values separated by slashes in 23 records (e.g., `"English/Japanese"`, `"English/Spanish"`), producing 38 distinct raw labels. | Misrepresents linguistic diversity and distorts language-level quality benchmarks. | Extract `primary_language` (first listed before `/`) and generate a boolean indicator `is_multilingual = 1` for compound entries. Map to `dim_language`. | 23 compound rows (All 584 mapped) |
| **DQ-05** | `Runtime` | Format heterogeneity: 42 titles have runtime < 40 minutes (minimum 4 min), mixing short films, aftershows, and interview specials with full-length features. | Directly comparing runtimes across dissimilar video formats skews central tendency and correlation analysis. | Create `runtime_bucket`: `Short/Special` (< 40m), `Standard` (40–120m), `Long` (> 120m). Treat shorts as format outliers rather than anomalous feature films. | 42 titles (< 40m), 483 standard, 59 long (> 120m) |
| **DQ-06** | `Title` | Encoding artifacts in raw source bytes from mixed character encodings:<br>• Row 117: `Òlòt?ré` (contains `?` `0x3F`)<br>• Row 242: `Tribhanga \x96 Tedhi Medhi Crazy` (Windows-1252 en-dash `0x96`)<br>• Row 297: `Como Caído del Cielo` (`\xED` = `í`)<br>• Row 391: `7 años` (`\xF1` = `ñ`) | Display artifacts in consoles and reporting tools; potential join mismatches if altered. | Preserve strings as decoded with `latin-1` / `cp1252`. Trim leading/trailing whitespace. Do NOT invent guessed corrections; document explicitly. | 4 records |
| **DQ-07** | `Genre` & `Language` | Extreme long-tail distribution with very low sample sizes:<br>• Only 7 raw genres and 6 raw languages have $\ge 10$ titles.<br>• 108 raw genres and 32 raw languages have $< 10$ titles. | Drawing statistical inferences from $n < 10$ groups risks extreme sample bias and spurious conclusions. | Enforce minimum sample rule: any group with $n < 10$ titles is flagged as `low_sample`. In reports and visuals, low-sample groups are presented with clear warning badges and excluded from high-level generalizations. | 108 raw genres, 32 raw languages |
| **DQ-08** | Outlier Detection | Arbitrary visual inspection of scatter plots in legacy notebook (eyeballing *The Irishman* only). | Overlooks short runtime outliers (specials/aftershows) and low/high rating extremes. | Implement rigorous statistical $1.5 \times \text{IQR}$ rule for both Runtime (IQR = 22m, lower fence = 53m, upper fence = 141m) and IMDb Score (IQR = 1.3, lower fence = 3.75, upper fence = 8.95), cross-referenced with z-scores. | 75 runtime outliers, 9 score outliers |

---

## 3. Legacy Notebook Code Defect Log (`Netflix_Data_Analyses.ipynb`)

| Defect ID | Section / Question | Defect Description | Technical Root Cause | Corrective Action Implemented |
| :---: | :--- | :--- | :--- | :--- |
| **CD-01** | Setup | Hardcoded Google Colab path: `pd.read_csv('/content/NetflixOriginals.csv', encoding='latin-1')`. | Static cloud path invalid in local/production environments. | Converted to relative modular project paths (`data/raw/` or repo root). |
| **CD-02** | Q5 | Positional assignment mismatch in `avg_run_time`. `Documentary` was assigned 108.00 min instead of its true mean of 78.96 min. | `data_genre['avg_run_time'] = data.groupby('Genre')['Runtime'].mean().reset_index()['avg_run_time']`. Groupby series sorted alphabetically (`Action` at index 0) was pasted into frequency-sorted dataframe (`Documentary` at index 0). | Used explicit key-based merge or direct groupby aggregation: `df.groupby('Genre')['Runtime'].mean()`. |
| **CD-03** | Q3 & Q9 | Aggregations grouped by `Title`, returning individual movies instead of genre summaries. | `.groupby(['Language', 'Genre', 'Title'])` and `.groupby(['Genre', 'Title'])`. | Grouped strictly by `Genre` or `Genre Group`, computing `mean()`, `median()`, and title counts with sample filters. |
| **CD-04** | Q1 & Q4 | Redundant grouping keys (`groupby(['Language', 'Title'])`). | Unnecessary since `Title` is already unique across all 584 rows. | Simplified aggregations to relevant dimensional attributes. |
| **CD-05** | Setup & Q2 | Created `Weekday` and `Month` columns but never analyzed them. | Incomplete feature exploration. | Built full temporal release pattern analysis (Friday dominance 65.6%, October peak 13.2%). |
| **CD-06** | Q11 | Code bug in bar chart: `.rename(columns={'index':'Year','Year':'Count'})` with `px.bar(..., x='Count', y='count')`. | Inconsistent column names causing runtime error or faulty plotting. | Rewrote clean bar chart showing release volume by year with full-year callouts. |
| **CD-07** | Global | Absence of written interpretations, executive findings, or limitations. | Notebook only executed raw code blocks without business narrative. | Authored executive summary, interview prep, DAX measures, and structured markdown commentary throughout. |

---
*Verified and signed off for the Data Analyst Portfolio Upgrade.*
