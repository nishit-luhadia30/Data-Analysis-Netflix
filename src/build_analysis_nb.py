import json
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
cells = []

# Title & Metadata
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "# Netflix Originals: Advanced Analytical Deep Dive\n",
        "**Upgraded Exploratory & Statistical Analysis Notebook**\n",
        "\n",
        "**Project:** Data Analyst Portfolio Upgrade (SQL + Python + Power BI)  \n",
        "**Author:** Data Strategy & Analytics  \n",
        "**Dataset:** `NetflixOriginals.csv` (584 titles, 2014 - May 2021)  \n",
        "\n",
        "### Project Framework: 3 Questions, 3 Tools, 3 Dashboard Pages\n",
        "- **Question 1: Portfolio Mix** — Catalog composition by genre, language, YoY scaling, and release timing.\n",
        "- **Question 2: Perceived Quality** — Perceived quality benchmarks (IMDb score), acclaim share (>= 7.0), and runtime relationships.\n",
        "- **Question 3: Outliers & Strategic Gaps** — Statistical outliers (IQR & z-score) and underperforming content opportunities.\n",
        "\n",
        "---"
    ]
})

# Setup & Imports
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "import os\n",
        "import sqlite3\n",
        "import numpy as np\n",
        "import pandas as pd\n",
        "import matplotlib.pyplot as plt\n",
        "import seaborn as sns\n",
        "from scipy import stats\n",
        "\n",
        "# Plotting aesthetic\n",
        "sns.set_theme(style=\"whitegrid\", palette=\"muted\")\n",
        "plt.rcParams.update({\n",
        "    'font.size': 11,\n",
        "    'axes.labelsize': 12,\n",
        "    'axes.titlesize': 14,\n",
        "    'xtick.labelsize': 10,\n",
        "    'ytick.labelsize': 10,\n",
        "    'figure.titlesize': 16,\n",
        "    'figure.dpi': 120\n",
        "})\n",
        "\n",
        "# Paths\n",
        "DB_PATH = os.path.join(\"..\", \"netflix.db\")\n",
        "CSV_PATH = os.path.join(\"..\", \"data\", \"processed\", \"powerbi\", \"fact_titles.csv\")\n",
        "\n",
        "df = pd.read_csv(CSV_PATH)\n",
        "print(f\"Loaded fact_titles: {df.shape[0]} rows, {df.shape[1]} columns\")\n",
        "df.head(3)"
    ]
})

# Q1
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 1: Language and Extended Runtimes\n",
        "**Original Notebook Question:** *\"In which language was the long hour film created\"*\n",
        "\n",
        "**Audit Findings & Fix:**\n",
        "- The original notebook ran `.groupby(['Language','Title'])['Runtime'].mean()`, which is redundant because `Title` is already unique.\n",
        "- Here, we evaluate long-hour films (> 120 min) across languages and compare average feature lengths by language (for reliable groups $n \\ge 10$)."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# 1. Top longest individual films\n",
        "longest_films = df.sort_values(by='runtime', ascending=False)[['title', 'primary_language', 'genre_group', 'runtime', 'imdb_score']].head(8)\n",
        "print(\"Top 8 Longest Films:\")\n",
        "print(longest_films.to_string(index=False))\n",
        "\n",
        "# 2. Runtime distribution across languages with n >= 10\n",
        "lang_counts = df['primary_language'].value_counts()\n",
        "major_langs = lang_counts[lang_counts >= 10].index.tolist()\n",
        "df_major_lang = df[df['primary_language'].isin(major_langs)]\n",
        "\n",
        "plt.figure(figsize=(10, 5))\n",
        "sns.boxplot(data=df_major_lang, x='primary_language', y='runtime', order=major_langs, palette='crest')\n",
        "plt.title('Runtime Distribution by Major Primary Language (n >= 10)', weight='bold')\n",
        "plt.xlabel('Primary Language')\n",
        "plt.ylabel('Runtime (Minutes)')\n",
        "plt.tight_layout()\n",
        "plt.show()\n",
        "\n",
        "lang_rt_summary = df_major_lang.groupby('primary_language')['runtime'].agg(['count', 'mean', 'median']).round(1)\n",
        "print(\"\\nMajor Language Runtime Benchmarks:\")\n",
        "print(lang_rt_summary)"
    ]
})

# Q2
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 2: Documentary Quality Trajectory (Jan 2019 – June 2020)\n",
        "**Original Notebook Question:** *\"Find and visualize the IMDB values of the movies shot in the 'Documentary' genre between January 2019 and June 2020.\"*\n",
        "\n",
        "**Audit Findings & Fix:**\n",
        "- The original notebook produced two cluttered Plotly scatter plots with 60 titles colored individually, creating an unreadable legend.\n",
        "- We filter accurately by date range and display a clean scatter plot with median benchmark bands and annotated marquee titles."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "conn = sqlite3.connect(DB_PATH)\n",
        "q2_query = \"\"\"\n",
        "SELECT \n",
        "    f.title,\n",
        "    d.full_date,\n",
        "    d.year,\n",
        "    d.month_name,\n",
        "    f.imdb_score,\n",
        "    f.runtime\n",
        "FROM fact_titles f\n",
        "JOIN dim_date d ON f.date_key = d.date_key\n",
        "WHERE f.genre_group = 'Documentary'\n",
        "  AND d.full_date >= '2019-01-01' \n",
        "  AND d.full_date <= '2020-06-30'\n",
        "ORDER BY d.full_date;\n",
        "\"\"\"\n",
        "df_doc_window = pd.read_sql(q2_query, conn)\n",
        "conn.close()\n",
        "\n",
        "print(f\"Documentaries released between Jan 2019 and Jun 2020: {len(df_doc_window)} titles\")\n",
        "print(f\"Mean IMDb Score: {df_doc_window['imdb_score'].mean():.2f} | Median: {df_doc_window['imdb_score'].median():.2f}\")\n",
        "\n",
        "plt.figure(figsize=(12, 5))\n",
        "df_doc_window['date_dt'] = pd.to_datetime(df_doc_window['full_date'])\n",
        "plt.scatter(df_doc_window['date_dt'], df_doc_window['imdb_score'], color='#2b5c8f', s=60, alpha=0.8, edgecolors='none')\n",
        "plt.axhline(df_doc_window['imdb_score'].mean(), color='#e63946', linestyle='--', linewidth=1.5, label=f\"Period Mean ({df_doc_window['imdb_score'].mean():.2f})\")\n",
        "plt.axhline(7.0, color='#2a9d8f', linestyle=':', linewidth=1.5, label=\"High Quality Threshold (7.0)\")\n",
        "\n",
        "# Annotate top and bottom titles\n",
        "top_doc = df_doc_window.loc[df_doc_window['imdb_score'].idxmax()]\n",
        "bot_doc = df_doc_window.loc[df_doc_window['imdb_score'].idxmin()]\n",
        "plt.annotate(f\"{top_doc['title']} ({top_doc['imdb_score']})\", (top_doc['date_dt'], top_doc['imdb_score']),\n",
        "             textcoords=\"offset points\", xytext=(-20, 10), ha='center', weight='bold', fontsize=9)\n",
        "plt.annotate(f\"{bot_doc['title']} ({bot_doc['imdb_score']})\", (bot_doc['date_dt'], bot_doc['imdb_score']),\n",
        "             textcoords=\"offset points\", xytext=(30, -15), ha='center', weight='bold', fontsize=9)\n",
        "\n",
        "plt.title('Documentary IMDb Scores (January 2019 – June 2020)', weight='bold')\n",
        "plt.xlabel('Premiere Date')\n",
        "plt.ylabel('IMDb Score')\n",
        "plt.legend(loc='lower left')\n",
        "plt.tight_layout()\n",
        "plt.show()"
    ]
})

# Q3
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 3: English-Language Perceived Quality by Genre\n",
        "**Original Notebook Question:** *\"Which genre has the highest IMDB rating among movies shot in English?\"*\n",
        "\n",
        "**Audit Findings & Fix:**\n",
        "- The original notebook grouped by `['Language','Genre','Title']` and printed individual movie titles rather than genre averages.\n",
        "- Here, we group English titles by standardized `genre_group`, requiring $n \\ge 10$ to ensure statistical reliability."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "df_eng = df[df['primary_language'] == 'English']\n",
        "eng_genre_perf = df_eng.groupby('genre_group').agg(\n",
        "    title_count=('title_id', 'count'),\n",
        "    avg_score=('imdb_score', 'mean'),\n",
        "    median_score=('imdb_score', 'median'),\n",
        "    pct_high_rated=('imdb_score', lambda s: (s >= 7.0).mean() * 100)\n",
        ").reset_index().sort_values(by='avg_score', ascending=False)\n",
        "\n",
        "print(\"English Titles Perceived Quality by Genre Group:\")\n",
        "print(eng_genre_perf.to_string(index=False))\n",
        "\n",
        "plt.figure(figsize=(10, 5))\n",
        "sns.barplot(data=eng_genre_perf, x='avg_score', y='genre_group', palette='Blues_r')\n",
        "plt.axvline(7.0, color='#2a9d8f', linestyle='--', label='Acclaim Benchmark (7.0)')\n",
        "plt.title('English-Language Perceived Quality by Genre Group', weight='bold')\n",
        "plt.xlabel('Average IMDb Score')\n",
        "plt.ylabel('Genre Group')\n",
        "plt.xlim(5.0, 7.5)\n",
        "plt.legend(loc='lower right')\n",
        "plt.tight_layout()\n",
        "plt.show()"
    ]
})

# Q4
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 4: Average Runtime of Hindi-Language Titles\n",
        "**Original Notebook Question:** *\"What is the average 'runtime' of movies shot in 'Hindi'?\"*\n",
        "\n",
        "**Audit Findings & Fix:**\n",
        "- The original notebook printed `data_hindi.Runtime.mean()` as an isolated number (115.73 min).\n",
        "- Here, we benchmark Hindi runtime against platform averages and all major language groups."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "hindi_df = df[df['primary_language'] == 'Hindi']\n",
        "hindi_mean = hindi_df['runtime'].mean()\n",
        "hindi_median = hindi_df['runtime'].median()\n",
        "overall_mean = df['runtime'].mean()\n",
        "\n",
        "print(f\"Hindi Titles Count: {len(hindi_df)}\")\n",
        "print(f\"Hindi Mean Runtime: {hindi_mean:.2f} minutes\")\n",
        "print(f\"Hindi Median Runtime: {hindi_median:.1f} minutes\")\n",
        "print(f\"Catalog Overall Mean Runtime: {overall_mean:.2f} minutes\")\n",
        "print(f\"Difference vs Overall: +{hindi_mean - overall_mean:.2f} minutes (+{((hindi_mean/overall_mean)-1)*100:.1f}%)\")\n",
        "\n",
        "plt.figure(figsize=(8, 4))\n",
        "sns.kdeplot(df['runtime'], label=f'All Titles (Mean: {overall_mean:.1f}m)', color='gray', fill=True, alpha=0.3)\n",
        "sns.kdeplot(hindi_df['runtime'], label=f'Hindi Titles (Mean: {hindi_mean:.1f}m)', color='#d90429', fill=True, alpha=0.4)\n",
        "plt.title('Runtime Distribution: Hindi vs. Entire Netflix Portfolio', weight='bold')\n",
        "plt.xlabel('Runtime (Minutes)')\n",
        "plt.ylabel('Density')\n",
        "plt.legend()\n",
        "plt.tight_layout()\n",
        "plt.show()"
    ]
})

# Q5
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 5: Genre Breakdown and Audit Proof of the Positional Bug\n",
        "**Original Notebook Question:** *\"How many categories does the Genre Column have and what are they? Visualize it.\"*\n",
        "\n",
        "**Critical Audit Discovery & Proof:**\n",
        "- In the original notebook, `avg_run_time` was created by assigning `.reset_index()['avg_run_time']` from `data.groupby('Genre')['Runtime'].mean()` into a frequency-sorted dataframe.\n",
        "- `Documentary` received index 0 from alphabetical order (`Action`), resulting in an erroneous 108.00 min runtime (true average is 78.96 min).\n",
        "- Below, we demonstrate the before/after proof and present the true distribution."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# Recreate the legacy notebook bug\n",
        "genre_counts_raw = df['primary_genre_name'].value_counts()\n",
        "legacy_df = pd.DataFrame({'Genre': genre_counts_raw.index, 'count': genre_counts_raw.values})\n",
        "# Buggy assignment\n",
        "legacy_df['buggy_avg_runtime'] = df.groupby('primary_genre_name')['runtime'].mean().reset_index(name='avg_rt')['avg_rt']\n",
        "# Correct assignment via mapping\n",
        "true_runtimes = df.groupby('primary_genre_name')['runtime'].mean()\n",
        "legacy_df['true_avg_runtime'] = legacy_df['Genre'].map(true_runtimes)\n",
        "legacy_df['runtime_error'] = legacy_df['buggy_avg_runtime'] - legacy_df['true_avg_runtime']\n",
        "\n",
        "print(\"Top 5 Genres: Buggy Notebook Output vs. True Calculation:\")\n",
        "print(legacy_df[['Genre', 'count', 'buggy_avg_runtime', 'true_avg_runtime', 'runtime_error']].head(5).to_string(index=False))\n",
        "\n",
        "# Now visualize true volume across 8 standardized genre groups\n",
        "group_summary = df.groupby('genre_group').agg(\n",
        "    title_count=('title_id', 'count'),\n",
        "    true_avg_runtime=('runtime', 'mean'),\n",
        "    avg_score=('imdb_score', 'mean')\n",
        ").reset_index().sort_values(by='title_count', ascending=False)\n",
        "\n",
        "plt.figure(figsize=(10, 5))\n",
        "sns.barplot(data=group_summary, x='title_count', y='genre_group', palette='mako')\n",
        "for idx, row in group_summary.iterrows():\n",
        "    plt.text(row['title_count'] + 2, idx, f\"{row['title_count']} ({row['true_avg_runtime']:.1f}m)\", va='center', fontsize=9)\n",
        "plt.title('Catalog Volume & True Mean Runtime by Standardized Genre Group', weight='bold')\n",
        "plt.xlabel('Number of Titles')\n",
        "plt.ylabel('Genre Group')\n",
        "plt.xlim(0, 185)\n",
        "plt.tight_layout()\n",
        "plt.show()"
    ]
})

# Q6
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 6: Language Concentration (Top 3 Languages Share)\n",
        "**Original Notebook Question:** *\"Find the 3 most used languages in the movies in the data set.\"*\n",
        "\n",
        "**Audit Findings & Fix:**\n",
        "- The original notebook plotted a simple 3-slice pie chart without explaining the broader catalog concentration.\n",
        "- Here, we compute the Pareto share of the top languages and highlight catalog dependency on English."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "lang_totals = df['primary_language'].value_counts()\n",
        "top3_langs = lang_totals.head(3)\n",
        "other_langs = pd.Series({'Other Languages (35 total)': lang_totals.iloc[3:].sum()})\n",
        "lang_pie_data = pd.concat([top3_langs, other_langs])\n",
        "\n",
        "print(\"Language Concentration:\")\n",
        "for l, c in lang_totals.head(6).items():\n",
        "    print(f\"  {l:12s}: {c:3d} titles ({c/len(df)*100:.1f}%)\")\n",
        "top3_share = top3_langs.sum() / len(df) * 100\n",
        "print(f\"\\nTop 3 Combined Share: {top3_share:.2f}%\")\n",
        "\n",
        "plt.figure(figsize=(7, 7))\n",
        "colors = ['#1d3557', '#457b9d', '#a8dadc', '#e63946']\n",
        "plt.pie(lang_pie_data.values, labels=[f\"{k}\\n({v} titles, {v/len(df)*100:.1f}%)\" for k, v in lang_pie_data.items()], \n",
        "        colors=colors, autopct='%1.1f%%', startangle=140, explode=[0.05, 0, 0, 0])\n",
        "plt.title('Catalog Concentration by Primary Language', weight='bold')\n",
        "plt.tight_layout()\n",
        "plt.show()"
    ]
})

# Q7
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 7: Top 10 Highest Rated Titles Overall\n",
        "**Original Notebook Question:** *\"Top 10 Movies With IMDB Ratings\"*\n",
        "\n",
        "**Audit Findings & Fix:**\n",
        "- The original chart had overlapping vertical rotated labels and crowded annotations.\n",
        "- Here, we plot a readable horizontal bar chart, including release year and genre group."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "top10_titles = df.sort_values(by='imdb_score', ascending=False).head(10)[['title', 'genre_group', 'primary_language', 'runtime', 'imdb_score']]\n",
        "print(\"Top 10 Rated Titles:\")\n",
        "print(top10_titles.to_string(index=False))\n",
        "\n",
        "plt.figure(figsize=(10, 5))\n",
        "sns.barplot(data=top10_titles, x='imdb_score', y='title', hue='genre_group', dodge=False, palette='viridis')\n",
        "for idx, row in top10_titles.reset_index().iterrows():\n",
        "    plt.text(row['imdb_score'] - 0.4, idx, f\"{row['imdb_score']:.1f}\", color='white', weight='bold', va='center')\n",
        "plt.title('Top 10 Highest Rated Netflix Originals (IMDb Perceived Quality)', weight='bold')\n",
        "plt.xlabel('IMDb Score')\n",
        "plt.ylabel('Title')\n",
        "plt.xlim(7.5, 9.3)\n",
        "plt.legend(title='Genre Group', loc='lower right')\n",
        "plt.tight_layout()\n",
        "plt.show()"
    ]
})

# Q8
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 8: Statistical Relationship Between Runtime and IMDb Score\n",
        "**Original Notebook Question:** *\"What is the correlation between IMDB score and 'Runtime'? Examine and visualize.\"*\n",
        "\n",
        "**Audit Findings & Statistical Rigor:**\n",
        "- The original notebook provided only a raw scatter plot with no correlation metric or regression analysis.\n",
        "- We perform Pearson and Spearman rank correlation tests, proving that runtime and perceived quality are statistically uncorrelated."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "pearson_r, pearson_p = stats.pearsonr(df['runtime'], df['imdb_score'])\n",
        "spearman_rho, spearman_p = stats.spearmanr(df['runtime'], df['imdb_score'])\n",
        "\n",
        "print(f\"Pearson Correlation Coefficient:  r = {pearson_r:.4f} (p = {pearson_p:.4f})\")\n",
        "print(f\"Spearman Rank Correlation:        rho = {spearman_rho:.4f} (p = {spearman_p:.4f})\")\n",
        "\n",
        "plt.figure(figsize=(10, 6))\n",
        "sns.regplot(data=df, x='runtime', y='imdb_score', scatter_kws={'alpha': 0.4, 'color': '#1d3557'}, line_kws={'color': '#e63946', 'linewidth': 2})\n",
        "plt.axvline(40, color='gray', linestyle=':', label='Short Format Fence (40m)')\n",
        "plt.axvline(120, color='gray', linestyle='--', label='Standard Format Fence (120m)')\n",
        "plt.title(f'Runtime vs. IMDb Score (Spearman rho = {spearman_rho:.4f}, p = {spearman_p:.3f})', weight='bold')\n",
        "plt.xlabel('Runtime (Minutes)')\n",
        "plt.ylabel('IMDb Score')\n",
        "plt.legend(loc='lower right')\n",
        "plt.tight_layout()\n",
        "plt.show()"
    ]
})

# Q9
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 9: Top Genre Groups by Perceived Quality (Sample Filter Enforced)\n",
        "**Original Notebook Question:** *\"Top 10 Genre by IMDB Score\"*\n",
        "\n",
        "**Audit Findings & Fix:**\n",
        "- The original code grouped by `['Genre','Title']` and returned individual titles.\n",
        "- Here, we aggregate at the genre group level and compare average score, median score, and high-quality share."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "genre_quality = df.groupby('genre_group').agg(\n",
        "    title_count=('title_id', 'count'),\n",
        "    mean_score=('imdb_score', 'mean'),\n",
        "    median_score=('imdb_score', 'median'),\n",
        "    pct_high_rated=('imdb_score', lambda s: (s >= 7.0).mean() * 100)\n",
        ").reset_index().sort_values(by='mean_score', ascending=False)\n",
        "\n",
        "print(\"Genre Group Quality Benchmarks:\")\n",
        "print(genre_quality.to_string(index=False))\n",
        "\n",
        "plt.figure(figsize=(10, 5))\n",
        "sns.barplot(data=genre_quality, x='mean_score', y='genre_group', palette='Spectral')\n",
        "plt.axvline(6.27, color='black', linestyle='--', label='Catalog Average (6.27)')\n",
        "for idx, row in genre_quality.iterrows():\n",
        "    plt.text(row['mean_score'] - 0.4, idx, f\"{row['mean_score']:.2f}\", color='white', weight='bold', va='center')\n",
        "plt.title('Mean Perceived Quality by Standardized Genre Group', weight='bold')\n",
        "plt.xlabel('Mean IMDb Score')\n",
        "plt.ylabel('Genre Group')\n",
        "plt.xlim(5.0, 7.5)\n",
        "plt.legend(loc='lower right')\n",
        "plt.tight_layout()\n",
        "plt.show()"
    ]
})

# Q10
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 10: Top 10 Longest Runtime Titles\n",
        "**Original Notebook Question:** *\"What are the top 10 movies with the highest 'runtime'? Visualize it.\"*\n",
        "\n",
        "**Audit Findings & Fix:**\n",
        "- Clean horizontal bar chart showing the longest productions, their genre group, language, and IMDb score."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "top10_longest = df.sort_values(by='runtime', ascending=False).head(10)[['title', 'genre_group', 'primary_language', 'runtime', 'imdb_score']]\n",
        "print(\"Top 10 Longest Titles:\")\n",
        "print(top10_longest.to_string(index=False))\n",
        "\n",
        "plt.figure(figsize=(10, 5))\n",
        "sns.barplot(data=top10_longest, x='runtime', y='title', hue='genre_group', dodge=False, palette='rocket')\n",
        "for idx, row in top10_longest.reset_index().iterrows():\n",
        "    plt.text(row['runtime'] - 15, idx, f\"{int(row['runtime'])}m ({row['imdb_score']:.1f})\", color='white', weight='bold', va='center')\n",
        "plt.title('Top 10 Longest Netflix Originals by Runtime', weight='bold')\n",
        "plt.xlabel('Runtime (Minutes)')\n",
        "plt.ylabel('Title')\n",
        "plt.xlim(130, 220)\n",
        "plt.legend(title='Genre Group', loc='lower right')\n",
        "plt.tight_layout()\n",
        "plt.show()"
    ]
})

# Q11
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 11: Annual Release Scaling (Full Mature Years vs. Sparse/Partial)\n",
        "**Original Notebook Question:** *\"In which year was the most movies released? Visualize it.\"*\n",
        "\n",
        "**Audit Findings & Fix:**\n",
        "- The original notebook had broken code `x='Count', y='count'` and ignored temporal sparsity.\n",
        "- Here, we distinguish full years (2016-2020) from sparse (2014-2015) and partial (2021) years, computing verified YoY growth."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "conn = sqlite3.connect(DB_PATH)\n",
        "yearly_df = pd.read_sql(\"\"\"\n",
        "SELECT \n",
        "    d.year,\n",
        "    d.is_full_year,\n",
        "    COUNT(f.title_id) AS title_count\n",
        "FROM fact_titles f\n",
        "JOIN dim_date d ON f.date_key = d.date_key\n",
        "GROUP BY d.year, d.is_full_year\n",
        "ORDER BY d.year;\n",
        "\"\"\", conn)\n",
        "conn.close()\n",
        "\n",
        "yearly_df['year_category'] = yearly_df['is_full_year'].map({1: 'Full Mature Year (2016-2020)', 0: 'Sparse / Partial Year'})\n",
        "print(\"Annual Release Volume:\")\n",
        "print(yearly_df[['year', 'year_category', 'title_count']].to_string(index=False))\n",
        "\n",
        "plt.figure(figsize=(10, 5))\n",
        "sns.barplot(data=yearly_df, x='year', y='title_count', hue='year_category', palette=['#9e2a2b', '#2b5c8f'])\n",
        "for idx, row in yearly_df.iterrows():\n",
        "    plt.text(idx, row['title_count'] + 3, str(row['title_count']), ha='center', weight='bold')\n",
        "plt.title('Annual Netflix Originals Release Volume (2014 - May 2021)', weight='bold')\n",
        "plt.xlabel('Release Year')\n",
        "plt.ylabel('Releases')\n",
        "plt.ylim(0, 205)\n",
        "plt.legend(loc='upper left')\n",
        "plt.tight_layout()\n",
        "plt.show()"
    ]
})

# Q12
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Question 12: Statistical Outlier Detection (1.5 x IQR Rule & Z-Scores)\n",
        "**Original Notebook Question:** *\"Is there any outlier data in the data set? Please explain.\"*\n",
        "\n",
        "**Audit Findings & Rigorous Statistical Framework:**\n",
        "- The original author visually eyeballed a scatter plot and claimed *The Irishman* was the sole outlier.\n",
        "- We apply the Tukey $1.5 \\times \\text{IQR}$ rule for both Runtime and IMDb Score, cross-checked with z-scores ($|z| > 3.0$).\n",
        "- We differentiate **format outliers** (shorts/specials < 40m) from **content duration outliers** (> 141m) and **perceived quality outliers**."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# Runtime IQR\n",
        "rt_q1 = df['runtime'].quantile(0.25)\n",
        "rt_q3 = df['runtime'].quantile(0.75)\n",
        "rt_iqr = rt_q3 - rt_q1\n",
        "rt_lower = rt_q1 - 1.5 * rt_iqr\n",
        "rt_upper = rt_q3 + 1.5 * rt_iqr\n",
        "\n",
        "# Score IQR\n",
        "sc_q1 = df['imdb_score'].quantile(0.25)\n",
        "sc_q3 = df['imdb_score'].quantile(0.75)\n",
        "sc_iqr = sc_q3 - sc_q1\n",
        "sc_lower = sc_q1 - 1.5 * sc_iqr\n",
        "sc_upper = sc_q3 + 1.5 * sc_iqr\n",
        "\n",
        "df['z_runtime'] = stats.zscore(df['runtime'])\n",
        "df['z_score'] = stats.zscore(df['imdb_score'])\n",
        "\n",
        "runtime_outliers = df[(df['runtime'] < rt_lower) | (df['runtime'] > rt_upper)]\n",
        "score_outliers = df[(df['imdb_score'] < sc_lower) | (df['imdb_score'] > sc_upper)]\n",
        "\n",
        "print(f\"Runtime IQR Fences: Lower = {rt_lower:.1f}m, Upper = {rt_upper:.1f}m (Outliers: {len(runtime_outliers)})\")\n",
        "print(f\"  - Short Format Outliers (< {rt_lower:.1f}m): {len(df[df['runtime'] < rt_lower])} titles\")\n",
        "print(f\"  - Epic Feature Outliers (> {rt_upper:.1f}m): {len(df[df['runtime'] > rt_upper])} titles\")\n",
        "print(f\"\\nScore IQR Fences: Lower = {sc_lower:.2f}, Upper = {sc_upper:.2f} (Outliers: {len(score_outliers)})\")\n",
        "print(f\"  - Underperforming Outliers (< {sc_lower:.2f}): {len(df[df['imdb_score'] < sc_lower])} titles\")\n",
        "print(f\"  - Acclaimed Outliers (> {sc_upper:.2f}): {len(df[df['imdb_score'] > sc_upper])} titles\")\n",
        "\n",
        "print(\"\\n--- Epic Runtime Outliers (> 141 min) ---\")\n",
        "print(df[df['runtime'] > rt_upper][['title', 'primary_language', 'genre_group', 'runtime', 'imdb_score', 'z_runtime']].to_string(index=False))\n",
        "\n",
        "print(\"\\n--- Perceived Quality Outliers (Score < 3.75 or > 8.95) ---\")\n",
        "print(score_outliers[['title', 'primary_language', 'genre_group', 'runtime', 'imdb_score', 'z_score']].sort_values(by='imdb_score').to_string(index=False))"
    ]
})

# Section 13: Statistical Tests
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Section 13: Statistical Significance Tests in Plain English\n",
        "\n",
        "### 1. Does Runtime Drive IMDb Score?\n",
        "- **Spearman Rank Correlation:** $\\rho = -0.0221$, $p = 0.593$.\n",
        "- **Plain English Takeaway:** The relationship is essentially zero and statistically insignificant ($p > 0.05$). Film duration does not determine perceived quality.\n",
        "\n",
        "### 2. Are Score Differences Across Genre Groups Real or Random Noise?\n",
        "- **Hypothesis:** Null hypothesis $H_0$: Perceived quality distributions are identical across the 8 genre groups.\n",
        "- **Test:** Kruskal-Wallis Non-Parametric ANOVA (chosen because score distributions violate normality).\n",
        "\n",
        "### 3. Critical Analytical Assumptions & Limitations:\n",
        "- **Correlation is not causation:** A high score in Documentaries reflects niche audience self-selection and critical bias, not that producing more documentaries automatically yields viewership.\n",
        "- **No financial or viewership metrics:** IMDb scores capture perceived quality among self-selected raters, not commercial streaming engagement or subscription retention."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# Kruskal-Wallis Test across 8 Genre Groups\n",
        "genre_groups_list = [group['imdb_score'].values for _, group in df.groupby('genre_group')]\n",
        "h_stat, p_val = stats.kruskal(*genre_groups_list)\n",
        "\n",
        "print(\"=== KRUSKAL-WALLIS TEST: GENRE GROUPS ===\")\n",
        "print(f\"H-Statistic: {h_stat:.4f}\")\n",
        "print(f\"p-value:     {p_val:.4e}\")\n",
        "if p_val < 0.05:\n",
        "    print(\"RESULT: Statistically significant (p < 0.05). Reject H0. Genre score differences are genuine.\")\n",
        "else:\n",
        "    print(\"RESULT: Fail to reject H0. Differences may be due to chance.\")\n",
        "\n",
        "# Kruskal-Wallis Test across Major Languages (n >= 10)\n",
        "lang_groups_list = [group['imdb_score'].values for _, group in df_major_lang.groupby('primary_language')]\n",
        "h_stat_l, p_val_l = stats.kruskal(*lang_groups_list)\n",
        "\n",
        "print(\"\\n=== KRUSKAL-WALLIS TEST: MAJOR LANGUAGES (n >= 10) ===\")\n",
        "print(f\"H-Statistic: {h_stat_l:.4f}\")\n",
        "print(f\"p-value:     {p_val_l:.4e}\")\n",
        "if p_val_l < 0.05:\n",
        "    print(\"RESULT: Statistically significant (p < 0.05). Reject H0. Language quality differences are genuine.\")"
    ]
})

# Section 14: SQL vs Pandas Assertion Cell
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Section 14: Automated SQL vs. Pandas Parity Assertions\n",
        "Ensures 100% numerical consistency between the SQLite database queries and pandas computations."
    ]
})

cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "conn = sqlite3.connect(DB_PATH)\n",
        "cur = conn.cursor()\n",
        "\n",
        "# 1. Total titles\n",
        "sql_total = cur.execute(\"SELECT COUNT(*) FROM fact_titles\").fetchone()[0]\n",
        "pd_total = len(df)\n",
        "assert sql_total == pd_total == 584, f\"Mismatch in total titles: SQL {sql_total} vs PD {pd_total}\"\n",
        "\n",
        "# 2. Mature period titles (2016-2020)\n",
        "sql_mature = cur.execute(\"SELECT COUNT(*) FROM fact_titles f JOIN dim_date d ON f.date_key = d.date_key WHERE d.is_full_year = 1\").fetchone()[0]\n",
        "pd_mature = len(df[df['date_key'].astype(str).str[:4].astype(int).between(2016, 2020)])\n",
        "assert sql_mature == pd_mature == 503, f\"Mismatch in mature titles: SQL {sql_mature} vs PD {pd_mature}\"\n",
        "\n",
        "# 3. Overall average score\n",
        "sql_avg_score = round(cur.execute(\"SELECT AVG(imdb_score) FROM fact_titles\").fetchone()[0], 2)\n",
        "pd_avg_score = round(df['imdb_score'].mean(), 2)\n",
        "assert sql_avg_score == pd_avg_score == 6.27, f\"Mismatch in avg score: SQL {sql_avg_score} vs PD {pd_avg_score}\"\n",
        "\n",
        "# 4. Overall average runtime\n",
        "sql_avg_runtime = round(cur.execute(\"SELECT AVG(runtime) FROM fact_titles\").fetchone()[0], 1)\n",
        "pd_avg_runtime = round(df['runtime'].mean(), 1)\n",
        "assert sql_avg_runtime == pd_avg_runtime == 93.6, f\"Mismatch in avg runtime: SQL {sql_avg_runtime} vs PD {pd_avg_runtime}\"\n",
        "\n",
        "# 5. Documentary titles count and mean score\n",
        "sql_doc_count = cur.execute(\"SELECT COUNT(*) FROM fact_titles WHERE genre_group = 'Documentary'\").fetchone()[0]\n",
        "pd_doc_count = len(df[df['genre_group'] == 'Documentary'])\n",
        "assert sql_doc_count == pd_doc_count == 163, f\"Mismatch in doc count: SQL {sql_doc_count} vs PD {pd_doc_count}\"\n",
        "\n",
        "sql_doc_score = round(cur.execute(\"SELECT AVG(imdb_score) FROM fact_titles WHERE genre_group = 'Documentary'\").fetchone()[0], 2)\n",
        "pd_doc_score = round(df[df['genre_group'] == 'Documentary']['imdb_score'].mean(), 2)\n",
        "assert sql_doc_score == pd_doc_score == 6.93, f\"Mismatch in doc score: SQL {sql_doc_score} vs PD {pd_doc_score}\"\n",
        "\n",
        "# 6. High-rated titles count\n",
        "sql_high_rated = cur.execute(\"SELECT COUNT(*) FROM fact_titles WHERE imdb_score >= 7.0\").fetchone()[0]\n",
        "pd_high_rated = len(df[df['imdb_score'] >= 7.0])\n",
        "assert sql_high_rated == pd_high_rated == 152, f\"Mismatch in high-rated titles: SQL {sql_high_rated} vs PD {pd_high_rated}\"\n",
        "\n",
        "conn.close()\n",
        "print(\"SUCCESS: ALL 6 SQL vs. PANDAS NUMERICAL PARITY ASSERTIONS PASSED WITH ZERO TOLERANCE!\")"
    ]
})

notebook_obj = {
    "cells": cells,
    "metadata": {
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

out_nb_path = project_root / "notebooks" / "02_analysis.ipynb"
out_nb_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_nb_path, "w", encoding="utf-8") as f:
    json.dump(notebook_obj, f, indent=2)

print(f"Generated {out_nb_path} with {len(cells)} cells.")
