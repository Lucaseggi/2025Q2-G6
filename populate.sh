#!/bin/bash

# Array of norm IDs and types
norms=(
"66648,Acordada"
"96480,Acta"
"136102,Actuacion"
"139014,Acuerdo"
"182238,Circular"
"31904,Comunicación"
"144986,Convenio"
"119353,Decisión"
"33335,Decisión Administrativa"
"144306,Decreto"
"184331,Decreto"
"293573,Decreto/Ley"
"100919,Directiva"
"189151,Disposición"
"92978,Instrucción"
"103468,Interpretación"
"113553,Laudo"
"109257,Nota"
"141325,Nota Externa"
"335800,Protocolo"
"164570,Providencia"
"120563,Recomendación"
"194674,Resolución"
"194675,Resolución"
"309636,Resolución"
"402994,Resolución"
"402995,Resolución"
)

echo "================================================================================"
echo "Testing Process Endpoint - Norms by Type"
echo "================================================================================"
echo "Total norms to test: ${#norms[@]}"
echo ""

count=0
success=0
failed=0

for norm in "${norms[@]}"; do
    IFS=',' read -r id tipo <<< "$norm"
    count=$((count + 1))

    echo -n "[$count/${#norms[@]}] Processing norm $id ($tipo)... "

    response=$(curl -s -w "\n%{http_code}" --location 'http://localhost:8003/process' \
        --header 'Content-Type: application/json' \
        --data "{\"infoleg_id\": $id, \"force\": false}" 2>/dev/null)

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        echo "✓ SUCCESS"
        success=$((success + 1))
    else
        echo "✗ FAILED (HTTP $http_code)"
        failed=$((failed + 1))
    fi

    sleep 10
done

echo ""
echo "================================================================================"
echo "SUMMARY"
echo "================================================================================"
echo "Total:      $count"
echo "Success:    $success"
echo "Failed:     $failed"
echo "Success rate: $(awk "BEGIN {printf \"%.2f\", ($success/$count)*100}")%"
