// node compra_test.js — extrae cmpMatch() de dashboard.html y prueba las sugerencias al escribir
const h = require('fs').readFileSync(__dirname + '/dashboard.html', 'utf8');
const line = n => { const i = h.indexOf('const ' + n + ' ='); return h.slice(i, h.indexOf('\n', i)); };
const fn = n => { const i = h.indexOf('function ' + n + '('); return h.slice(i, h.indexOf('\n}\n', i) + 2); };
const cmpMatch = new Function([line('norm'), line('CMP_STOP'), line('CMP_SYN'), fn('cmpMatch'), 'return cmpMatch;'].join('\n'))();
const assert = require('assert');
const it = (name, times, last = '2026-10-01') => ({ name, times, last });
const hab = [it('Leche semidesnatada Hacendado', 20), it('Leche entera Hacendado', 3), it('Lechuga iceberg', 5),
  it('Ensalada mezcla lavada', 4), it('Huevos grandes L', 12), it('Plátano de Canarias IGP', 9, '2026-10-20'), it('Banana', 9, '2026-10-25')];
const names = q => cmpMatch(q, hab).map(x => x.name);
assert.deepEqual(names('lec'), ['Leche semidesnatada Hacendado', 'Lechuga iceberg', 'Leche entera Hacendado'], 'prefijo y más comprado primero');
assert.deepEqual(names('leche semi'), ['Leche semidesnatada Hacendado'], 'todas las palabras');
assert.deepEqual(names('Léche  SEMI'), ['Leche semidesnatada Hacendado'], 'sin tildes ni mayúsculas');
assert.deepEqual(names('huevos'), ['Huevos grandes L'], 'plural');
assert.deepEqual(names('platanos de canarias'), ['Plátano de Canarias IGP'], 'plural, tilde y «de»');
assert.deepEqual(names('lechuga'), ['Lechuga iceberg', 'Ensalada mezcla lavada'], 'sinónimos de Mercadona');
assert.deepEqual(names('de'), [], 'solo palabras vacías: nada');
assert.deepEqual(cmpMatch('atun', [it('Atún claro', 2, '2026-01-01'), it('Atún en aceite', 2, '2026-09-01')]).map(x => x.name), ['Atún en aceite', 'Atún claro'], 'empate: lo último comprado');
console.log('compra_test hecho');
