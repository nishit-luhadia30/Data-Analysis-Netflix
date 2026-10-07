-- ============================================================================
-- sql/quality_checks.sql
-- Automated Data Quality & Referential Integrity Verification Script
-- Target: SQLite (netflix.db)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- CHECK 1: Primary Key Uniqueness in fact_titles
-- Expected result: 0 rows (no duplicates)
-- ----------------------------------------------------------------------------
SELECT 
    'CHECK 1: Duplicate title_id' AS check_name,
    title_id, 
    COUNT(*) AS occurrence_count
FROM fact_titles
GROUP BY title_id
HAVING COUNT(*) > 1;

SELECT 
    'CHECK 1b: Duplicate Title names' AS check_name,
    title, 
    COUNT(*) AS occurrence_count
FROM fact_titles
GROUP BY title
HAVING COUNT(*) > 1;

-- ----------------------------------------------------------------------------
-- CHECK 2: Referential Integrity - Orphan keys in bridge_title_genre
-- Expected result: 0 rows (every title_id must exist in fact_titles)
-- ----------------------------------------------------------------------------
SELECT 
    'CHECK 2: Orphan title_id in bridge' AS check_name,
    b.title_id
FROM bridge_title_genre b
LEFT JOIN fact_titles f ON b.title_id = f.title_id
WHERE f.title_id IS NULL;

-- ----------------------------------------------------------------------------
-- CHECK 3: Referential Integrity - Orphan genre_id in bridge_title_genre
-- Expected result: 0 rows (every genre_id must exist in dim_genre)
-- ----------------------------------------------------------------------------
SELECT 
    'CHECK 3: Orphan genre_id in bridge' AS check_name,
    b.genre_id
FROM bridge_title_genre b
LEFT JOIN dim_genre g ON b.genre_id = g.genre_id
WHERE g.genre_id IS NULL;

-- ----------------------------------------------------------------------------
-- CHECK 4: Referential Integrity - Foreign keys in fact_titles
-- Expected result: 0 rows
-- ----------------------------------------------------------------------------
SELECT 
    'CHECK 4a: Orphan date_key in fact' AS check_name,
    f.date_key
FROM fact_titles f
LEFT JOIN dim_date d ON f.date_key = d.date_key
WHERE d.date_key IS NULL;

SELECT 
    'CHECK 4b: Orphan language_id in fact' AS check_name,
    f.primary_language_id
FROM fact_titles f
LEFT JOIN dim_language l ON f.primary_language_id = l.language_id
WHERE l.language_id IS NULL;

-- ----------------------------------------------------------------------------
-- CHECK 5: Total Row Count Parity
-- Expected result: 584 rows exactly
-- ----------------------------------------------------------------------------
SELECT 
    'CHECK 5: Row Count Validation' AS check_name,
    COUNT(*) AS total_fact_rows,
    CASE WHEN COUNT(*) = 584 THEN 'PASS (584 rows)' ELSE 'FAIL' END AS status
FROM fact_titles;

-- ----------------------------------------------------------------------------
-- CHECK 6: Domain Validity - IMDb Score bounds [0.0, 10.0]
-- Expected result: 0 invalid rows
-- ----------------------------------------------------------------------------
SELECT 
    'CHECK 6: Invalid IMDb Scores' AS check_name,
    title_id, 
    title, 
    imdb_score
FROM fact_titles
WHERE imdb_score < 0.0 OR imdb_score > 10.0;

-- ----------------------------------------------------------------------------
-- CHECK 7: Domain Validity - Runtime bounds (> 0)
-- Expected result: 0 invalid rows
-- ----------------------------------------------------------------------------
SELECT 
    'CHECK 7: Invalid Runtimes' AS check_name,
    title_id, 
    title, 
    runtime
FROM fact_titles
WHERE runtime <= 0;

-- ----------------------------------------------------------------------------
-- CHECK 8: Primary Genre Designation in Bridge Table
-- Expected result: Exactly 584 rows where is_primary = 1 (one primary per title)
-- ----------------------------------------------------------------------------
SELECT 
    'CHECK 8: Primary Genre Count in Bridge' AS check_name,
    COUNT(*) AS primary_genre_count,
    CASE WHEN COUNT(*) = 584 THEN 'PASS (584 primary genres)' ELSE 'FAIL' END AS status
FROM bridge_title_genre
WHERE is_primary = 1;
