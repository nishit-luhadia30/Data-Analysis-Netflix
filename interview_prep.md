# Interview Preparation Guide: Netflix Originals Analytics Project

**Target Roles:** Data Analyst | Analytics Engineer | BI Developer | Strategy Associate  
**Author:** Data Strategy & Analytics  
**Context:** Comprehensive walkthrough of technical, statistical, and strategic decisions in this project.

---

### Q1: Can you walk me through the high-level architecture of this project and why you decided to upgrade the legacy notebook?
**Answer:**  
"The original project was an exploratory notebook written for Google Colab that answered 12 basic questions using pandas and plotly. However, it had no data architecture, lacked statistical verification, suffered from critical positional bugs, and contained zero written business conclusions.

I transformed it into a consulting-grade analytics solution structured around **3 Questions, 3 Tools, and 3 Dashboard Pages**:
1. **Questions:** Portfolio Mix (volume & cadence), Perceived Quality (ratings & acclaim), and Outliers & Strategic Gaps.
2. **Tools:** Python for automated cleaning, star schema export, and non-parametric hypothesis testing; SQLite for 12 enterprise-grade analytical queries; and Power BI for data modeling, DAX engineering, and wireframe dashboard design.
3. **Pages:** Portfolio Overview, Perceived Quality Analysis, and Outliers & Strategic Opportunity Matrix.

I maintained 100% data integrity by archiving original files untouched in `/original`, developing on a dedicated git branch (`analyst-upgrade`), and writing automated assertions proving that all SQL and Python totals match with zero tolerance."

---

### Q2: What was the critical bug in Question 5 of the legacy notebook, and how did you identify and prove it?
**Answer:**  
"In Question 5, the legacy code attempted to compute the average runtime for each genre and append it to a genre frequency table:
```python
genre = data['Genre'].value_counts()
data_genre = pd.DataFrame({'Genre': genre.index, 'count': genre.values})
data_genre['avg_run_time'] = (
    data.groupby('Genre')['Runtime']
    .mean()
    .reset_index(name='avg_run_time')['avg_run_time']
)
```
The root cause was a **positional index misalignment**: `value_counts()` sorts the dataframe by frequency descending (row 0 is `Documentary`, count 159). However, `data.groupby('Genre')['Runtime'].mean().reset_index()` sorts alphabetically (row 0 is `Action`). Because the author extracted the column as a raw unindexed Series, pandas assigned values by physical row position.

Consequently, `Documentary` was assigned 108.00 minutes—which is actually the mean runtime of `Action` films. The true average runtime of `Documentary` is 78.96 minutes, creating a massive **+29.04 minute error** across 159 titles. Every single genre in the legacy notebook received an incorrect runtime. I proved this mathematically in Python by comparing positional assignments against key-based lookups and documented the discrepancy in `data_quality_log.md`."

---

### Q3: Why did you construct a relational star schema with a bridge table instead of querying the flat CSV file directly?
**Answer:**  
"In the raw dataset, 51 titles have compound genre strings separated by slashes (e.g., `Anime / Short`, `Action/Science fiction`), producing 115 unstandardized labels. 

If you keep the data in a flat table, you face a dilemma:
- If you leave compound strings as-is, you fragment your sample sizes and cannot accurately aggregate all `Animation` or `Action` titles.
- If you duplicate rows to split genres in a flat table, all your measures—total catalog count, runtime sums, and release volume—become artificially inflated and distorted.

By building a star schema:
- `fact_titles` maintains the pristine grain of one row per unique title (584 rows).
- `dim_date`, `dim_genre`, and `dim_language` store normalized dimensional attributes.
- `bridge_title_genre` captures the many-to-many relationship (643 title-genre pairs) with an `is_primary` flag.
This allows analysts to slice by individual atomic genres or high-level genre groups without ever duplicating the underlying title count."

---

### Q4: Why is `DISTINCTCOUNT` strictly required in DAX and SQL when joining through the bridge table?
**Answer:**  
"Because a single title can belong to multiple genres. In our catalog, 51 titles belong to 2 or more genres, creating 643 rows in `bridge_title_genre` for 584 unique titles.

If an analyst joins `fact_titles` to `bridge_title_genre` and writes `SELECT COUNT(*) FROM fact_titles f JOIN bridge_title_genre b ...`, any multi-genre film is counted multiple times. The total catalog would falsely show 643 titles instead of 584. 

Therefore, in SQL, we must write `COUNT(DISTINCT f.title_id)`. In Power BI DAX, all volume measures must use `DISTINCTCOUNT(fact_titles[title_id])`. Furthermore, when traversing the bridge in DAX, we preserve single-direction filtering in the schema and use `CALCULATE([Total Titles], CROSSFILTER(fact_titles[title_id], bridge_title_genre[title_id], Both))` to maintain complete model predictability."

---

### Q5: Why did you choose Tukey's $1.5 \times \text{IQR}$ rule for outlier detection instead of z-scores or visual inspection?
**Answer:**  
"The legacy notebook simply eyeballed a scatter plot and declared *The Irishman* as the sole outlier. That is entirely subjective and missed 74 runtime outliers and 9 score outliers.

I selected the Interquartile Range ($1.5 \times \text{IQR}$) method because:
1. **Robustness to Non-Normality:** Both runtime and IMDb score distributions violate Gaussian normality (runtime has a severe positive skew with a heavy short-format tail; score is negatively skewed). Standard deviation and z-scores assume normality and are themselves distorted by extreme values.
2. **Standard Non-Parametric Boundaries:** 
   - For runtime: $\text{Q1} = 86\text{m}$, $\text{Q3} = 108\text{m}$, $\text{IQR} = 22\text{m}$. Lower fence is $86 - (1.5 \times 22) = 53\text{m}$; upper fence is $108 + (1.5 \times 22) = 141\text{m}$.
   - For score: $\text{Q1} = 5.7$, $\text{Q3} = 7.0$, $\text{IQR} = 1.3$. Lower fence is $3.75$; upper fence is $8.95$.

Importantly, as an analyst, I categorized outliers by type: titles under 40 minutes (42 titles) are **format differences** (shorts, aftershows, interviews), whereas films like *The Irishman* (209 min) are **epic feature outliers**. For scores, 8 titles were sub-3.75 quality outliers (*Enter the Anime* at 2.5) and 1 was an acclaimed outlier (*David Attenborough: A Life on Our Planet* at 9.0). I used z-scores ($|z| > 3$) as a secondary cross-check."

---

### Q6: Why did you establish a minimum group size threshold ($n \ge 10$) and how did you handle groups below it?
**Answer:**  
"In the raw data, only 7 of 115 genres and 6 of 38 languages have 10 or more titles. 108 genres and 32 languages have fewer than 10 titles, with dozens containing just 1 or 2 titles.

In analytics, drawing strategic conclusions from tiny samples is a classic sample bias trap. If a language has 1 title that scored 8.0 (e.g., *A Sun* in Chinese), reporting that 'Chinese is Netflix's highest-performing language' would be statistically misleading.

My governance rule was threefold:
1. **Flag, do not hide:** Include low-sample groups in data exploration, but attach an explicit `low_sample` warning badge.
2. **Suppress high-level generalization:** Require $n \ge 10$ for ranking tables, benchmark cards, and hypothesis testing.
3. **Consolidate taxonomy:** Mapped all 115 raw genres into 8 standardized genre groups where every single group has $n \ge 21$, ensuring all strategic categories are statistically robust."

---

### Q7: Why did you choose the Kruskal-Wallis test instead of standard One-Way ANOVA?
**Answer:**  
"One-Way ANOVA relies on three strict parametric assumptions:
1. Normality of residuals within groups.
2. Homogeneity of variance (homoscedasticity across groups).
3. Continuous, normally distributed dependent variable.

When I ran diagnostic checks on IMDb scores grouped by genre and language, Shapiro-Wilk and skewness tests showed significant departure from normality. Group sizes were also highly unbalanced (Documentary had 163 titles while Action/Other had 21).

The **Kruskal-Wallis test** is the non-parametric analogue to One-Way ANOVA. It evaluates whether samples originate from the same distribution by analyzing the rank sums of scores rather than raw means. The test yielded an $H\text{-statistic} = 168.87$ ($p = 7.7 \times 10^{-33}$) across the 8 genre groups and $H = 437.56$ ($p < 0.001$) across major languages, providing conclusive mathematical evidence that perceived quality differences between genres are genuine and not random chance."

---

### Q8: What did your analysis reveal regarding the relationship between runtime and perceived quality?
**Answer:**  
"A common hypothesis in streaming is that longer films are more prestigious or receive higher ratings. I tested this rigorously using both Pearson correlation and Spearman rank correlation:
- **Spearman Rank Correlation:** $\rho = -0.0221$ ($p = 0.593$).
- **Pearson Linear Correlation:** $r = -0.0409$ ($p = 0.325$).

Because the p-values are far above the 0.05 threshold, the correlation is statistically indistinguishable from zero. Furthermore, when I segmented the catalog into 4 quality quartiles using SQL `NTILE(4)`, the mean runtimes were virtually identical:
- Q1 (Bottom 25%, scores $\le 5.7$): 94.9 minutes.
- Q2 (Lower-mid 25%, scores 5.8–6.3): 94.6 minutes.
- Q3 (Upper-mid 25%, scores 6.4–6.9): 94.9 minutes.
- Q4 (Top 25%, scores $\ge 7.0$): 91.8 minutes.

This provides definitive empirical proof that duration has zero influence on perceived quality."

---

### Q9: Why did you isolate mature reporting years (2016–2020) and flag 2014, 2015, and 2021 as sparse/partial?
**Answer:**  
"A frequent pitfall in time-series analysis is naive Year-over-Year (YoY) calculation across incomplete periods.
- In 2014, Netflix released only 1 original title (December 13).
- In 2015, they released only 9 titles (beginning late May).
- In 2021, the dataset terminates on May 27, capturing only 71 titles across 5 months.

If you compute 2021 vs. 2020 without filtering, you would show a -61.2% drop in releases, falsely implying that Netflix slashed its original film production. In reality, 2021 was on pace for ~170 titles. Similarly, computing growth from 2014 to 2015 yields a misleading +800% increase based on 8 incremental movies.

I engineered the `is_full_year` boolean flag in `dim_date` (set to 1 for 2016–2020, 0 otherwise) and restricted all YoY metrics (`LAG()` in SQL, `Titles YoY Growth %` in DAX) strictly to mature full years (503 titles). This revealed genuine business scaling: +120.0% in 2017, +50.0% in 2018, +26.3% in 2019, and +46.4% in 2020."

---

### Q10: What are the fundamental limitations of this project, and how do you prevent stakeholders from misinterpreting the numbers?
**Answer:**  
"A great data analyst must understand what the data *cannot* say. I explicitly communicated five critical boundaries:
1. **IMDb Score is a Quality Proxy, Not Popularity:** IMDb ratings represent self-selected public reviewers, not the average Netflix subscriber. Documentaries often attract passionate, appreciative viewers who rate generously, while popular mass comedies attract casual, critical viewers.
2. **Zero Viewership or Engagement Data:** The dataset contains no hours watched, completion rates, or household reach. An executive must never assume that a 9.0 documentary had higher commercial reach than a 5.5 comedy.
3. **No Financial or ROI Data:** Production budgets, marketing costs, and licensing fees are absent. We cannot calculate return on investment.
4. **Sample Size Censoring:** With 584 total titles, breaking down into niche intersections (e.g., Italian Romance) yields sample sizes of 1 or 2 titles, which cannot support strategic policy.
5. **Correlation is Not Causation:** Demonstrating that Documentaries average 6.93 does not mean greenlighting 50 more documentaries will increase subscriber growth or platform satisfaction.

By stating these boundaries clearly up front, I protected the organization from making flawed commercial decisions based on unverified assumptions."
