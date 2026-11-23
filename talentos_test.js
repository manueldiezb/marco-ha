// node talentos_test.js — extrae talentosFrom() de dashboard.html y la prueba
const fs = require('fs');
const assert = require('assert');
const h = fs.readFileSync(__dirname + '/dashboard.html', 'utf8');
const i = h.indexOf('function talentosFrom');
if (i < 0) { console.error('✗ falta talentosFrom en dashboard.html'); process.exit(1); }
const talentosFrom = new Function(h.slice(i, h.indexOf('\n}\n', i) + 2) + 'return talentosFrom;')();
const s = (id, state, a) => ({ entity_id: id, state, attributes: a });
const all = [
  s('sensor.talentos_ana', '7', { name: 'Ana', avatar: '🦋', order: 2 }),
  s('sensor.talentos_leo', '-2', { name: 'Leo', avatar: '🦁', order: 0 }),
  s('sensor.talentos_sol', 'unavailable', { name: 'Sol', avatar: '🐣', order: 3 }),
  s('sensor.otra_cosa', '5', {}),
];
const k = talentosFrom(all);
assert(k.map(x => x.name).join() === 'Leo,Ana', 'orden de la app y fuera los no numéricos: ' + k.map(x => x.name));
assert(k[0].balance === -2 && k[0].avatar === '🦁', 'campos');
assert(talentosFrom([]).length === 0, 'sin sensores, nada');
console.log('talentos_test hecho');
