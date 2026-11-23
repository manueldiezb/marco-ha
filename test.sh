#!/bin/sh
# Todas las pruebas del Marco. Sale con error si falla alguna.
cd "$(dirname "$0")" || exit 1
f=0
node -e "const s=require('fs').readFileSync('dashboard.html','utf8');for(const m of s.matchAll(/<script>([\\s\\S]*?)<\\/script>/g))new Function(m[1])" || { echo "FALLA sintaxis de dashboard.html"; f=1; }
for t in *_test.js; do node "$t" >/dev/null || { echo "FALLA $t"; f=1; }; done
for t in test_aviones.py test_persianas.py; do python3 "$t" >/dev/null || { echo "FALLA $t"; f=1; }; done   # necesita jinja2
python3 fr24_matricula.py --test >/dev/null || { echo "FALLA fr24_matricula.py"; f=1; }
python3 liturgia.py --test >/dev/null || { echo "FALLA liturgia.py"; f=1; }
[ $f = 0 ] && echo "todo ok"; exit $f
