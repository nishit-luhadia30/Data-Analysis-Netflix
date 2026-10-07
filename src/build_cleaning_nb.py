import json
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Phase 1: Data Cleaning & Star Schema Pipeline\n",
                "**Netflix Originals Analytics Portfolio Project**\n",
                "\n",
                "This notebook documents the ingestion, transformation, feature engineering, and relational modeling of `NetflixOriginals.csv`.\n",
                "\n",
                "### Business Context & Objectives:\n",
                "- Client: Content Strategy Team at a streaming platform.\n",
                "- Objective: Transform uncurated raw CSV into a clean star schema with robust date dimensions, normalized bridge tables for compound genres, and analytical categorical buckets.\n",
                "- Target outputs: SQLite database (`netflix.db`) and CSV star schema in `data/processed/powerbi/`."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "import pandas as pd\n",
                "import numpy as np\n",
                "import sqlite3\n",
                "from datetime import datetime\n",
                "\n",
                "# Relative paths\n",
                "RAW_PATH = os.path.join(\"..\", \"NetflixOriginals.csv\")\n",
                "GENRE_MAP_PATH = os.path.join(\"..\", \"data\", \"external\", \"genre_group_map.csv\")\n",
                "PROCESSED_DIR = os.path.join(\"..\", \"data\", \"processed\", \"powerbi\")\n",
                "DB_PATH = os.path.join(\"..\", \"netflix.db\")\n",
                "\n",
                "print(f\"Raw dataset path: {RAW_PATH}\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 1. Data Ingestion & Initial Audit\n",
                "Read raw CSV with `encoding='latin-1'` as required by special characters in titles."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "df_raw = pd.read_csv(RAW_PATH, encoding='latin-1')\n",
                "print(f\"Dataset shape: {df_raw.shape[0]} rows, {df_raw.shape[1]} columns\")\n",
                "print(f\"Missing values per column:\\n{df_raw.isnull().sum()}\")\n",
                "print(f\"Unique titles: {df_raw['Title'].nunique()}\")\n",
                "assert df_raw.shape[0] == 584, \"Expected exactly 584 rows\"\n",
                "assert df_raw['Title'].nunique() == 584, \"All titles must be unique\"\n",
                "df_raw.head(3)"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2. Date Parsing & Temporal Dimensions\n",
                "- Handles formatting anomalies (5 rows have periods instead of commas, e.g. `October 16. 2019`).\n",
                "- Generates Date Key (`YYYYMMDD`), Year, Quarter, Month Name, Day of Week, and flags.\n",
                "- `is_full_year`: Flagged `1` for 2016-2020 (mature reporting period), `0` for sparse 2014-2015 and partial 2021."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Clean periods and standardize\n",
                "clean_dates = df_raw['Premiere'].str.replace('.', ',', regex=False).str.strip()\n",
                "parsed_dates = pd.to_datetime(clean_dates, format='mixed')\n",
                "\n",
                "df_clean = df_raw.copy()\n",
                "df_clean['premiere_date'] = parsed_dates\n",
                "df_clean['date_key'] = df_clean['premiere_date'].dt.strftime('%Y%m%d').astype(int)\n",
                "df_clean['year'] = df_clean['premiere_date'].dt.year\n",
                "df_clean['quarter'] = 'Q' + df_clean['premiere_date'].dt.quarter.astype(str)\n",
                "df_clean['month_num'] = df_clean['premiere_date'].dt.month\n",
                "df_clean['month_name'] = df_clean['premiere_date'].dt.month_name()\n",
                "df_clean['day_of_month'] = df_clean['premiere_date'].dt.day\n",
                "df_clean['day_of_week'] = df_clean['premiere_date'].dt.dayofweek + 1  # 1 = Monday\n",
                "df_clean['weekday_name'] = df_clean['premiere_date'].dt.day_name()\n",
                "df_clean['is_weekend'] = df_clean['day_of_week'].isin([6, 7]).astype(int)\n",
                "df_clean['is_full_year'] = df_clean['year'].between(2016, 2020).astype(int)\n",
                "\n",
                "print(\"Releases by year with full-year flag:\")\n",
                "print(df_clean.groupby(['year', 'is_full_year']).size().reset_index(name='title_count'))"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3. Genre Normalization, Bridge Table & Genre Grouping\n",
                "- 51 rows contain compound genres separated by `/`.\n",
                "- We construct `bridge_title_genre` to preserve many-to-many relationships without duplicating title metrics.\n",
                "- Primary genre rule: The first listed genre is designated as `is_primary = 1`.\n",
                "- Map all raw genres into 8 high-level analytical genre groups via `data/external/genre_group_map.csv`."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "genre_map_df = pd.read_csv(GENRE_MAP_PATH)\n",
                "genre_group_lookup = dict(zip(genre_map_df['raw_genre'], genre_map_df['genre_group']))\n",
                "\n",
                "# Assign Title ID\n",
                "df_clean['title_id'] = range(1, len(df_clean) + 1)\n",
                "\n",
                "# Parse genres\n",
                "bridge_rows = []\n",
                "atomic_genres = set()\n",
                "\n",
                "for _, row in df_clean.iterrows():\n",
                "    t_id = row['title_id']\n",
                "    raw_g = row['Genre'].strip()\n",
                "    parts = [p.strip() for p in raw_g.split('/') if p.strip()]\n",
                "    for idx, g in enumerate(parts):\n",
                "        atomic_genres.add(g)\n",
                "        bridge_rows.append({\n",
                "            'title_id': t_id,\n",
                "            'genre_name': g,\n",
                "            'is_primary': 1 if idx == 0 else 0\n",
                "        })\n",
                "\n",
                "df_bridge = pd.DataFrame(bridge_rows)\n",
                "\n",
                "# Create dim_genre\n",
                "sorted_genres = sorted(list(atomic_genres))\n",
                "genre_to_id = {g: i + 1 for i, g in enumerate(sorted_genres)}\n",
                "dim_genre = pd.DataFrame([\n",
                "    {\n",
                "        'genre_id': genre_to_id[g],\n",
                "        'genre_name': g,\n",
                "        'genre_group': genre_group_lookup.get(g, 'Other')\n",
                "    }\n",
                "    for g in sorted_genres\n",
                "])\n",
                "\n",
                "df_bridge['genre_id'] = df_bridge['genre_name'].map(genre_to_id)\n",
                "df_bridge = df_bridge[['title_id', 'genre_id', 'is_primary']]\n",
                "\n",
                "# Primary genre info for fact table\n",
                "primary_genres = df_clean['Genre'].apply(lambda x: [p.strip() for p in x.split('/')][0])\n",
                "df_clean['primary_genre_name'] = primary_genres\n",
                "df_clean['primary_genre_id'] = df_clean['primary_genre_name'].map(genre_to_id)\n",
                "df_clean['genre_group'] = df_clean['Genre'].map(genre_group_lookup).fillna(df_clean['primary_genre_name'].map(lambda g: genre_group_lookup.get(g, 'Other')))\n",
                "\n",
                "print(f\"Unique atomic genres in dim_genre: {len(dim_genre)}\")\n",
                "print(f\"Total bridge rows: {len(df_bridge)}\")\n",
                "print(\"\\nDistribution across 8 Genre Groups:\")\n",
                "print(df_clean['genre_group'].value_counts())"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4. Language Normalization & Multilingual Flags\n",
                "- 23 rows contain compound languages separated by `/`.\n",
                "- We extract `primary_language` (first listed) and set `is_multilingual = 1` for compound entries."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "lang_parts = df_clean['Language'].apply(lambda x: [p.strip() for p in x.split('/') if p.strip()])\n",
                "df_clean['primary_language'] = lang_parts.apply(lambda parts: parts[0])\n",
                "df_clean['is_multilingual'] = lang_parts.apply(lambda parts: 1 if len(parts) > 1 else 0)\n",
                "\n",
                "unique_langs = sorted(df_clean['primary_language'].unique())\n",
                "lang_to_id = {l: i + 1 for i, l in enumerate(unique_langs)}\n",
                "dim_language = pd.DataFrame([\n",
                "    {'language_id': lang_to_id[l], 'language_name': l}\n",
                "    for l in unique_langs\n",
                "])\n",
                "df_clean['primary_language_id'] = df_clean['primary_language'].map(lang_to_id)\n",
                "\n",
                "print(f\"Primary languages count: {len(dim_language)}\")\n",
                "print(f\"Multilingual titles: {df_clean['is_multilingual'].sum()}\")\n",
                "print(\"\\nTop languages:\")\n",
                "print(df_clean['primary_language'].value_counts().head(6))"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 5. Analytical Bucketing & Feature Engineering\n",
                "We define two standard business categorical dimensions:\n",
                "1. **Runtime Buckets**:\n",
                "   - `Short/Special (<40m)`: Format variance (shorts, specials, aftershows).\n",
                "   - `Standard (40-120m)`: Standard feature release.\n",
                "   - `Long (>120m)`: Extended/epic release.\n",
                "2. **Score Buckets**:\n",
                "   - `Low (<5.5)`: Sub-par quality floor.\n",
                "   - `Mid (5.5-6.9)`: Solid average quality.\n",
                "   - `High (>=7.0)`: Acclaimed / marquee titles."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "def assign_runtime_bucket(rt):\n",
                "    if rt < 40:\n",
                "        return 'Short/Special (<40m)'\n",
                "    elif rt <= 120:\n",
                "        return 'Standard (40-120m)'\n",
                "    return 'Long (>120m)'\n",
                "\n",
                "def assign_score_bucket(sc):\n",
                "    if sc < 5.5:\n",
                "        return 'Low (<5.5)'\n",
                "    elif sc < 7.0:\n",
                "        return 'Mid (5.5-6.9)'\n",
                "    return 'High (>=7.0)'\n",
                "\n",
                "df_clean['runtime_bucket'] = df_clean['Runtime'].apply(assign_runtime_bucket)\n",
                "df_clean['score_bucket'] = df_clean['IMDB Score'].apply(assign_score_bucket)\n",
                "\n",
                "print(\"Runtime bucket distribution:\")\n",
                "print(df_clean['runtime_bucket'].value_counts())\n",
                "print(\"\\nScore bucket distribution:\")\n",
                "print(df_clean['score_bucket'].value_counts())"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 6. Star Schema Construction & Validation\n",
                "Construct and validate `fact_titles`, `dim_date`, `dim_genre`, `bridge_title_genre`, and `dim_language`."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Fact table\n",
                "fact_titles = df_clean[[\n",
                "    'title_id', 'Title', 'date_key', 'primary_genre_id', 'primary_genre_name',\n",
                "    'genre_group', 'primary_language_id', 'primary_language', 'is_multilingual',\n",
                "    'Runtime', 'runtime_bucket', 'IMDB Score', 'score_bucket'\n",
                "]].rename(columns={'Title': 'title', 'Runtime': 'runtime', 'IMDB Score': 'imdb_score'})\n",
                "\n",
                "# Dim date\n",
                "dim_date = df_clean[[\n",
                "    'date_key', 'premiere_date', 'year', 'quarter', 'month_num', 'month_name',\n",
                "    'day_of_month', 'day_of_week', 'weekday_name', 'is_weekend', 'is_full_year'\n",
                "]].drop_duplicates(subset=['date_key']).rename(columns={'premiere_date': 'full_date'}).sort_values('date_key')\n",
                "dim_date['full_date'] = dim_date['full_date'].dt.strftime('%Y-%m-%d')\n",
                "\n",
                "# Data validation assertions\n",
                "assert len(fact_titles) == 584, \"Fact titles count must be exactly 584\"\n",
                "assert fact_titles['title_id'].nunique() == 584, \"title_id must be unique PK\"\n",
                "assert df_bridge['title_id'].isin(fact_titles['title_id']).all(), \"No orphan title IDs in bridge\"\n",
                "assert df_bridge['genre_id'].isin(dim_genre['genre_id']).all(), \"No orphan genre IDs in bridge\"\n",
                "assert fact_titles['primary_language_id'].isin(dim_language['language_id']).all(), \"No orphan languages\"\n",
                "assert fact_titles['imdb_score'].between(0, 10).all(), \"Scores must be within [0, 10]\"\n",
                "\n",
                "print(\"ALL INTEGRITY & REFERENTIAL CONSTRAINTS PASSED SUCCESSFULLY!\")\n",
                "print(f\"fact_titles rows: {len(fact_titles)}\")\n",
                "print(f\"dim_date rows: {len(dim_date)}\")\n",
                "print(f\"dim_genre rows: {len(dim_genre)}\")\n",
                "print(f\"bridge_title_genre rows: {len(df_bridge)}\")\n",
                "print(f\"dim_language rows: {len(dim_language)}\")"
            ]
        }
    ],
    "metadata": {
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

out_nb_path = project_root / "notebooks" / "01_cleaning.ipynb"
out_nb_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_nb_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2)

print(f"Created {out_nb_path} successfully.")
