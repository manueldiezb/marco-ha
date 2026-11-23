#!/usr/bin/env python3
"""Liturgia del día para la tarjeta y la página «Oración» del Marco (corre dentro de Home Assistant).

Escribe /config/www/marco/liturgia.json (público: solo textos litúrgicos). Lo lanza la automatización
«marco_liturgia» cada hora; si el JSON de hoy ya está completo no hace nada (gasta una IA al día).
  · Lecturas (traducción oficial de España): API de WordPress de Magnificat España.
  · Día litúrgico (español) y lista del santoral: Evangelizo.  · Color y próximas fiestas: calapi (calendario romano).
  · Título con números romanos, santos principales y mensajes de cada lectura: gpt-5.4-mini (~0,001 $).
Uso: liturgia.py [AAAA-MM-DD]      MARCO_SIN_IA=1 → sin IA (prueba de lo demás)
"""
import datetime as dt, html, json, os, re, subprocess, sys, unicodedata, urllib.parse, urllib.request

BASE = os.environ.get('MARCO_BASE', '/config')
OUT = f'{BASE}/www/marco/liturgia.json'
MAG = 'https://es.magnificat.net/wp-json/wp/v2/magnificat_content'
CAT = {377: 'lectura', 376: 'salmo', 37: 'evangelio', 38: 'santo', 36: 'intencion'}
UA = {'User-Agent': 'Mozilla/5.0 (Marco familiar)'}


def get(url, js=True):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        b = r.read().decode()
    return json.loads(b) if js else b


def clean(s):
    """HTML de Magnificat → texto: sin guiones blandos ni marcas del salmo; <br> = salto de línea."""
    s = re.sub(r'<span class="(GREP_IMBRIQUES_(Espace_Refrain|Refrain_R|Refrain_Barre)|Puce_de_Fin)">[^<]*</span>', '', s)
    s = re.sub(r'<br\s*/?>\s*', '\n', s)
    return html.unescape(re.sub(r'<[^>]+>', '', s)).replace('\xad', '').replace('\xa0', ' ').strip()


def paras(content, skip=('Titre', 'Lecture_Titre')):
    out = []
    for cls, body in re.findall(r'<p class="([^"]*)"[^>]*>(.*?)</p>', content, re.S):
        if not any(k in cls for k in skip) and clean(body):
            out.append((cls, clean(body)))
    return out


def reading(p, kind):
    c = p['content']['rendered']
    ref = re.search(r'Lecture_Titre_Ref">([^<]*)', c)
    titulo = clean(re.sub(r'<span class="GREP_IMBRIQUES_Lecture_Titre_Ref">.*?</span>', '', html.unescape(p['title']['rendered'])))
    r = {'tipo': kind, 'titulo': re.sub(r'\s*[\d,.\s–—-]+[a-z]?$', '', titulo).strip() if ref else titulo,
         'ref': clean(ref.group(1)) if ref else ''}
    ps = paras(c)
    if kind == 'salmo':
        r['titulo'] = re.sub(r'[—•\s]+', ' ', titulo).strip()               # «—• Salmo 23 •—» → «Salmo 23»
        r['resp'] = next((t for k, t in ps if 'Refrain' in k), '')
        r['texto'] = [t for k, t in ps if 'Refrain' not in k]
    else:
        r['texto'] = [t for _, t in ps]
    return r


def orden(lect):
    """Orden de la misa: 1.ª lectura, salmo, 2.ª lectura (si la hay), Evangelio. Magnificat publica el salmo
    después de las dos lecturas."""
    por = lambda t: [l for l in lect if l['tipo'] == t]
    lecturas = por('lectura')
    return lecturas[:1] + por('salmo') + lecturas[1:] + por('evangelio')


def magnificat(day):
    a, b = (day - dt.timedelta(days=1)).isoformat() + 'T23:59:59', day.isoformat() + 'T23:59:59'
    posts = sorted(get(f'{MAG}?after={a}&before={b}&per_page=50'), key=lambda p: p['date'])
    lect, santo = [], None
    for p in posts:
        kind = next((CAT[c] for c in p['categories'] if c in CAT), None)
        if kind in ('lectura', 'salmo', 'evangelio'):
            lect.append(reading(p, kind))
        elif kind == 'santo':
            ps = paras(p['content']['rendered'], skip=('Nom',))
            santo = {'nombre': clean(p['title']['rendered']),
                     'cita': next((t for k, t in ps if 'Intro' in k), ''),
                     'fecha': next((t for k, t in ps if 'Date' in k), ''),
                     'texto': [t for k, t in ps if 'Texte' in k],
                     'final': next((t for k, t in ps if 'Conclusion' in k), '')}
    lect = orden(lect)
    # la intención del Papa sale el día 1 de cada mes: la última publicada
    it = get(f'{MAG}?categories=36&per_page=1')
    intencion = None
    if it and it[0]['date'][:7] == day.isoformat()[:7]:
        ps = paras(it[0]['content']['rendered'])                  # solo la intención y su explicación, no el resto
        intencion = {'texto': next((t for k, t in ps if 'Intentions_Pape' in k and 'Pape2' not in k), ''),
                     'nota': next((t for k, t in ps if 'Intentions_Pape2' in k), '')}
        intencion = intencion if intencion['texto'] else None
    return lect, santo, intencion


def evangelizo(day, kind):
    try:
        return get(f'https://feed.evangelizo.org/v2/reader.php?date={day:%Y%m%d}&type={kind}&lang=SP', js=False).strip()
    except Exception:
        return ''


def calapi(day):
    """Los días de calapi del mes de hoy y del siguiente (para las próximas fiestas)."""
    days = []
    for d in (day, (day.replace(day=1) + dt.timedelta(days=32))):
        days += get(f'http://calapi.inadiutorium.cz/api/v0/en/calendars/default/{d.year}/{d.month}')
    return {d['date']: d for d in days}


def color(c):
    """Color del día; rosa en Gaudete (III Adviento) y Laetare (IV Cuaresma)."""
    if c['weekday'] == 'sunday' and (c['season'], c['season_week']) in (('advent', 3), ('lent', 4)):
        return 'rose'
    if c['celebrations'][0]['title'] == 'All Souls':
        return 'violet'                                           # en España, Fieles Difuntos en morado
    # ponytail: calapi es el calendario romano general; las fiestas propias de España (p. ej. el Pilar) no cambian el color
    return c['celebrations'][0]['colour']


def ciclo(day, c):
    """Ciclo dominical: el año litúrgico 2025-26 es el A (año en que termina % 3: 1 A, 2 B, 0 C)."""
    fin = day.year + (1 if c['season'] == 'advent' and day.month >= 11 else 0)
    return 'CAB'[fin % 3]


def roman(n):
    out = ''
    for v, s in ((40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')):
        out += s * (n // v); n %= v
    return out


def titulo_base(t):
    """«33er domingo del Tiempo Ordinario» → «XXXIII Domingo del Tiempo Ordinario» (por si falla la IA)."""
    t = re.sub(r'(\d+)\s*(?:o|a|er|era|º|ª)\b', lambda m: roman(int(m.group(1))), t)
    return t[:1].upper() + t[1:].replace(' domingo', ' Domingo')


def ai(data):
    key = open(f'{BASE}/.openai-key').read().strip()
    lect = '\n\n'.join(f"[{i}] {l['tipo']} — {l['titulo']} {l['ref']}\n" + ('R/ ' + l['resp'] + '\n' if l.get('resp') else '')
                       + '\n'.join(l['texto']) for i, l in enumerate(data['lecturas']))
    fiestas = '\n'.join(f"{f['fecha']}: {f['en']}" for f in data['fiestas'])
    q = (f"Hoy es {data['fecha']} en España. Día litúrgico según Evangelizo: «{data['dia_ev']}». "
         f"Calendario romano (inglés): {data['cal_en']}. Santoral de Evangelizo: {', '.join(data['santoral'][:25])}.\n\n"
         f"Lecturas de la misa de hoy:\n{lect}\n\nPróximas fiestas (inglés):\n{fiestas}\n\n"
         'Responde SOLO con JSON, en español de España:\n'
         '{"titulo": nombre oficial del día como en el misal español, con números romanos y mayúsculas así: '
         '«XXXII Domingo del Tiempo Ordinario», «Martes de la XXXI semana del Tiempo Ordinario», «Todos los Santos», '
         '«Jesucristo, Rey del Universo», «San Carlos Borromeo, obispo»,\n'
         ' "santos": los 2 o 3 santos o celebraciones más conocidos de hoy (nombre corto, sin «beato» salvo que sea muy '
         'conocido); si hoy es una solemnidad o fiesta del Señor o de la Virgen, empieza por ella,\n'
         ' "mensajes": una lista con un mensaje por lectura, en el mismo orden [0], [1]…: 1 o 2 frases sencillas y '
         'cálidas (máx. 30 palabras) con la idea principal, para una familia con niños; en el salmo, qué rezamos,\n'
         ' "frase": la frase más importante del Evangelio, copiada literal, de 6 a 16 palabras,\n'
         ' "fiestas": los nombres en español oficial de las próximas fiestas, en el mismo orden}')
    req = urllib.request.Request('https://api.openai.com/v1/responses', json.dumps({'model': 'gpt-5.4-mini', 'input': q}).encode(),
                                 {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.load(r)
    text = res.get('output_text') or ''.join(c.get('text', '') for o in res.get('output', []) if o.get('type') == 'message'
                                             for c in o.get('content', []))
    return json.loads(re.search(r'\{.*\}', text, re.S).group(0))


def palabras(s):
    s = unicodedata.normalize('NFD', s.lower())
    return set(re.findall(r'[a-z]{4,}', ''.join(c for c in s if unicodedata.category(c) != 'Mn'))) - {'santa', 'beato', 'beata'}


def de_hoy(santos, santoral, titulo):
    """Solo los santos de la IA que están en el santoral de Evangelizo o en el título del día: el 15/11/2026 se
    inventó «Santa Isabel de Hungría» (es el 17) a partir de «Beata Isabel Achler»."""
    ok = [palabras(x) for x in santoral + [titulo]]
    return [s for s in santos if palabras(s) and any(palabras(s) <= w for w in ok)]


def build(day):
    old = {}
    try:
        old = json.load(open(OUT))
    except Exception:
        pass
    if old.get('fecha') == day.isoformat() and old.get('completo'):
        return None                                               # ya está el de hoy
    cal = calapi(day)
    c = cal[day.isoformat()]
    lect, santo, intencion = magnificat(day)
    santoral = re.findall(r'>([^<>]+)</a>', evangelizo(day, 'saint'))
    santoral = [html.unescape(s).strip() for s in santoral if 'no ejemplares' not in s]
    dia_ev = html.unescape(re.sub(r'<[^>]+>', '', evangelizo(day, 'liturgic_t')))
    fiestas = [{'fecha': f, 'en': x['celebrations'][0]['title'], 'color': color(x)}
               for f, x in sorted(cal.items())
               if day.isoformat() < f <= (day + dt.timedelta(days=14)).isoformat()
               and x['celebrations'][0]['rank_num'] <= 2.7 and x['celebrations'][0]['rank'] != 'Sunday']
    d = {'fecha': day.isoformat(), 'titulo': titulo_base(dia_ev) or c['celebrations'][0]['title'], 'color': color(c),
         'ciclo': ciclo(day, c), 'santos': santoral[:3], 'frase': '', 'lecturas': lect, 'santo': santo,
         'intencion': intencion, 'fiestas': fiestas, 'santoral': santoral, 'dia_ev': dia_ev,
         'cal_en': '; '.join(f"{x['title']} ({x['rank']}, {x['colour']})" for x in c['celebrations'])}
    if lect and not os.environ.get('MARCO_SIN_IA'):
        r = ai(d)
        d['titulo'] = r.get('titulo') or d['titulo']
        d['santos'] = de_hoy(r.get('santos') or [], santoral, d['titulo']) or d['santos']
        d['frase'] = r.get('frase', '')
        for l, m in zip(lect, r.get('mensajes', [])):
            l['mensaje'] = m
        for f, n in zip(fiestas, r.get('fiestas', [])):
            f['nombre'] = n
        # Magnificat publica pasada la medianoche (Evangelio 00:10, santo ~02:00) y esto corre a las :05: sin
        # Evangelio no se da por hecho el día, y el santo (no lo hay todos los días) se espera hasta las 3
        d['completo'] = any(l['tipo'] == 'evangelio' for l in lect) and (santo is not None or dt.datetime.now().hour >= 3)
    for f in fiestas:
        f.setdefault('nombre', f['en'])
    for k in ('dia_ev', 'cal_en'):
        d.pop(k)
    return d


if __name__ == '__main__':
    if sys.argv[1:] == ['--test']:
        ev = ['San Félix de Nola', 'Beata Isabel Achler', 'San Alberto Magno', 'San Rafael de San José Kalinowski']
        assert de_hoy(['Santa Isabel de Hungría', 'San Alberto Magno', 'San Rafael Kalinowski'], ev,
                      'XXXIII Domingo del Tiempo Ordinario') == ['San Alberto Magno', 'San Rafael Kalinowski']
        assert de_hoy(['Jesucristo, Rey del Universo'], ev, 'Jesucristo, Rey del Universo') == ['Jesucristo, Rey del Universo']
        sys.exit(print('ok'))
    # shell_command corta a los 60 s: el padre lanza un hijo desligado y vuelve enseguida
    if os.environ.get('MARCO_CHILD') != '1' and not os.environ.get('MARCO_FOREGROUND'):
        subprocess.Popen([sys.executable, *sys.argv], env={**os.environ, 'MARCO_CHILD': '1'}, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=open(f'{BASE}/marco/liturgia.err', 'a'))
        sys.exit(0)
    try:
        from zoneinfo import ZoneInfo
        hoy = dt.datetime.now(ZoneInfo('Europe/Madrid')).date()
    except Exception:
        hoy = dt.date.today()
    day = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else hoy
    d = build(day)
    if d:
        tmp = OUT + '.tmp'
        json.dump(d, open(tmp, 'w'), ensure_ascii=False)
        os.replace(tmp, OUT)                                      # atómico: el marco nunca lee un JSON a medias
        print('ok', d['fecha'], d['titulo'], d['color'], len(d['lecturas']), 'lecturas')
