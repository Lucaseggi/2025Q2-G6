-- Distribution of norms grouped by tipo_norma
-- Shows count and percentage for each norm type

SELECT
    COALESCE(tipo_norma, 'NULL') AS tipo_norma,
    COUNT(*) AS norm_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM normas
GROUP BY tipo_norma
ORDER BY norm_count DESC;
