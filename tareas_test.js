// node tareas_test.js — extrae tarDue() y tarOrden() de dashboard.html: fechas de los recordatorios y su orden
const h = require('fs').readFileSync(__dirname + '/dashboard.html', 'utf8');
const fn = n => { const i = h.indexOf('function ' + n + '('); return h.slice(i, h.indexOf('\n}\n', i) + 2); };
const line = n => { const i = h.indexOf('const ' + n + ' ='); return h.slice(i, h.indexOf(';\n', i) + 1); };
const { tarDue, tarOrden, tarGrupo, tarSplit } = new Function([line('TAR_HECHAS'), fn('tarSplit'), fn('tarDue'), line('tarOrden'), fn('tarGrupo'), 'return { tarDue, tarOrden, tarGrupo, tarSplit };'].join('\n'))();
const assert = require('assert');
const now = new Date('2026-11-16T13:00');
assert.deepEqual(tarDue('2026-11-16', now), { txt: 'Hoy', late: false }, 'hoy sin hora no está vencida');
assert.deepEqual(tarDue('2026-11-17', now), { txt: 'Mañana', late: false });
assert.deepEqual(tarDue('2026-11-15', now), { txt: 'Ayer', late: true });
assert.deepEqual(tarDue('2026-11-16T10:00:00+01:00', now), { txt: 'Hoy 10:00', late: true }, 'con hora: vencida si ya pasó');
assert.equal(tarDue('2026-11-25', now).txt, '25 nov');
const ids = tarOrden([{ uid: 'a' }, { uid: 'b', due: '2026-11-20' }, { uid: 'c' }, { uid: 'd', due: '2026-11-16T09:00:00+01:00' }]).map(x => x.uid);
assert.deepEqual(ids, ['d', 'b', 'a', 'c'], 'con fecha primero, el resto en su orden');
const g = d => tarGrupo({ due: d }, now);
assert.deepEqual(['2026-11-10', '2026-11-16', '2026-11-16T22:00:00+01:00', '2026-11-17', '2026-11-17T08:00:00+01:00', '2026-11-18'].map(g),
  ['hoy', 'hoy', 'hoy', 'manana', 'manana', 'resto'], 'vencidas y de hoy en Hoy; mañana; el resto');
assert.equal(tarGrupo({}, now), 'resto', 'sin fecha: más adelante');
// Hechas: la última tachada arriba; lo tocado aquí manda hasta que HA lo confirme o pasen 2 min
const all = [{ uid: 'p', status: 'needs_action' }, { uid: 'v', status: 'completed', completed: '2026-11-10T09:00:00+01:00' },
  { uid: 'n', status: 'completed', completed: '2026-11-18T20:00:00+01:00' }, { uid: 'x', status: 'needs_action' }];
const fuera = new Map([['x', { status: 'completed', t: Date.parse('2026-11-19T10:00') }], ['n', { status: 'completed', t: 0 }]]);
let r = tarSplit(all, fuera, Date.parse('2026-11-19T10:01'));
assert.deepEqual(r.items.map(i => i.uid), ['p'], 'x tachada aquí no vuelve aunque HA aún la dé pendiente');
assert.deepEqual(r.hechas.map(i => i.uid), ['x', 'n', 'v'], 'hechas: la más reciente arriba');
assert.ok(!fuera.has('n'), 'HA ya coincide: se olvida');
r = tarSplit(all, fuera, Date.parse('2026-11-19T10:03'));
assert.deepEqual(r.items.map(i => i.uid), ['p', 'x'], 'a los 2 min manda HA');
assert.equal(tarSplit(Array.from({ length: 30 }, (_, i) => ({ uid: 'h' + i, status: 'completed' })), new Map()).hechas.length, 15, 'solo las últimas');
console.log('tareas_test hecho');
