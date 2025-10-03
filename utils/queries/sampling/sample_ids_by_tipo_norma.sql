-- Sample IDs for each tipo_norma category
-- 5 Resoluciones, 2 Decretos, 1 of each other type

(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Resolución' LIMIT 5)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Decreto' LIMIT 2)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Disposición' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Decisión Administrativa' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Comunicación' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Decreto/Ley' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Nota Externa' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Decisión' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Directiva' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Instrucción' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Acordada' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Circular' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Nota' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Acta' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Recomendación' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Laudo' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Convenio' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Acuerdo' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Providencia' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Protocolo' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Actuacion' LIMIT 1)
UNION ALL
(SELECT infoleg_id, tipo_norma FROM normas WHERE tipo_norma = 'Interpretación' LIMIT 1)
ORDER BY tipo_norma, infoleg_id;
