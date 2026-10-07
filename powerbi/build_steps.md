# Power BI Desktop Build Steps: Netflix Originals

**Project:** Netflix Originals Analytics Portfolio Upgrade  
**Target:** Power BI Desktop  
**Data Location:** `data/processed/powerbi/*.csv`  
**Author:** Data Strategy & Analytics  

Follow this concise, numbered build order to reconstruct the complete 3-page dashboard in Power BI Desktop from scratch.

---

## Step 1: Data Ingestion (Power Query)
1. Open **Power BI Desktop**.
2. Click **Get Data** $\rightarrow$ **Text/CSV**.
3. Ingest each of the 5 processed CSV files from `data/processed/powerbi/`:
   - `fact_titles.csv`
   - `dim_date.csv`
   - `dim_genre.csv`
   - `dim_language.csv`
   - `bridge_title_genre.csv`
4. In **Power Query Editor**, verify data types:
   - `date_key`, `year`, `title_id`, `genre_id`, `language_id`: **Whole Number**
   - `runtime`, `imdb_score`: **Decimal Number**
   - `full_date`: **Date**
   - Text fields (`title`, `genre_group`, `primary_language`, buckets): **Text**
5. Click **Close & Apply**.

---

## Step 2: Establish Model Relationships (Model View)
1. Navigate to **Model View** (left navigation bar).
2. Configure 1-to-many relationships (single cross-filter direction, single-direction filter):
   - `dim_date[date_key]` $\rightarrow$ `fact_titles[date_key]` (1:*)
   - `dim_language[language_id]` $\rightarrow$ `fact_titles[primary_language_id]` (1:*)
   - `dim_genre[genre_id]` $\rightarrow$ `fact_titles[primary_genre_id]` (1:*)
   - `dim_genre[genre_id]` $\rightarrow$ `bridge_title_genre[genre_id]` (1:*)
   - `fact_titles[title_id]` $\rightarrow$ `bridge_title_genre[title_id]` (1:*)
3. Verify that all relationship lines show the single arrow pointing towards `fact_titles` or `bridge_title_genre`.
4. Hide foreign key ID columns from Report View to keep the field list clean.

---

## Step 3: Implement DAX Measures
1. In Report View, right-click `fact_titles` $\rightarrow$ **New measure**.
2. Copy and paste each measure from `powerbi/measures.dax`:
   - `Total Titles = DISTINCTCOUNT(fact_titles[title_id])`
   - `Avg IMDb Score = AVERAGE(fact_titles[imdb_score])`
   - `Median IMDb Score = MEDIAN(fact_titles[imdb_score])`
   - `% High-Rated Titles = ...` (Format as **Percentage**, 1 decimal)
   - `% Low-Rated Titles = ...` (Format as **Percentage**, 1 decimal)
   - `Avg Runtime = AVERAGE(fact_titles[runtime])` (Format as **Decimal**, 1 decimal)
   - `Titles YoY Growth % = ...` (Format as **Percentage**, 1 decimal)
   - `Top Genre Share % = ...` (Format as **Percentage**, 1 decimal)
   - `Language Diversity Count = ...` (Whole number)
   - `Sample Reliability Badge = ...` (Text)
   - `Titles Across All Genre Tags = ...` (Whole number)
3. Organize measures into a display folder named `_Measures`.

---

## Step 4: Build Page 1 — Portfolio Overview
1. Rename Page 1 to **Portfolio Overview**.
2. **Top Filter Slicers:**
   - Dropdown slicer for `dim_date[year]`.
   - Dropdown slicer for `fact_titles[genre_group]`.
   - Dropdown slicer for `fact_titles[primary_language]`.
3. **KPI Cards (Top Banner):**
   - Card 1: `[Total Titles]` (Data label: 584)
   - Card 2: `[Mature Period Titles]` (Data label: 503)
   - Card 3: `[Avg Runtime]` (Data label: 93.6 min)
   - Card 4: `[Avg IMDb Score]` (Data label: 6.27)
   - Card 5: `[Top Genre Share %]` (Data label: 27.9%)
4. **Visual 1 (Annual Releases):**
   - Clustered column chart.
   - X-axis: `dim_date[year]`.
   - Y-axis: `[Total Titles]`.
   - Tooltip: `[Titles YoY Growth %]`.
5. **Visual 2 (Genre Composition):**
   - Donut chart or horizontal bar chart.
   - Category: `fact_titles[genre_group]`.
   - Values: `[Total Titles]`.
6. **Visual 3 (Language Concentration):**
   - Horizontal bar chart.
   - Y-axis: `fact_titles[primary_language]`.
   - X-axis: `[Total Titles]`.
7. **Visual 4 (Release Timing):**
   - Clustered bar chart.
   - Y-axis: `dim_date[weekday_name]` (Sorted by Day of Week 1-7).
   - X-axis: `[Total Titles]`.

---

## Step 5: Build Page 2 — Perceived Quality Analysis
1. Create a new page, rename to **Quality Analysis**.
2. **Top Filter Slicers:**
   - Dropdown slicers for `fact_titles[genre_group]`, `fact_titles[primary_language]`, and `fact_titles[runtime_bucket]`.
3. **Visual 5 (Genre Score Benchmarks):**
   - Clustered bar chart (Horizontal).
   - Y-axis: `fact_titles[genre_group]`.
   - X-axis: `[Avg IMDb Score]`.
   - Add Constant Line on X-axis at `6.27` (Label: *Catalog Avg*).
4. **Visual 6 (Acclaim Tier Distribution):**
   - 100% Stacked bar chart.
   - Y-axis: `fact_titles[genre_group]`.
   - X-axis: `[Total Titles]`.
   - Legend: `fact_titles[score_bucket]`.
   - Colors: Green for `High (>=7.0)`, Slate/Gray for `Mid (5.5-6.9)`, Crimson for `Low (<5.5)`.
5. **Visual 7 (Runtime vs. IMDb Score):**
   - Scatter chart.
   - Values: `fact_titles[title]`.
   - X-axis: `fact_titles[runtime]`.
   - Y-axis: `fact_titles[imdb_score]`.
   - Legend: `fact_titles[genre_group]`.
   - Turn on **Trend line** (linear regression).

---

## Step 6: Build Page 3 — Outliers & Opportunities
1. Create a new page, rename to **Outliers & Opportunities**.
2. **Visual 8 (Outlier Explorer Table):**
   - Table visual.
   - Columns: `title`, `genre_group`, `primary_language`, `runtime`, `imdb_score`, `runtime_bucket`, `score_bucket`.
   - Filter on Visual: `runtime < 53` OR `runtime > 141` OR `imdb_score < 3.75` OR `imdb_score > 8.95`.
3. **Visual 9 (Quadrant Strategic Scatter):**
   - Scatter chart.
   - Details: `primary_language`.
   - Legend: `genre_group`.
   - X-axis: `[Total Titles]`.
   - Y-axis: `[Avg IMDb Score]`.
   - Add Reference Lines: X-axis at 15 titles; Y-axis at 6.27.
4. **Visual 10 (Opportunity Heatmap Matrix):**
   - Matrix visual.
   - Rows: `fact_titles[genre_group]`.
   - Columns: `fact_titles[primary_language]`.
   - Values: `[Avg IMDb Score]`.
   - Apply Conditional Formatting: Background color gradient (Red at 5.0, Yellow at 6.2, Green at 7.0).

---

## Step 7: Export to PDF & Screenshots for Portfolio
1. Go to **File** $\rightarrow$ **Export** $\rightarrow$ **Export to PDF**.
2. Save the resulting PDF file as `reports/Netflix_Originals_Dashboard.pdf`.
3. Capture full-resolution screenshots of each page:
   - `reports/screenshots/page1_portfolio_overview.png`
   - `reports/screenshots/page2_quality_analysis.png`
   - `reports/screenshots/page3_outliers_opportunities.png`
4. Reference these screenshots in the portfolio `README.md`.
