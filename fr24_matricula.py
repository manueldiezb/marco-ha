# Lo que FR24 sabe de un vuelo programado, de las salidas y llegadas de su aeropuerto (la misma librería que la integración de HA).
# Uso (shell_command.fr24_matricula de packages/vuelos.yaml): python3 fr24_matricula.py MAD UX5053 1794766800 [EC-NUZ]
# Imprime {"fl": tramo, "cadena": [vuelo que trae el avión], "ctx": {origen, destino}} o {}. Los tramos con la forma de
# adb_tramo (aviones.jinja) para que la tarjeta los trate igual. ctx = retraso medio reciente (min) y METAR de las salidas del
# origen y las llegadas al destino, para la causa del retraso. El 4.º argumento es la matrícula conocida (manual o anterior)
# por si FR24 aún no la tiene en la salida.
# FR24 no sabe la ruta solo con el número (su lista de vuelos da 403): el aeropuerto y la hora los pone AeroDataBox una vez.
# ponytail: tope de 6 páginas de 100 por lista (Barajas: ~3 h por página); si FR24 bloquea (403/429) sale {} y manda AeroDataBox.
import json, re, sys

ESTADOS = {'canceled': 'Canceled', 'diverted': 'Diverted', 'landed': 'Arrived'}


def g(d, *ks):
    for k in ks:
        d = (d or {}).get(k) if isinstance(d, dict) else None
    return d


def modelo(texto, code):
    """«Boeing 737-8GP» → «Boeing 737-800» (código de cliente fuera); «Airbus A320-251N» → «Airbus A320neo»."""
    t = texto or code or ''
    t = re.sub(r'^(Boeing 7[0-9]7)-([0-9])[0-9A-Z]{2}$', r'\1-\g<2>00', t)
    if re.match(r'^Airbus A3[0-9]{2}-', t):
        t = re.sub(r'-[0-9A-Z]+$', '', t) + ('neo' if (code or '').endswith('N') else '')
    return t


def tramo(f, de='', a=''):
    t, ap = f.get('time') or {}, f.get('airport') or {}
    real, est, sch = t.get('real') or {}, t.get('estimated') or {}, t.get('scheduled') or {}
    st = g(f, 'status', 'generic', 'status', 'text') or ''
    estado = ESTADOS.get(st) or ('Arrived' if real.get('arrival') else 'EnRoute' if real.get('departure') or g(f, 'status', 'live') else 'Expected')
    o, d = ap.get('origin') or {}, ap.get('destination') or {}
    return {'n': g(f, 'identification', 'number', 'default') or '', 'estado': estado,
            'id': g(f, 'identification', 'id') or '', 'cs': g(f, 'identification', 'callsign') or '',   # para abrir el vuelo en directo
            'de': g(o, 'code', 'iata') or de, 'a': g(d, 'code', 'iata') or a,
            'origen': g(o, 'position', 'region', 'city') or '', 'destino': g(d, 'position', 'region', 'city') or '',
            'sp': sch.get('departure') or 0, 'se': real.get('departure') or est.get('departure') or 0,
            'lp': sch.get('arrival') or 0, 'le': real.get('arrival') or est.get('arrival') or g(t, 'other', 'eta') or 0,
            'terminal': g(o, 'info', 'terminal') or '', 'puerta': g(o, 'info', 'gate') or '',
            'reg': g(f, 'aircraft', 'registration') or '', 'modelo': modelo(g(f, 'aircraft', 'model', 'text'), g(f, 'aircraft', 'model', 'code')),
            'aerolinea': g(f, 'airline', 'name') or '', 'iata': g(f, 'airline', 'code', 'iata') or '', 'icao': g(f, 'airline', 'code', 'icao') or ''}


def busca(salidas, n, sp):
    """La salida con ese número (o indicativo) y hora programada a menos de 1 h de sp."""
    for x in salidas:
        f = x.get('flight') or {}
        ide = f.get('identification') or {}
        if n in {g(ide, 'number', 'default'), g(ide, 'number', 'alternative'), ide.get('callsign')} \
                and abs((g(f, 'time', 'scheduled', 'departure') or 0) - sp) < 3600:
            return f
    return None


def entrante(llegadas, reg, sp):
    """La llegada de esa matrícula más tardía antes de sp: el vuelo que trae mi avión."""
    c = [x['flight'] for x in llegadas if g(x, 'flight', 'aircraft', 'registration') == reg
         and 0 < (g(x, 'flight', 'time', 'scheduled', 'arrival') or 0) < sp]
    return max(c, key=lambda f: g(f, 'time', 'scheduled', 'arrival')) if c else None


def aeropuerto(pd, lado):
    """Retraso medio reciente (salidas o llegadas) y METAR de un pluginData de get_airport_details."""
    return {'media': g(pd, 'details', 'stats', lado, 'recent', 'delayAvg') or 0, 'metar': g(pd, 'weather', 'metar') or ''}


def paginas(api, ap, lista, hasta):
    """Páginas de salidas o llegadas hasta pasar de la hora «hasta» (programada); da (pluginData, datos) de cada una."""
    for page in range(1, 7):
        pd = api.get_airport_details(ap, flight_limit=100, page=page)['airport']['pluginData']
        s = pd['schedule'][lista]
        datos = s.get('data') or []
        yield pd, datos
        ts = [g(x, 'flight', 'time', 'scheduled', 'departure' if lista == 'departures' else 'arrival') or 0 for x in datos]
        if not datos or max(ts) > hasta or page >= g(s, 'page', 'total'):
            return


def main(ap, n, sp, reg=''):
    from FlightRadarAPI import FlightRadar24API
    api = FlightRadar24API()
    for pd, datos in paginas(api, ap, 'departures', sp + 3600):
        f = busca(datos, n, sp)
        if f:
            break
    else:
        return {}
    fl = tramo(f, de=ap)
    r = {'fl': fl, 'cadena': [], 'ctx': {'origen': aeropuerto(pd, 'departures'), 'destino': {}}}
    reg = fl['reg'] or reg
    if reg:
        llegadas = [x for _, datos in paginas(api, ap, 'arrivals', sp) for x in datos]
        e = entrante(llegadas, reg, sp)
        if e:
            r['cadena'] = [dict(tramo(e, a=ap), reg=reg)]
    try:
        r['ctx']['destino'] = aeropuerto(api.get_airport_details(fl['a'], flight_limit=1)['airport']['pluginData'], 'arrivals') if fl['a'] else {}
    except Exception:
        pass
    return r


if __name__ == '__main__':
    if sys.argv[1:] == ['--test']:
        mio = {'identification': {'number': {'default': 'UX5053'}, 'callsign': 'AEA29LN'}, 'status': {'generic': {'status': {'text': 'estimated'}}},
               'time': {'scheduled': {'departure': 1000, 'arrival': 5000}, 'real': {'departure': None}, 'estimated': {'departure': 2080}},
               'airport': {'origin': {'info': {'terminal': '3', 'gate': 'E81'}}, 'destination': {'code': {'iata': 'SVQ'}, 'position': {'region': {'city': 'Seville'}}}},
               'aircraft': {'registration': 'EC-NUZ', 'model': {'code': 'B738', 'text': 'Boeing 737-8GP'}}, 'airline': {'name': 'Air Europa', 'code': {'iata': 'UX', 'icao': 'AEA'}}}
        assert busca([{'flight': mio}], 'UX5053', 1500) is mio and busca([{'flight': mio}], 'AEA29LN', 1500) is mio
        assert busca([{'flight': mio}], 'UX5053', 1000 + 86400) is None   # el de otro día
        t = tramo(mio, de='MAD')
        assert (t['de'], t['a'], t['destino'], t['sp'], t['se'], t['lp'], t['estado'], t['terminal'], t['puerta'], t['modelo'], t['iata']) == \
            ('MAD', 'SVQ', 'Seville', 1000, 2080, 5000, 'Expected', '3', 'E81', 'Boeing 737-800', 'UX'), t
        vgo = {'identification': {'id': '4295e739', 'number': {'default': 'UX7317'}, 'callsign': 'AEA7317'}, 'status': {'generic': {'status': {'text': 'scheduled'}}},
               'time': {'scheduled': {'departure': -3000, 'arrival': 600}, 'real': {}, 'estimated': {'departure': -2400}},
               'airport': {'origin': {'code': {'iata': 'VGO'}, 'position': {'region': {'city': 'Vigo'}}}}, 'aircraft': {'registration': 'EC-NUZ'}}
        tarde = dict(vgo, time={'scheduled': {'arrival': 9000}})
        assert entrante([{'flight': vgo}, {'flight': tarde}, {'flight': dict(vgo, aircraft={'registration': 'EC-XXX'})}], 'EC-NUZ', 1000) is vgo
        e = tramo(vgo, a='MAD')
        assert (e['n'], e['de'], e['a'], e['origen'], e['se'], e['estado']) == ('UX7317', 'VGO', 'MAD', 'Vigo', -2400, 'Expected'), e
        assert (e['id'], e['cs'], t['id']) == ('4295e739', 'AEA7317', ''), e
        assert modelo('Airbus A320-251N', 'A20N') == 'Airbus A320neo' and modelo('Airbus A321-231', 'A321') == 'Airbus A321'
        assert modelo('Boeing 787-9 Dreamliner', 'B789') == 'Boeing 787-9 Dreamliner' and modelo(None, 'E195') == 'E195'
        pd = {'details': {'stats': {'arrivals': {'recent': {'delayAvg': 31}}}}, 'weather': {'metar': 'LEZL 151630Z 24012KT TSRA'}}
        assert aeropuerto(pd, 'arrivals') == {'media': 31, 'metar': 'LEZL 151630Z 24012KT TSRA'} and aeropuerto({}, 'arrivals') == {'media': 0, 'metar': ''}
        print('ok')
    else:
        try:
            print(json.dumps(main(sys.argv[1].upper(), sys.argv[2].upper(), int(sys.argv[3]), (sys.argv[4] if len(sys.argv) > 4 else '').upper().strip('-'))))
        except Exception:
            print('{}')
