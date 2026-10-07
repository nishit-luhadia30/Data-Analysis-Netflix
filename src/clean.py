"""
src/clean.py
Data Cleaning, Feature Engineering, and Star Schema Pipeline for Netflix Originals.

Outputs:
1. SQLite Database: netflix.db
2. Power BI Star Schema CSVs: data/processed/powerbi/*.csv
   - fact_titles.csv
   - dim_date.csv
   - dim_genre.csv
   - bridge_title_genre.csv
   - dim_language.csv
"""

import os
import csv
import sqlite3
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_CSV_PATH = os.path.join(BASE_DIR, "NetflixOriginals.csv")
GENRE_MAP_PATH = os.path.join(BASE_DIR, "data", "external", "genre_group_map.csv")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed", "powerbi")
DB_PATH = os.path.join(BASE_DIR, "netflix.db")

os.makedirs(PROCESSED_DIR, exist_ok=True)


def parse_date(date_str):
    """
    Parses dates like 'August 5, 2020' or 'October 16. 2019' (handling period typos).
    """
    cleaned = date_str.strip().replace('.', ',')
    cleaned = " ".join(cleaned.split())
    for fmt in ["%B %d, %Y", "%d-%b-%y", "%b %d, %Y", "%B %d %Y"]:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unable to parse date string: '{date_str}'")


def load_genre_map(map_path):
    genre_group_map = {}
    with open(map_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            genre_group_map[r['raw_genre'].strip()] = r['genre_group'].strip()
    return genre_group_map


def clean_and_transform():
    print(f"Reading raw data from: {RAW_CSV_PATH}")
    genre_group_map = load_genre_map(GENRE_MAP_PATH)

    raw_records = []
    with open(RAW_CSV_PATH, mode='r', encoding='latin-1') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_records.append(row)

    print(f"Loaded {len(raw_records)} raw records.")

    # Distinct lookups to build dimensions
    genres_dict = {}  # genre_name -> {genre_id, genre_name, genre_group}
    languages_dict = {}  # language_name -> {language_id, language_name}
    date_dict = {}  # date_str_key -> dim_date record

    genre_id_counter = 1
    language_id_counter = 1

    # First pass: collect unique atomic genres and atomic languages
    for row in raw_records:
        raw_genre = row['Genre'].strip()
        raw_lang = row['Language'].strip()

        # Split compound genres
        g_parts = [p.strip() for p in raw_genre.split('/') if p.strip()]
        for g in g_parts:
            if g not in genres_dict:
                # determine genre group
                group = genre_group_map.get(raw_genre, genre_group_map.get(g, "Other"))
                genres_dict[g] = {
                    "genre_id": genre_id_counter,
                    "genre_name": g,
                    "genre_group": group
                }
                genre_id_counter += 1

        # Split compound languages
        l_parts = [p.strip() for p in raw_lang.split('/') if p.strip()]
        for l in l_parts:
            if l not in languages_dict:
                languages_dict[l] = {
                    "language_id": language_id_counter,
                    "language_name": l
                }
                language_id_counter += 1

    # Prepare tables
    fact_titles = []
    bridge_title_genre = []

    for idx, row in enumerate(raw_records, start=1):
        title_id = idx
        title = row['Title'].strip()
        raw_genre = row['Genre'].strip()
        raw_lang = row['Language'].strip()
        runtime = float(row['Runtime'])
        score = float(row['IMDB Score'])

        # Date transformations
        dt = parse_date(row['Premiere'])
        date_key = int(dt.strftime("%Y%m%d"))
        if date_key not in date_dict:
            quarter = (dt.month - 1) // 3 + 1
            # 2014, 2015, and 2021 are not full years
            is_full = 1 if 2016 <= dt.year <= 2020 else 0
            is_weekend = 1 if dt.weekday() in (5, 6) else 0
            date_dict[date_key] = {
                "date_key": date_key,
                "full_date": dt.strftime("%Y-%m-%d"),
                "year": dt.year,
                "quarter": f"Q{quarter}",
                "month_num": dt.month,
                "month_name": dt.strftime("%B"),
                "day_of_month": dt.day,
                "day_of_week": dt.weekday() + 1,  # 1 = Monday
                "weekday_name": dt.strftime("%A"),
                "is_weekend": is_weekend,
                "is_full_year": is_full
            }

        # Genre parsing and bridge creation
        g_parts = [p.strip() for p in raw_genre.split('/') if p.strip()]
        primary_genre_name = g_parts[0]
        primary_genre_id = genres_dict[primary_genre_name]["genre_id"]
        primary_genre_group = genre_group_map.get(raw_genre, genres_dict[primary_genre_name]["genre_group"])

        for g_order, g in enumerate(g_parts):
            bridge_title_genre.append({
                "title_id": title_id,
                "genre_id": genres_dict[g]["genre_id"],
                "is_primary": 1 if g_order == 0 else 0
            })

        # Language parsing
        l_parts = [p.strip() for p in raw_lang.split('/') if p.strip()]
        primary_lang_name = l_parts[0]
        primary_language_id = languages_dict[primary_lang_name]["language_id"]
        is_multilingual = 1 if len(l_parts) > 1 else 0

        # Runtime Bucketing
        # <40 min: Short / Special (aftershows, shorts, anthologies)
        # 40-120 min: Standard Feature
        # >120 min: Long / Epic Feature
        if runtime < 40:
            runtime_bucket = "Short/Special (<40m)"
        elif runtime <= 120:
            runtime_bucket = "Standard (40-120m)"
        else:
            runtime_bucket = "Long (>120m)"

        # Score Bucketing
        # <5.5: Low (underperforming quality)
        # 5.5 - 6.9: Mid (average / standard release)
        # >=7.0: High (critically acclaimed / top perceived quality)
        if score < 5.5:
            score_bucket = "Low (<5.5)"
        elif score < 7.0:
            score_bucket = "Mid (5.5-6.9)"
        else:
            score_bucket = "High (>=7.0)"

        fact_titles.append({
            "title_id": title_id,
            "title": title,
            "date_key": date_key,
            "primary_genre_id": primary_genre_id,
            "primary_genre_name": primary_genre_name,
            "genre_group": primary_genre_group,
            "primary_language_id": primary_language_id,
            "primary_language": primary_lang_name,
            "is_multilingual": is_multilingual,
            "runtime": runtime,
            "runtime_bucket": runtime_bucket,
            "imdb_score": score,
            "score_bucket": score_bucket
        })

    # Convert lookups to lists
    dim_date = sorted(date_dict.values(), key=lambda x: x["date_key"])
    dim_genre = sorted(genres_dict.values(), key=lambda x: x["genre_id"])
    dim_language = sorted(languages_dict.values(), key=lambda x: x["language_id"])

    print(f"\n--- Transformation Summary ---")
    print(f"fact_titles: {len(fact_titles)} rows")
    print(f"dim_date: {len(dim_date)} unique dates")
    print(f"dim_genre: {len(dim_genre)} unique atomic genres")
    print(f"bridge_title_genre: {len(bridge_title_genre)} title-genre associations")
    print(f"dim_language: {len(dim_language)} unique languages")

    # Export to CSV for Power BI
    export_csv(os.path.join(PROCESSED_DIR, "fact_titles.csv"), fact_titles)
    export_csv(os.path.join(PROCESSED_DIR, "dim_date.csv"), dim_date)
    export_csv(os.path.join(PROCESSED_DIR, "dim_genre.csv"), dim_genre)
    export_csv(os.path.join(PROCESSED_DIR, "bridge_title_genre.csv"), bridge_title_genre)
    export_csv(os.path.join(PROCESSED_DIR, "dim_language.csv"), dim_language)

    # Save to SQLite
    save_to_sqlite(DB_PATH, fact_titles, dim_date, dim_genre, bridge_title_genre, dim_language)
    print("\nData cleaning and SQLite database export complete.")


def export_csv(filepath, dict_list):
    if not dict_list:
        return
    fieldnames = list(dict_list[0].keys())
    with open(filepath, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dict_list)
    print(f"Exported {len(dict_list)} rows to {filepath}")


def save_to_sqlite(db_path, fact_titles, dim_date, dim_genre, bridge_title_genre, dim_language):
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create tables
    cur.execute("""
    CREATE TABLE dim_date (
        date_key INTEGER PRIMARY KEY,
        full_date TEXT NOT NULL,
        year INTEGER NOT NULL,
        quarter TEXT NOT NULL,
        month_num INTEGER NOT NULL,
        month_name TEXT NOT NULL,
        day_of_month INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL,
        weekday_name TEXT NOT NULL,
        is_weekend INTEGER NOT NULL,
        is_full_year INTEGER NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE dim_genre (
        genre_id INTEGER PRIMARY KEY,
        genre_name TEXT NOT NULL,
        genre_group TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE dim_language (
        language_id INTEGER PRIMARY KEY,
        language_name TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE fact_titles (
        title_id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        date_key INTEGER NOT NULL,
        primary_genre_id INTEGER NOT NULL,
        primary_genre_name TEXT NOT NULL,
        genre_group TEXT NOT NULL,
        primary_language_id INTEGER NOT NULL,
        primary_language TEXT NOT NULL,
        is_multilingual INTEGER NOT NULL,
        runtime REAL NOT NULL,
        runtime_bucket TEXT NOT NULL,
        imdb_score REAL NOT NULL,
        score_bucket TEXT NOT NULL,
        FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
        FOREIGN KEY (primary_genre_id) REFERENCES dim_genre(genre_id),
        FOREIGN KEY (primary_language_id) REFERENCES dim_language(language_id)
    );
    """)

    cur.execute("""
    CREATE TABLE bridge_title_genre (
        title_id INTEGER NOT NULL,
        genre_id INTEGER NOT NULL,
        is_primary INTEGER NOT NULL,
        PRIMARY KEY (title_id, genre_id),
        FOREIGN KEY (title_id) REFERENCES fact_titles(title_id),
        FOREIGN KEY (genre_id) REFERENCES dim_genre(genre_id)
    );
    """)

    # Helper inserter
    def insert_rows(table_name, rows):
        if not rows:
            return
        keys = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(keys))
        sql = f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({placeholders})"
        data = [[r[k] for k in keys] for r in rows]
        cur.executemany(sql, data)

    insert_rows("dim_date", dim_date)
    insert_rows("dim_genre", dim_genre)
    insert_rows("dim_language", dim_language)
    insert_rows("fact_titles", fact_titles)
    insert_rows("bridge_title_genre", bridge_title_genre)

    conn.commit()
    conn.close()
    print(f"Saved complete star schema to SQLite database: {db_path}")


if __name__ == "__main__":
    clean_and_transform()
