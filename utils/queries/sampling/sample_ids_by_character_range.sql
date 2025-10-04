-- Sample IDs for each character range bracket
-- Distribution based on percentage: more samples for higher percentages

WITH text_lengths AS (
    SELECT
        infoleg_id,
        CASE
            WHEN texto_norma_actualizado IS NOT NULL THEN LENGTH(texto_norma_actualizado)
            WHEN texto_norma IS NOT NULL THEN LENGTH(texto_norma)
            ELSE NULL
        END AS character_count,
        CASE
            WHEN texto_norma_actualizado IS NOT NULL THEN 'texto_norma_actualizado'
            WHEN texto_norma IS NOT NULL THEN 'texto_norma'
            ELSE 'no_text'
        END AS text_source
    FROM normas
),
categorized AS (
    SELECT
        infoleg_id,
        CASE
            WHEN text_source = 'no_text' THEN 'No text'
            WHEN character_count = 0 THEN 'Empty (0 chars)'
            WHEN character_count < 500 THEN '1-499 chars'
            WHEN character_count < 1000 THEN '500-999 chars'
            WHEN character_count < 2000 THEN '1K-2K chars'
            WHEN character_count < 3000 THEN '2K-3K chars'
            WHEN character_count < 5000 THEN '3K-5K chars'
            WHEN character_count < 7500 THEN '5K-7.5K chars'
            WHEN character_count < 10000 THEN '7.5K-10K chars'
            WHEN character_count < 15000 THEN '10K-15K chars'
            WHEN character_count < 20000 THEN '15K-20K chars'
            WHEN character_count < 30000 THEN '20K-30K chars'
            WHEN character_count < 50000 THEN '30K-50K chars'
            WHEN character_count < 75000 THEN '50K-75K chars'
            WHEN character_count < 100000 THEN '75K-100K chars'
            WHEN character_count < 150000 THEN '100K-150K chars'
            WHEN character_count < 200000 THEN '150K-200K chars'
            ELSE '200K+ chars'
        END AS character_range,
        character_count,
        ROW_NUMBER() OVER (
            PARTITION BY CASE
                WHEN text_source = 'no_text' THEN 'No text'
                WHEN character_count = 0 THEN 'Empty (0 chars)'
                WHEN character_count < 500 THEN '1-499 chars'
                WHEN character_count < 1000 THEN '500-999 chars'
                WHEN character_count < 2000 THEN '1K-2K chars'
                WHEN character_count < 3000 THEN '2K-3K chars'
                WHEN character_count < 5000 THEN '3K-5K chars'
                WHEN character_count < 7500 THEN '5K-7.5K chars'
                WHEN character_count < 10000 THEN '7.5K-10K chars'
                WHEN character_count < 15000 THEN '10K-15K chars'
                WHEN character_count < 20000 THEN '15K-20K chars'
                WHEN character_count < 30000 THEN '20K-30K chars'
                WHEN character_count < 50000 THEN '30K-50K chars'
                WHEN character_count < 75000 THEN '50K-75K chars'
                WHEN character_count < 100000 THEN '75K-100K chars'
                WHEN character_count < 150000 THEN '100K-150K chars'
                WHEN character_count < 200000 THEN '150K-200K chars'
                ELSE '200K+ chars'
            END
            ORDER BY infoleg_id
        ) AS rn
    FROM text_lengths
)
SELECT infoleg_id, character_range, character_count
FROM categorized
WHERE
    (character_range = 'No text' AND rn <= 5)
    OR (character_range = 'Empty (0 chars)' AND rn <= 1)
    OR (character_range = '1-499 chars' AND rn <= 1)
    OR (character_range = '500-999 chars' AND rn <= 2)
    OR (character_range = '1K-2K chars' AND rn <= 2)
    OR (character_range = '2K-3K chars' AND rn <= 2)
    OR (character_range = '3K-5K chars' AND rn <= 5)
    OR (character_range = '5K-7.5K chars' AND rn <= 10)
    OR (character_range = '7.5K-10K chars' AND rn <= 5)
    OR (character_range = '10K-15K chars' AND rn <= 3)
    OR (character_range = '15K-20K chars' AND rn <= 2)
    OR (character_range = '20K-30K chars' AND rn <= 2)
    OR (character_range = '30K-50K chars' AND rn <= 1)
    OR (character_range = '50K-75K chars' AND rn <= 1)
    OR (character_range = '75K-100K chars' AND rn <= 1)
    OR (character_range = '100K-150K chars' AND rn <= 1)
    OR (character_range = '150K-200K chars' AND rn <= 1)
    OR (character_range = '200K+ chars' AND rn <= 1)
ORDER BY
    CASE character_range
        WHEN 'No text' THEN 1
        WHEN 'Empty (0 chars)' THEN 2
        WHEN '1-499 chars' THEN 3
        WHEN '500-999 chars' THEN 4
        WHEN '1K-2K chars' THEN 5
        WHEN '2K-3K chars' THEN 6
        WHEN '3K-5K chars' THEN 7
        WHEN '5K-7.5K chars' THEN 8
        WHEN '7.5K-10K chars' THEN 9
        WHEN '10K-15K chars' THEN 10
        WHEN '15K-20K chars' THEN 11
        WHEN '20K-30K chars' THEN 12
        WHEN '30K-50K chars' THEN 13
        WHEN '50K-75K chars' THEN 14
        WHEN '75K-100K chars' THEN 15
        WHEN '100K-150K chars' THEN 16
        WHEN '150K-200K chars' THEN 17
        WHEN '200K+ chars' THEN 18
    END,
    infoleg_id;
