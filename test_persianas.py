# Reproduce los casos de marco-ipad/blind_test.js con la macro de HA. Ejecutar: python3 test_persianas.py
import json, jinja2, datetime as dt
def flt(v, d=None):
    try: return float(v)
    except (TypeError, ValueError): return d
def it(v, d=0):
    try: return int(float(v))
    except (TypeError, ValueError): return d
env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'), extensions=['jinja2.ext.loopcontrols'])
env.filters.update(float=flt, int=it, to_json=json.dumps)
mac = env.get_template('persianas.jinja').module.persiana
T = lambda hms, d=23: dt.datetime(2026, 10, d, *map(int, hms.split(':'))).timestamp()
def run(evs, travel, now, cae=False):
    s = {'pos': None, 'mov': 0, 't0': 0}
    for o, t in evs:
        s = json.loads(str(mac(s['pos'] if s['pos'] is not None else 'unknown', s['mov'], s['t0'], o, travel, t, cae)))
    # disparador «fin»: si sigue moviéndose y ya pasó el recorrido, se asienta
    if s['mov'] and now - s['t0'] >= travel:
        s = json.loads(str(mac(s['pos'] if s['pos'] is not None else 'unknown', s['mov'], s['t0'], '', travel, s['t0'] + travel)))
    return s
dorm = [('parar','23:40:36'),('bajar','23:49:09'),('subir','23:49:40'),('parar','23:49:59'),('bajar','23:54:28'),('parar','23:55:04')]
dorm = [(o, T(t, 22)) for o, t in dorm] + [(o, T(t)) for o, t in [('bajar','00:00:37'),('parar','00:01:14'),('bajar','00:01:46'),('parar','00:02:21')]]
now = T('00:10:00')
assert run(dorm, 35, now)['pos'] == 0, 'dormitorio bajada'
assert run([(o, T(t)) for o, t in [('subir','00:01:04'),('parar','00:01:06'),('bajar','00:01:46'),('parar','00:02:47')]], 60, now)['pos'] == 0, 'comedor'
assert run([('subir', T('00:09:50'))], 27, now)['mov'] == 1, 'subiendo'
m = run([(o, T(t)) for o, t in [('bajar','00:00:00'),('parar','00:00:40'),('subir','00:01:00'),('parar','00:01:30'),('bajar','00:05:00'),('parar','00:05:10')]], 35, now)
assert 3 < m['pos'] < 97, m
assert run([('parar', T('00:01:00'))], 35, now)['pos'] is None, 'sin datos'
assert run([('bajar', T('00:01:00'))], 35, now)['pos'] == 0, 'sin parar'
assert run([(o, T(t)) for o, t in [('bajar','00:00:00'),('parar','00:00:40'),('subir','00:01:00'),('parar','00:01:34')]], 35, now)['pos'] == 100, 'subida'
medio = [(o, T(t)) for o, t in [('bajar','00:00:00'),('parar','00:00:40'),('subir','00:01:00'),('parar','00:01:15')]]
assert run(medio, 35, now, cae=True)['pos'] is None, 'dormitorio parada a medias = desconocida'
assert run(dorm, 35, now, cae=True)['pos'] == 0, 'dormitorio bajada completa con cae'
print('ok')
