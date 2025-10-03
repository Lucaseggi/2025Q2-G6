-- Distribution of norms grouped by titulo_sumario
-- Shows count and percentage for each titulo_sumario

SELECT
    COALESCE(titulo_sumario, 'NULL') AS titulo_sumario,
    COUNT(*) AS norm_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM normas
GROUP BY titulo_sumario
ORDER BY norm_count DESC;
