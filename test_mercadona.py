# Comprobación sin red de mercadona.py: python3 -I test_mercadona.py
import importlib.util, os
spec = importlib.util.spec_from_file_location('mercadona', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mercadona.py'))
mc = importlib.util.module_from_spec(spec); spec.loader.exec_module(mc)

leche = {'id': '10', 'display_name': 'Leche', 'thumbnail': 'https://x/l.jpg?fit=1', 'price_instructions': {'unit_price': '0.95'}}
platano = {'id': '20', 'display_name': 'Plátano', 'price_instructions': {'unit_price': '0.40', 'selling_method': 2,
           'increment_bunch_amount': '0.2', 'min_bunch_amount': '0.4', 'reference_price': '2.00', 'reference_format': 'kg'}}
cart = {'id': 'c', 'version': 3, 'lines': [{'product': leche, 'quantity': 2, 'sources': ['x']}, {'product': platano, 'quantity': 0.6}]}

# sumar, añadir nuevo, bajar de 1 a 0 y a peso por debajo del mínimo
lines, after = mc.apply_delta(cart, '10', 1)
assert after == 3 and lines[0] == {'product_id': '10', 'quantity': 3, 'sources': ['x']}
lines, after = mc.apply_delta(cart, '99', 1)
assert after == 1 and lines[-1]['product_id'] == '99' and len(lines) == 3
lines, after = mc.apply_delta({'lines': [{'product': leche, 'quantity': 1}]}, '10', -1)
assert after == 0 and lines == []
lines, after = mc.apply_delta(cart, '20', -0.2, 0.4)
assert after == 0.4 and len(lines) == 2
lines, after = mc.apply_delta(cart, '20', -0.4, 0.4)
assert after == 0 and [l['product_id'] for l in lines] == ['10']
lines, after = mc.apply_delta(cart, '30', -1)            # quitar lo que no está: no inventa líneas
assert after == 0 and len(lines) == 2

# vista: paso y mínimo a peso, foto sin la query original, total sin summary
v = mc.cart_view(cart)
p = v['items'][1]
assert (p['sm'], p['step'], p['min'], p['ref']) == (2, 0.2, 0.4, '2.00 €/kg'), p
assert v['items'][0]['img'] == 'https://x/l.jpg?fit=crop&w=200&h=200' and v['items'][0]['step'] == 1
assert v['total'] == round(0.95 * 2 + 2.0 * 0.6, 2) and v['count'] == 2
assert mc.cart_view({'lines': [], 'summary': {'total': '12.5'}})['total'] == 12.5
print('ok')
assert mc.fmt({}, {'is_pack': True, 'pack_size': 1.0, 'unit_name': 'briks', 'total_units': 6, 'size_format': 'l'}) == '6 briks × 1 L'
assert mc.fmt({'packaging': 'Pieza'}, {'unit_size': 0.25, 'size_format': 'kg', 'approx_size': True}) == 'Pieza 0,25 kg aprox.'
assert mc.fmt({}, {}) is None
print('ok fmt')
assert mc.fmt({}, {'is_pack': True, 'size_format': 'ud'}) is None; print('ok ud')

# ticket de tienda: PDF mínimo con el mismo formato (texto por coordenadas, comprimido)
import zlib
def tj(x, y, t): return f'BT /F2 20.4 Tf 1 0 0 1 {x} {y} Tm ({t})Tj ET\n'
body = (tj(156.9, 2302.8, '04/12/2024 19:34 ') + tj(81.83, 2166, 'Descripción') + tj(401, 2166, 'P. Unit') +
        tj(61.43, 2140, '1') + tj(81.83, 2140, 'CACAHUETE FRITO MIEL') + tj(534, 2140, '1,65') +
        tj(61.43, 2110, '2') + tj(81.83, 2110, '12 HUEVOS SUPER GRAN') + tj(423, 2110, '3,32') + tj(534, 2110, '6,64') +
        tj(61.43, 2080, '1') + tj(81.83, 2080, 'AGUACATE') +
        tj(122.6, 2057, '0,610 kg') + tj(381, 2057, '5,50 \x80/kg') + tj(534, 2057, '3,36') +
        tj(372, 2020, 'TOTAL \\(\x80\\)') + tj(513, 2020, '11,65') + tj(262, 2000, 'TARJETA BANCARIA') + tj(513, 2000, '11,65'))
pdf = b'%PDF-1.3\nstream\n' + zlib.compress(body.encode('latin-1')) + b'endstream\n'
t = mc.ticket(pdf)
assert t['date'] == '2024-12-04' and t['total'] == 11.65, t
assert [(l['name'], l['qty'], l['price'], l['kg']) for l in t['lines']] == [
    ('CACAHUETE FRITO MIEL', 1, 1.65, None), ('12 HUEVOS SUPER GRAN', 2, 3.32, None), ('AGUACATE', 1, 5.5, 0.61)], t['lines']
print('ok ticket')

# formato 2025 (openhtmltopdf): glifos de 2 bytes + tabla ToUnicode, cabecera «Cnt. Descripción», pescadería sin cantidad
def g(t): return '<' + ''.join(f'{ord(ch) - 29:04X}' for ch in t) + '>'
cmap = b'beginbfrange\n<0003> <00FF> <0020>\nendbfrange\n'
def tj2(x, y, t): return f'BT /F2 20.4 Tf 1 0 0 1 {x} {y} Tm {g(t)} Tj ET\n'
body = (tj2(156, 1617, '30/10/2026 11:37') + tj2(37.5, 1485, 'Cnt.') + tj2(82.6, 1485, 'Descripción') +
        tj2(62, 1459, '3') + tj2(82.6, 1459, 'MAC-CHEESE') + tj2(425, 1459, '1,30') + tj2(538, 1459, '3,90') +
        tj2(82.6, 766, 'PESCADO') + tj2(103, 740, 'SALMON ENTERO') + tj2(123, 718, '2,400 kg') + tj2(384, 718, '8,95 E/kg') + tj2(528, 718, '21,48') +
        tj2(391, 536, 'TOTAL') + tj2(528, 536, '25,38'))
pdf = b'%PDF-1.4\nstream\n' + zlib.compress(cmap) + b'endstream\nstream\n' + zlib.compress(body.encode()) + b'endstream\n'
t = mc.ticket(pdf)
assert t['date'] == '2026-10-30' and t['total'] == 25.38, t
assert [(l['name'], l['qty'], l['price'], l['kg']) for l in t['lines']] == [('MAC-CHEESE', 3, 1.3, None), ('SALMON ENTERO', 1, 8.95, 2.4)], t['lines']
print('ok ticket 2025')

# habituales: todo el histórico pesando lo reciente (20 compras de hace 2 años < 4 de este mes)
import tempfile, time
tmp = tempfile.mkdtemp(); mc.TICKETS, mc.CACHE, mc.GMAIL = f'{tmp}/t.json', f'{tmp}/c.json', f'{tmp}/nada'
P = lambda i, n: mc.item({'id': i, 'display_name': n, 'price_instructions': {'unit_price': '1'}})
ago = lambda days: time.strftime('%Y-%m-%d', time.localtime(time.time() - days * 86400))
mc.save(mc.TICKETS, {'uid': 1, 'pending': {}, 'map': {'PANAL': P('1', 'Pañal'), 'BRAG': P('2', 'Braguitas'), 'BOLSA': None},
        'tickets': [{'date': ago(700 + i * 10), 'lines': [['PANAL', 1]]} for i in range(20)] +
                   [{'date': ago(i * 7), 'lines': [['BRAG', 1], ['BRAG', 1], ['BOLSA', 1]]} for i in range(4)]})
class FakeM:
    def api(self, method, path): return {'results': []}
r = mc.habituales(FakeM())
assert [i['name'] for i in r['items']] == ['Braguitas', 'Pañal'] and r['items'][0]['usual'] == 2, r['items']
print('ok habituales')
mc.OCULTOS = f'{tmp}/o.json'
mc.ocultar('1'); assert [i['name'] for i in mc.sin_ocultos(r)['items']] == ['Braguitas']
mc.ocultar('1', volver=True); assert len(mc.sin_ocultos(r)['items']) == 2
print('ok ocultar')
