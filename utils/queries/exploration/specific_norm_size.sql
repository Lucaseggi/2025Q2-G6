-- Calculate the text size for reference norm with infoleg_id 180781
-- This query shows the character count of the main text field

SELECT
    infoleg_id,
    CASE
        WHEN texto_norma_actualizado IS NOT NULL THEN LENGTH(texto_norma_actualizado)
        WHEN texto_norma IS NOT NULL THEN LENGTH(texto_norma)
        ELSE 0
    END AS character_count,
    CASE
        WHEN texto_norma_actualizado IS NOT NULL THEN 'texto_norma_actualizado'
        WHEN texto_norma IS NOT NULL THEN 'texto_norma'
        ELSE 'no_text'
    END AS text_source
FROM normas
WHERE infoleg_id = 183207;
