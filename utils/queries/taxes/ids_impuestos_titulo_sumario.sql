-- IDs for all norms with titulo_sumario = 'IMPUESTOS'

SELECT infoleg_id, titulo_sumario
FROM normas
WHERE titulo_sumario = 'IMPUESTOS'
ORDER BY infoleg_id;
