-- ============================================================================
-- sql/analysis.sql
-- 12 Analytical Business Queries for Netflix Originals Content Strategy
-- Target Engine: SQLite (netflix.db)
-- Author: Data Strategy & Analytics
-- ============================================================================

-- ============================================================================
-- QUERY 1: Executive Portfolio KPI Summary
-- Business Question: What are the foundational volume, quality, and runtime 
-- benchmarks of the Netflix Originals catalog?
-- Features: Aggregation, CASE statements, Subquery CTE, Conditional Shares.
-- ============================================================================
WITH portfolio_summary AS (
    SELECT 
        COUNT(*) AS total_titles,
        COUNT(DISTINCT f.title_id) AS distinct_titles,
        SUM(CASE WHEN d.is_full_year = 1 THEN 1 ELSE 0 END) AS mature_period_titles,
        ROUND(AVG(f.imdb_score), 2) AS avg_imdb_score,
        ROUND(AVG(f.runtime), 1) AS avg_runtime_minutes,
        SUM(CASE WHEN f.is_multilingual = 1 THEN 1 ELSE 0 END) AS multilingual_titles,
        SUM(CASE WHEN f.imdb_score >= 7.0 THEN 1 ELSE 0 END) AS high_rated_titles
    FROM fact_titles f
    JOIN dim_date d ON f.date_key = d.date_key
)
SELECT 
    total_titles,
    mature_period_titles,
    ROUND(100.0 * mature_period_titles / total_titles, 1) AS mature_period_share_pct,
    avg_imdb_score,
    avg_runtime_minutes,
    multilingual_titles,
    ROUND(100.0 * multilingual_titles / total_titles, 1) AS multilingual_share_pct,
    high_rated_titles,
    ROUND(100.0 * high_rated_titles / total_titles, 1) AS high_rated_share_pct
FROM portfolio_summary;

-- Interpretation:
-- The catalog spans 584 unique titles, with 86.1% (503 titles) concentrated in the 
-- mature full-year window (2016-2020). Overall mean perceived quality is 6.27 / 10 
-- with 24.3% achieving high ratings (>= 7.0), and 3.9% featuring multilingual production.


-- ============================================================================
-- QUERY 2: Portfolio Concentration (Top 3 Genres and Top 3 Languages Share)
-- Business Question: How concentrated is Netflix's content pipeline in its top 
-- 3 genre groups and top 3 primary languages?
-- Features: Multi-step CTE, SUM() OVER(), concentration ratio calculation.
-- ============================================================================
WITH genre_shares AS (
    SELECT 
        genre_group,
        COUNT(*) AS titles,
        ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_titles), 2) AS share_pct,
        ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) AS rank_order
    FROM fact_titles
    GROUP BY genre_group
),
lang_shares AS (
    SELECT 
        primary_language,
        COUNT(*) AS titles,
        ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_titles), 2) AS share_pct,
        ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) AS rank_order
    FROM fact_titles
    GROUP BY primary_language
)
SELECT 
    'Top 3 Genre Groups' AS concentration_dimension,
    GROUP_CONCAT(genre_group || ' (' || share_pct || '%)', ', ') AS top_components,
    ROUND(SUM(share_pct), 2) AS combined_share_pct
FROM genre_shares
WHERE rank_order <= 3
UNION ALL
SELECT 
    'Top 3 Primary Languages' AS concentration_dimension,
    GROUP_CONCAT(primary_language || ' (' || share_pct || '%)', ', ') AS top_components,
    ROUND(SUM(share_pct), 2) AS combined_share_pct
FROM lang_shares
WHERE rank_order <= 3;

-- Interpretation:
-- The portfolio demonstrates high concentration: the top 3 genre groups (Documentary, 
-- Drama, Comedy) capture 58.9% of all titles, while the top 3 languages (English, 
-- Hindi, Spanish) control 79.6% of the catalog, showing heavy English-market dependence.


-- ============================================================================
-- QUERY 3: Year-over-Year Growth (Full Mature Years Only: 2016-2020)
-- Business Question: How rapidly did annual release volume scale across full 
-- reporting years, and what were the YoY growth rates?
-- Features: Window function LAG(), WHERE filter on is_full_year = 1, percentage delta.
-- ============================================================================
WITH annual_releases AS (
    SELECT 
        d.year,
        COUNT(f.title_id) AS titles_released
    FROM fact_titles f
    JOIN dim_date d ON f.date_key = d.date_key
    WHERE d.is_full_year = 1
    GROUP BY d.year
)
SELECT 
    year,
    titles_released,
    LAG(titles_released) OVER (ORDER BY year) AS prev_year_titles,
    titles_released - LAG(titles_released) OVER (ORDER BY year) AS net_titles_added,
    ROUND(100.0 * (titles_released - LAG(titles_released) OVER (ORDER BY year)) / 
          LAG(titles_released) OVER (ORDER BY year), 1) AS yoy_growth_pct
FROM annual_releases
ORDER BY year;

-- Interpretation:
-- Annual releases expanded more than 6-fold from 30 titles in 2016 to 183 in 2020. 
-- Growth peaked at +120.0% in 2017 (+36 titles) before stabilizing at a strong 
-- +46.4% expansion (+58 titles) during the 2020 global pandemic lockdown year.


-- ============================================================================
-- QUERY 4: Cumulative Title Trajectory Over Time
-- Business Question: What is the cumulative release trajectory of Netflix Originals 
-- across all active calendar years?
-- Features: Cumulative running sum window function: SUM() OVER (ORDER BY ...).
-- ============================================================================
WITH yearly_cadence AS (
    SELECT 
        d.year,
        d.is_full_year,
        COUNT(f.title_id) AS annual_titles
    FROM fact_titles f
    JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY d.year, d.is_full_year
)
SELECT 
    year,
    CASE WHEN is_full_year = 1 THEN 'Full Mature Year' ELSE 'Sparse / Partial' END AS year_status,
    annual_titles,
    SUM(annual_titles) OVER (ORDER BY year ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_titles,
    ROUND(100.0 * SUM(annual_titles) OVER (ORDER BY year ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) / 
          (SELECT COUNT(*) FROM fact_titles), 1) AS cumulative_catalog_pct
FROM yearly_cadence
ORDER BY year;

-- Interpretation:
-- Netflix's original production ramped up exponentially: after releasing only 10 titles 
-- combined in 2014-2015 (1.7%), the platform crossed 50% cumulative catalog volume in 
-- 2019 (329 titles) and closed May 2021 at 584 total titles.


-- ============================================================================
-- QUERY 5: Release Timing Patterns (Day of Week and Seasonality)
-- Business Question: What scheduling patterns exist in Netflix releases by weekday 
-- and month, and is there evidence of weekend binge-drop strategy?
-- Features: GROUP BY with multi-level grouping, share calculation.
-- ============================================================================
SELECT 
    d.weekday_name,
    COUNT(f.title_id) AS titles_released,
    ROUND(100.0 * COUNT(f.title_id) / (SELECT COUNT(*) FROM fact_titles), 1) AS share_of_total_pct,
    ROUND(AVG(f.imdb_score), 2) AS avg_imdb_score
FROM fact_titles f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.day_of_week, d.weekday_name
ORDER BY titles_released DESC;

-- Interpretation:
-- 65.6% of all Netflix Originals (383 of 584) premiere on a Friday, confirming an 
-- intentional operational cadence designed to capture weekend streaming traffic, 
-- followed by Wednesday (14.0%). Weekend releases (Sat/Sun) account for only 2.4%.


-- ============================================================================
-- QUERY 6: Perceived Quality Benchmarks by Genre Group (Minimum Sample Filter)
-- Business Question: Which genre groups score highest and lowest on IMDb, 
-- filtering strictly for robust sample sizes (n >= 10)?
-- Features: GROUP BY, HAVING COUNT(*) >= 10, AVG, MIN, MAX, score range.
-- ============================================================================
SELECT 
    f.genre_group,
    COUNT(f.title_id) AS total_titles,
    ROUND(AVG(f.runtime), 1) AS avg_runtime_min,
    ROUND(AVG(f.imdb_score), 2) AS avg_imdb_score,
    MIN(f.imdb_score) AS min_imdb_score,
    MAX(f.imdb_score) AS max_imdb_score,
    ROUND(MAX(f.imdb_score) - MIN(f.imdb_score), 2) AS score_spread
FROM fact_titles f
GROUP BY f.genre_group
HAVING COUNT(f.title_id) >= 10
ORDER BY avg_imdb_score DESC;

-- Interpretation:
-- Documentaries dominate perceived quality with a platform-leading 6.93 average score 
-- across 163 titles, followed by Music/Concert/Specials (6.68). In contrast, 
-- Comedies (5.74) and Thriller/Crime/Horror (5.75) represent the lowest-scoring genres.


-- ============================================================================
-- QUERY 7: Quality Segmentation (Share of High-Rated Titles by Genre Group)
-- Business Question: What percentage of titles in each genre group achieve high 
-- perceived quality (IMDb >= 7.0) versus mediocre or low quality?
-- Features: CASE WHEN conditional counts, percentage proportions, sample enforcement.
-- ============================================================================
SELECT 
    f.genre_group,
    COUNT(f.title_id) AS total_titles,
    SUM(CASE WHEN f.imdb_score >= 7.0 THEN 1 ELSE 0 END) AS high_rated_titles,
    SUM(CASE WHEN f.imdb_score BETWEEN 5.5 AND 6.99 THEN 1 ELSE 0 END) AS mid_rated_titles,
    SUM(CASE WHEN f.imdb_score < 5.5 THEN 1 ELSE 0 END) AS low_rated_titles,
    ROUND(100.0 * SUM(CASE WHEN f.imdb_score >= 7.0 THEN 1 ELSE 0 END) / COUNT(f.title_id), 1) AS pct_high_rated,
    ROUND(100.0 * SUM(CASE WHEN f.imdb_score < 5.5 THEN 1 ELSE 0 END) / COUNT(f.title_id), 1) AS pct_low_rated
FROM fact_titles f
GROUP BY f.genre_group
HAVING COUNT(f.title_id) >= 10
ORDER BY pct_high_rated DESC;

-- Interpretation:
-- 55.8% of Documentaries achieve an IMDb score >= 7.0 (91 of 163 titles), whereas 
-- only 7.0% of Comedies and 3.5% of Romances clear the 7.0 threshold, indicating 
-- an acute quality deficit in scripted light entertainment.


-- ============================================================================
-- QUERY 8: Primary Language Performance Benchmarks & Sample Size Audit
-- Business Question: How do primary languages compare in perceived quality, 
-- and which languages must be flagged as low-sample (n < 10)?
-- Features: LEFT JOIN, CASE WHEN for low-sample flagging, conditional aggregation.
-- ============================================================================
SELECT 
    l.language_name,
    COUNT(f.title_id) AS total_titles,
    ROUND(AVG(f.imdb_score), 2) AS avg_imdb_score,
    ROUND(AVG(f.runtime), 1) AS avg_runtime_min,
    CASE 
        WHEN COUNT(f.title_id) < 10 THEN 'LOW-SAMPLE (<10 titles) - Flagged' 
        ELSE 'Robust Sample (>=10)' 
    END AS sample_reliability_status,
    SUM(CASE WHEN f.imdb_score >= 7.0 THEN 1 ELSE 0 END) AS high_rated_count
FROM dim_language l
LEFT JOIN fact_titles f ON l.language_id = f.primary_language_id
GROUP BY l.language_id, l.language_name
ORDER BY total_titles DESC, avg_imdb_score DESC;

-- Interpretation:
-- Among reliable languages (n >= 10), English (6.39 avg across 419 titles) and 
-- Spanish (6.31 avg across 34 titles) outperform French (5.77 across 20 titles, 
-- where 0% reached 7.0) and Italian (5.54). 26 languages are flagged as low-sample.


-- ============================================================================
-- QUERY 9: Top Marquee Title per Genre Group
-- Business Question: What is the highest-rated individual title in each genre 
-- group, and what were its runtime and release year?
-- Features: Window function ROW_NUMBER() with PARTITION BY genre_group.
-- ============================================================================
WITH ranked_titles AS (
    SELECT 
        f.genre_group,
        f.title,
        d.year,
        f.primary_language,
        f.runtime,
        f.imdb_score,
        ROW_NUMBER() OVER (PARTITION BY f.genre_group ORDER BY f.imdb_score DESC, f.runtime DESC) AS rank_in_genre
    FROM fact_titles f
    JOIN dim_date d ON f.date_key = d.date_key
)
SELECT 
    genre_group,
    title AS highest_rated_title,
    year AS release_year,
    primary_language,
    runtime AS runtime_minutes,
    imdb_score
FROM ranked_titles
WHERE rank_in_genre = 1
ORDER BY imdb_score DESC;

-- Interpretation:
-- David Attenborough: A Life on Our Planet leads all titles with a 9.0 rating in 
-- Documentary, followed by Springsteen on Broadway (8.5, Music/Concert/Special) 
-- and The Trial of the Chicago 7 (7.8, Drama).


-- ============================================================================
-- QUERY 10: Quality Quartile Segmentation (NTILE)
-- Business Question: When the catalog is divided into 4 equal quality tiers 
-- (quartiles), how do average runtime and genre group compositions vary?
-- Features: NTILE(4) window function, subquery aggregation.
-- ============================================================================
WITH score_quartiles AS (
    SELECT 
        title_id,
        title,
        genre_group,
        runtime,
        imdb_score,
        NTILE(4) OVER (ORDER BY imdb_score) AS quality_quartile
    FROM fact_titles
)
SELECT 
    quality_quartile,
    CASE 
        WHEN quality_quartile = 1 THEN 'Q1: Bottom 25% (Scores <= 5.7)'
        WHEN quality_quartile = 2 THEN 'Q2: Lower-Mid 25% (Scores 5.8 - 6.3)'
        WHEN quality_quartile = 3 THEN 'Q3: Upper-Mid 25% (Scores 6.4 - 6.9)'
        WHEN quality_quartile = 4 THEN 'Q4: Top 25% (Scores >= 7.0)'
    END AS quartile_label,
    COUNT(*) AS title_count,
    ROUND(MIN(imdb_score), 1) AS min_score,
    ROUND(MAX(imdb_score), 1) AS max_score,
    ROUND(AVG(imdb_score), 2) AS mean_score,
    ROUND(AVG(runtime), 1) AS mean_runtime_min
FROM score_quartiles
GROUP BY quality_quartile
ORDER BY quality_quartile;

-- Interpretation:
-- Mean runtime across all four quartiles remains virtually identical (92.5 min in Q1, 
-- 94.6 min in Q2, 94.9 min in Q3, 91.8 min in Q4), providing immediate SQL proof 
-- that length does not dictate audience or critic reception.


-- ============================================================================
-- QUERY 11: Multi-Genre Bridge Table Analysis with Distinct Counting
-- Business Question: What is the true distribution of all genre tags across the 
-- catalog, accounting for multi-genre titles without duplicating metrics?
-- Features: INNER JOIN bridge_title_genre, COUNT(DISTINCT title_id) demonstration.
-- ----------------------------------------------------------------------------
-- CRITICAL SQL NOTE:
-- A title with 3 genre associations produces 3 rows in a standard join with the 
-- bridge table. Using COUNT(*) would double-count titles and artificially inflate 
-- total catalog volume to 643 instead of 584. COUNT(DISTINCT f.title_id) is 
-- mandatory to maintain statistical integrity.
-- ============================================================================
SELECT 
    g.genre_name,
    COUNT(b.title_id) AS total_tag_occurrences,
    COUNT(DISTINCT b.title_id) AS distinct_titles,
    SUM(b.is_primary) AS primary_genre_titles,
    ROUND(AVG(f.imdb_score), 2) AS avg_imdb_score
FROM dim_genre g
JOIN bridge_title_genre b ON g.genre_id = b.genre_id
JOIN fact_titles f ON b.title_id = f.title_id
GROUP BY g.genre_id, g.genre_name
HAVING COUNT(DISTINCT b.title_id) >= 10
ORDER BY distinct_titles DESC;

-- Interpretation:
-- Atomic genre tags expand secondary classifications: Drama expands from 77 primary 
-- titles to 82 total associations (+5 secondary tags), and Comedy expands from 49 to 
-- 60 (+11 secondary tags), while Documentary remains 100% pure (159 primary, 0 secondary).


-- ============================================================================
-- QUERY 12: Content Strategy Opportunity Matrix (Genre Group x Primary Language)
-- Business Question: Which genre-language intersections represent high-performing 
-- strongholds versus strategic underrepresented opportunities?
-- Features: Multi-column GROUP BY, conditional aggregation, strategic categorization.
-- ============================================================================
SELECT 
    f.genre_group,
    f.primary_language,
    COUNT(f.title_id) AS title_count,
    ROUND(AVG(f.imdb_score), 2) AS avg_imdb_score,
    ROUND(AVG(f.runtime), 1) AS avg_runtime_min,
    CASE 
        WHEN COUNT(f.title_id) >= 15 AND AVG(f.imdb_score) >= 6.5 THEN 'Established Core (High Vol / High Score)'
        WHEN COUNT(f.title_id) >= 15 AND AVG(f.imdb_score) < 6.0 THEN 'Quality Vulnerability (High Vol / Low Score)'
        WHEN COUNT(f.title_id) BETWEEN 3 AND 14 AND AVG(f.imdb_score) >= 6.8 THEN 'High-Potential Opportunity (Low Vol / High Score)'
        WHEN COUNT(f.title_id) < 5 THEN 'Niche / Exploratory'
        ELSE 'Moderate Core'
    END AS strategic_opportunity_segment
FROM fact_titles f
GROUP BY f.genre_group, f.primary_language
HAVING COUNT(f.title_id) >= 3
ORDER BY title_count DESC, avg_imdb_score DESC;

-- Interpretation:
-- English Documentary (141 titles, 6.96 avg) and English Drama (58 titles, 6.47 avg) 
-- form Netflix's established core. Major strategic vulnerabilities appear in English 
-- Comedy (65 titles, 5.75 avg) and English Thriller/Horror (67 titles, 5.76 avg), 
-- indicating that scaled comedy and horror productions routinely underperform in quality.
