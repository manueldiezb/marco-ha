// node countdown_test.js — la línea «Cuenta atrás» de la descripción: color, efectos y enlace a la foto
const h = require('fs').readFileSync(__dirname + '/dashboard.html', 'utf8');
const pick = n => { const i = h.indexOf('const ' + n + ' ='); return h.slice(i, h.indexOf('\n', i)); };
const block = h.slice(h.indexOf('/* cd:start'), h.indexOf('/* cd:end */'));
const { cdParse } = new Function(pick('norm') + block + 'return { cdParse };')();
const assert = require('assert');
assert.equal(cdParse('Entradas en el bolso'), null);
assert.deepEqual(cdParse('Cuenta atrás'), { color: null, fx: [], url: '' });
assert.deepEqual(cdParse('cuenta atras · Rojo · nieve luces confeti'), { color: '#D9483B', fx: ['nieve', 'luces'], url: '' });
assert.deepEqual(cdParse('Hotel reservado\nCuenta atrás #12AB9F circo'), { color: '#12AB9F', fx: ['circo'], url: '' });
assert.deepEqual(cdParse('Cuenta atrás<br>Foto: <a href="https://x.com/a.jpg?w=1&amp;h=2">https://x.com/a.jpg?w=1&amp;h=2</a>'),
  { color: null, fx: [], url: 'https://x.com/a.jpg?w=1&h=2' });
assert.deepEqual(cdParse('Cuenta atrás · marrón · hojas'), { color: '#8B5A2B', fx: ['hojas'], url: '' });
console.log('ok');
