#!/usr/bin/env python3
"""Carrito de Mercadona para el Marco. Usa la API interna (no oficial) de tienda.mercadona.es, la misma que
documenta github.com/jjolmo/mercadona-mcp (revisado el 2026-11-01; aquí no se usa su código).

Uso (shell_command.marco_mercadona): mercadona.py <base64 de un JSON {"cmd": ..., ...}>  ->  JSON por stdout
  lista                      el carrito
  cambiar  {id, delta, min}  suma o resta en el carrito (en kg si va a peso) y devuelve el carrito releído
  habituales                 índice de lo comprado en los últimos pedidos y tickets de tienda (caché de 12 h o hasta
                             un pedido o ticket nuevo). Tickets: Gmail por IMAP, solo de ticket_digital@, sin guardar correos
  buscar   {q}               catálogo del almacén de la zona (Algolia, la búsqueda pública de la web)
  sesion   {dato}            guarda el MO-user de la web (o un refresh token) y comprueba que entra
  ocultar  {id, volver?}     quita un producto de los habituales (ya no se compra); con volver, lo recupera
A propósito NO hay nada para pedir, pagar ni cambiar pedidos ya hechos: el Marco solo toca el carrito.
"""
import base64, fcntl, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, unicodedata, zlib
from concurrent.futures import ThreadPoolExecutor

BASE = os.environ.get('MARCO_BASE', '/config')
SESSION = f'{BASE}/.mercadona'                       # tokens: modo 600, nunca bajo www/
CACHE = f'{BASE}/marco/mercadona-habituales.json'
WEB = f'{BASE}/marco/mercadona-web.json'
OCULTOS = f'{BASE}/marco/mercadona-ocultos.json'     # ids quitados de los habituales desde el Marco (para todos)
SHOP = 'https://tienda.mercadona.es'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
ORDERS = 100                                         # pedidos online que se leen (todos, en la práctica)
HALF = 182                                           # días: una compra de hace medio año cuenta la mitad


class AuthError(Exception): pass
class ApiError(Exception):
    def __init__(self, msg, status): super().__init__(msg); self.status = status


def load(path, default=None):
    try:
        with open(path) as f: return json.load(f)
    except (OSError, ValueError): return default


def save(path, data, secret=False):
    tmp = path + '.tmp'
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600 if secret else 0o644), 'w') as f: json.dump(data, f)
    os.replace(tmp, path)


def http(method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else None), r.headers
    except urllib.error.HTTPError as e:
        return e.code, None, e.headers


def jwt_claims(tok):
    try: return json.loads(base64.urlsafe_b64decode(tok.split('.')[1] + '=='))
    except Exception: return {}


# --- Web: versión (cabecera x-version) y clave pública de Algolia, leídas del bundle; 7 días de caché ---
def web():
    meta = load(WEB, {})
    if meta.get('key') and time.time() - meta.get('at', 0) < 7 * 86400: return meta
    def get(url): return urllib.request.urlopen(urllib.request.Request(url, headers={'user-agent': UA}), timeout=20).read().decode()
    path = re.search(r'/v\d+/index-[A-Za-z0-9_-]+\.js', get(SHOP + '/'))
    if not path: raise Exception('No encuentro la web de Mercadona')
    js = get(SHOP + path[0])
    pair = re.search(r'"([A-Z0-9]{10})",[A-Za-z0-9_$]+="([0-9a-f]{32})"', js)
    if not pair: raise Exception('No encuentro la búsqueda de Mercadona')
    idx = re.search(r'"(products_prod[a-z_]*)"', js)
    meta = {'version': re.search(r'/(v\d+)/', path[0])[1], 'app': pair[1], 'key': pair[2],
            'index': idx[1] if idx else 'products_prod', 'at': time.time()}
    save(WEB, meta)
    return meta


# --- Sesión ---
class Mercadona:
    def __init__(self):
        self.s = load(SESSION, {})

    def headers(self, auth=True):
        h = {'accept': 'application/json', 'accept-language': 'es-ES,es;q=0.9', 'content-type': 'application/json',
             'user-agent': UA, 'origin': SHOP, 'referer': SHOP + '/'}
        v = load(WEB, {}).get('version')
        if v: h['x-version'] = v
        if auth and self.s.get('access_token'): h['authorization'] = 'Bearer ' + self.s['access_token']
        return h

    def refresh(self):
        # Mercadona cambia el refresh token en cada renovación: con dos llamadas a la vez, la segunda gastaría uno ya
        # usado. Con el candado, la que llega tarde relee el fichero y, si otra ya renovó, usa ese token.
        stale = self.s.get('access_token')
        with open(SESSION + '.lock', 'w') as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            self.s = load(SESSION, {})
            if self.s.get('access_token') and self.s['access_token'] != stale: return
            if not self.s.get('refresh_token'): raise AuthError('Falta conectar Mercadona en Ajustes')
            st, tok, _ = http('POST', f'{SHOP}/api/auth/tokens/?lang=es', {'refresh_token': self.s['refresh_token']}, self.headers(False))
            if st != 200 or not tok or not tok.get('access_token'):
                raise AuthError(f'La sesión de Mercadona ha caducado ({st}): vuelve a conectarla en Ajustes')
            self.s['access_token'] = tok['access_token']
            if tok.get('refresh_token'): self.s['refresh_token'] = tok['refresh_token']
            self.learn(tok)
            save(SESSION, self.s, secret=True)

    def learn(self, tok=None):
        c = jwt_claims(self.s.get('access_token') or '')
        cid = (tok or {}).get('customer_uuid') or (tok or {}).get('customer_id') or c.get('customer_uuid') or c.get('uuid') or c.get('customer_id')
        if cid and not self.s.get('customer_id'): self.s['customer_id'] = cid

    def api(self, method, path, body=None, retry=True):
        if not self.s.get('access_token'): self.refresh()
        path = path.replace('/:me/', f"/{self.s.get('customer_id')}/")
        url = f"{SHOP}/api{path}{'&' if '?' in path else '?'}lang=es" + (f"&wh={self.s['warehouse']}" if self.s.get('warehouse') else '')
        st, data, hd = http(method, url, body, self.headers())
        wh = hd.get('x-customer-wh') if hd else None
        if wh and wh != self.s.get('warehouse'):
            self.s['warehouse'] = wh
            save(SESSION, self.s, secret=True)
        if st == 401 and retry:
            self.refresh()
            return self.api(method, path, body, False)
        if st >= 400: raise ApiError(f'{method} {path.split("?")[0]} -> {st}', st)
        return data


# --- Carrito ---
def lines_of(cart):
    return [p for l in (cart or {}).get('lines') or [] for p in (l.get('products') or [l])]


def fmt(p, pi):
    """Formato como en la web: «6 briks × 1 L», «Brik 1 L», «Pieza 0,2 kg aprox.»."""
    n = lambda v: f'{float(v):g}'.replace('.', ',') if v not in (None, '') else ''
    unit = {'l': 'L'}.get(pi.get('size_format'), pi.get('size_format') or '')
    if pi.get('is_pack'): txt = f"{pi.get('total_units') or ''} {pi.get('unit_name') or ''} × {n(pi.get('pack_size'))} {unit}"
    else: txt = f"{p.get('packaging') or ''} {n(pi.get('unit_size'))} {unit}" + (' aprox.' if pi.get('approx_size') else '')
    txt = ' '.join(txt.split())
    return txt if re.search(r'\d', txt) else None      # sin tamaño (p. ej. «× ud») no dice nada


def item(p, qty=None):
    """Lo que la página necesita de un producto (de carrito, pedido o Algolia)."""
    pi = p.get('price_instructions') or {}
    sm = pi.get('selling_method') or 0              # 0 = unidades; otro valor = a peso, cantidad en kg
    num = lambda v: float(v) if v not in (None, '') else None
    src = p.get('thumbnail') or ((p.get('photos') or [{}])[0].get('regular'))
    out = {'id': str(p.get('id') or p.get('product_id')), 'name': p.get('display_name') or p.get('name') or '?',
           'img': src.split('?')[0] + '?fit=crop&w=200&h=200' if src else None,
           'price': num(pi.get('unit_price')), 'ref': f"{pi['reference_price']} €/{pi.get('reference_format')}" if pi.get('reference_price') else None,
           'fmt': fmt(p, pi), 'sm': sm, 'step': num(pi.get('increment_bunch_amount')) if sm else 1,
           'min': num(pi.get('min_bunch_amount')) if sm else 1}
    if not out['step']: out['step'] = 1
    if not out['min']: out['min'] = out['step']
    if qty is not None: out['qty'] = qty
    return out


def cart_view(cart):
    items = [item(l.get('product') or l, l.get('quantity')) for l in lines_of(cart)]
    total = (cart.get('summary') or {}).get('total')
    if total is None:   # ponytail: igual que el repo; a peso se toma el precio de referencia (€/kg)
        total = sum(float((l.get('product') or {}).get('price_instructions', {}).get('reference_price' if i['sm'] else 'unit_price') or 0) * float(i['qty'] or 0)
                    for l, i in zip(lines_of(cart), items))
    return {'ok': True, 'items': items, 'count': len(items), 'total': round(float(total), 2)}


def apply_delta(cart, pid, delta, minimum=1):
    """Líneas para el PUT con `delta` aplicado a `pid`. Por debajo del mínimo, el producto sale del carrito."""
    lines = [{'product_id': str((l.get('product') or {}).get('id') or l.get('product_id')), 'quantity': l.get('quantity'),
              'sources': l.get('sources') or []} for l in lines_of(cart)]
    line = next((l for l in lines if l['product_id'] == pid), None)
    before = line['quantity'] if line else 0
    after = round(before + delta, 3)
    if after < minimum - 1e-6: after = 0
    if line: line['quantity'] = after
    elif after > 0: lines.append({'product_id': pid, 'quantity': after, 'sources': []})
    return [l for l in lines if l['quantity'] > 0], after


def cambiar(m, pid, delta, minimum=1):
    pid = str(pid)
    for attempt in range(2):
        cart = m.api('GET', '/customers/:me/cart/')
        lines, after = apply_delta(cart, pid, float(delta), minimum)
        body = {'id': cart.get('id'), 'lines': lines}
        if cart.get('version') is not None: body['version'] = cart['version']
        try:
            m.api('PUT', '/customers/:me/cart/', body)
            break
        except ApiError as e:   # otro móvil cambió el carrito a la vez: se relee y se repite una vez
            if e.status in (409, 412) and not attempt: continue
            raise
    view = cart_view(m.api('GET', '/customers/:me/cart/'))
    got = next((i['qty'] for i in view['items'] if i['id'] == pid), 0)
    if abs((got or 0) - after) > 1e-6: view.update(ok=False, error='Mercadona no ha guardado el cambio')
    return view


# --- Habituales: lo comprado en los últimos pedidos, para sugerir al escribir ---
def habituales(m):
    first = m.api('GET', '/customers/:me/orders/?page=1')
    cache = load(CACHE, {})
    try: tk = tickets_sync(m, {i['id'] for i in (cache.get('data') or {}).get('items') or []})
    except Exception as e:                            # sin Gmail o caído: se sigue solo con pedidos
        print(f'tickets: {e}', file=sys.stderr)
        tk = load(TICKETS, {'uid': 0, 'tickets': [], 'map': {}})
    newest = str(((first or {}).get('results') or [{}])[0].get('id')) + f"/{tk['uid']}/{len(tk['map'])}"
    if cache.get('newest') == newest and time.time() - cache.get('at', 0) < 12 * 3600: return cache['data']
    orders, page, data = [], 1, first
    while True:
        for o in data.get('results') or []:
            if 'cancel' in str(o.get('status_ui') or o.get('status')).lower(): continue
            orders.append(o)
        if len(orders) >= ORDERS or not data.get('next_page') or page >= 10: break
        page += 1
        data = m.api('GET', f'/customers/:me/orders/?page={page}')
    orders = orders[:ORDERS]

    def order_lines(o):
        out = []
        for p in range(1, 10):
            d = m.api('GET', f"/customers/:me/orders/{o.get('order_id') or o['id']}/lines/prepared/?page={p}")
            out += d.get('results') or []
            if not d.get('next_page') or not d.get('results'): break
        return o, out
    # en paralelo: shell_command corta a los 60 s y son ~30 pedidos
    with ThreadPoolExecutor(6) as ex: done = list(ex.map(order_lines, orders))
    # compras = pedidos + tickets de tienda, todo el histórico; cada una cuenta una vez por producto
    buys = []
    for o, lines in done:
        date = (o.get('start_date') or (o.get('slot') or {}).get('start') or '')[:10]
        buys.append((date, [(item({**(l.get('product') or {}), 'id': str(l.get('product_id') or (l.get('product') or {}).get('id'))}),
                             float(l.get('ordered_quantity') or l.get('quantity') or 1)) for l in lines]))
    online = {d for d, _ in buys}
    for t in tk['tickets']:
        if t['date'] in online: continue              # por si Mercadona manda también el ticket de un pedido online
        buys.append((t['date'], [(tk['map'][n], float(q)) for n, q in t['lines'] if tk['map'].get(n)]))   # None = ignorar (bolsa…)
    buys = sorted(buys, key=lambda b: b[0], reverse=True)
    today = time.strftime('%Y-%m-%d')
    age = lambda d: (time.mktime(time.strptime(today, '%Y-%m-%d')) - time.mktime(time.strptime(d, '%Y-%m-%d'))) / 86400 if d else 9999
    stats = {}
    for date, lines in buys:
        for it, qty in lines:
            s = stats.setdefault(it['id'], {**it, 'times': 0, 'qtys': [], 'last': '', 'seen': ''})
            if s['seen'] == date: s['qtys'][-1] += qty  # dos líneas del mismo producto en una compra: se suman
            else: s['times'] += 0.5 ** (age(date) / HALF); s['qtys'].append(qty)   # «times» = veces, pesando lo reciente
            s['seen'] = date
            s['last'] = max(s['last'], date)
    for s in stats.values():
        q = sorted(s.pop('qtys')[:10])               # las 10 últimas: la cantidad de ahora, no la de hace años
        s['times'] = round(s['times'], 2)
        s['usual'] = q[len(q) // 2]                   # cantidad típica (mediana)
        del s['seen']
    data = {'ok': True, 'orders': len(buys), 'items': sorted(stats.values(), key=lambda s: -s['times'])}
    save(CACHE, {'newest': newest, 'at': time.time(), 'data': data})
    return data


# --- Tickets de tienda (opcional): de un Gmail, solo los correos de Mercadona ---
# Nada del correo se guarda: se pide solo la parte PDF, se lee en memoria y queda lo derivado (fecha, nombre, cantidad).
GMAIL = f'{BASE}/.mercadona-gmail'                   # {"user", "password"} (contraseña de aplicación), modo 600
TICKETS = f'{BASE}/marco/mercadona-tickets.json'     # {uid, tickets: [{date, lines: [[nombre, cant]]}], map, pending}
SENDER = 'ticket_digital@mail.mercadona.com'


def ticket(pdf):
    """PDF del ticket → {date, total, lines: [{name, qty, price, kg}]}. Lee el texto por coordenadas (stdlib)."""
    streams = []
    for s in re.findall(rb'stream\r?\n(.*?)endstream', pdf, re.S):
        try: streams.append(zlib.decompress(s))
        except zlib.error: pass                       # imágenes y demás
    # Desde 2025 (openhtmltopdf) el texto va en glifos de 2 bytes; la tabla ToUnicode del propio PDF dice qué letra es cada uno
    uni = {}
    for t in streams:
        for a, b in re.findall(rb'<([0-9A-Fa-f]{4})>\s*<([0-9A-Fa-f]+)>', b''.join(re.findall(rb'beginbfchar(.*?)endbfchar', t, re.S))):
            uni[int(a, 16)] = bytes.fromhex(b.decode()).decode('utf-16-be')
        for a, b, c in re.findall(rb'<([0-9A-Fa-f]{4})>\s*<([0-9A-Fa-f]{4})>\s*<([0-9A-Fa-f]+)>', b''.join(re.findall(rb'beginbfrange(.*?)endbfrange', t, re.S))):
            for i in range(int(a, 16), int(b, 16) + 1): uni[i] = chr(int(c, 16) + i - int(a, 16))

    def text(raw):
        if raw[:1] == b'<': b = bytes.fromhex(raw[1:-1].decode())
        else: b = re.sub(rb'\\([0-7]{1,3}|.)', lambda m: bytes([int(m[1], 8)]) if m[1][:1].isdigit() else
                         {b'n': b'\n', b'r': b'\r', b't': b'\t'}.get(m[1], m[1]), raw[1:-1], flags=re.S)
        if uni and len(b) % 2 == 0: return ''.join(uni.get(int.from_bytes(b[i:i + 2], 'big'), '?') for i in range(0, len(b), 2))
        return b.decode('latin-1')

    rows = {}
    for t in streams:
        for x, y, raw in re.findall(rb'1 0 0 1 ([\d.]+) ([\d.]+) Tm\s*(\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f]*>)\s*Tj', t, re.S):
            rows.setdefault(round(float(y)), []).append((float(x), text(raw).strip()))
    num = lambda v: float(v.replace(',', '.'))
    out, inside = {'date': None, 'total': None, 'lines': []}, False
    for y in sorted(rows, reverse=True):
        cells = sorted(rows[y])
        text = ' '.join(c for _, c in cells)
        d = re.search(r'(\d\d)/(\d\d)/(\d{4}) \d\d:\d\d', text)
        if d and not out['date']: out['date'] = f'{d[3]}-{d[2]}-{d[1]}'
        if 'Descripción' in text: inside = True; continue      # 2025: «Cnt. Descripción …»
        if not inside: continue
        if text.startswith('TOTAL'): out['total'] = num(cells[-1][1]); break
        kg = re.match(r'([\d,]+) kg ([\d,]+) \S+/kg ([\d,]+)$', text)
        if kg and out['lines']:                       # segunda fila de lo que va a peso
            out['lines'][-1].update(kg=num(kg[1]), price=num(kg[2])); continue
        qty = [c for x, c in cells if x < 80 and c.isdigit()]
        name = [c for x, c in cells if 80 <= x < 300]
        price = [c for x, c in cells if x >= 300]
        if not name: continue
        q = int(qty[0]) if qty else 1                 # pescadería: sin cantidad, el peso va en la fila siguiente
        unit = num(price[0]) if len(price) == 2 else (num(price[0]) / q if price else None)
        out['lines'].append({'name': name[0], 'qty': q, 'price': round(unit, 2) if unit else None, 'kg': None})
    out['lines'] = [l for l in out['lines'] if l['price']]   # fuera los encabezados de sección («PESCADO»)
    return out


def gmail_pdfs(since_uid, limit):
    """(uid, bytes del PDF) de los correos de SENDER con uid > since_uid. Solo lectura y solo la parte PDF."""
    import imaplib
    cred = load(GMAIL)
    if not cred: return []
    with imaplib.IMAP4_SSL('imap.gmail.com', timeout=20) as im:
        im.login(cred['user'], cred['password'])
        box = next((re.search(rb'"([^"]+)"$', l)[1].decode() for _, ls in [im.list()] for l in ls if b'\\All' in l), 'INBOX')
        im.select(f'"{box}"', readonly=True)                       # EXAMINE: no marca nada como leído
        _, ids = im.uid('SEARCH', None, f'(FROM "{SENDER}" UID {since_uid + 1}:*)')
        out = []
        # ponytail: tope por pasada para caber en los 60 s de shell_command; el histórico se carga a mano con tope alto
        for uid in sorted(int(u) for u in ids[0].split() if int(u) > since_uid)[:limit]:
            for part in ('2', '1.2', '3', '1'):                    # dónde suele ir el adjunto
                _, h = im.uid('FETCH', str(uid), f'(BODY.PEEK[{part}.MIME])')
                head = (h[0][1] if h and isinstance(h[0], tuple) else b'').lower()
                if b'pdf' not in head: continue
                _, b = im.uid('FETCH', str(uid), f'(BODY.PEEK[{part}])')
                out.append((uid, base64.b64decode(b[0][1]) if b'base64' in head else b[0][1]))
                break
            else: out.append((uid, None))               # sin PDF: se salta, pero no se vuelve a mirar
        return out


def guess(m, name, price, known):
    """Producto de la tienda para un nombre de ticket, o None si no está claro. Precio ±15 % (los precios cambian)."""
    q = re.sub(r'\b(S/|P-?\d+|\d+ ?(G|KG|L|ML|CL))\b', ' ', name.replace('S/G', 'SIN GLUTEN').replace('S/LACT', 'SIN LACTOSA'))
    hits = buscar(m, ' '.join(q.split()).lower())['items'][:12]
    words = lambda s: re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode())
    toks = [w[:4] for w in words(q) if len(w) >= 3 and not w.isdigit()]
    # cada palabra del ticket tiene que empezar alguna del nombre («PETIT DE BOLSILLO FR» → «Petit de bolsillo sabor fresa»)
    named = [h for h in hits if toks and all(any(x.startswith(t) for x in words(h['name'])) for t in toks)]
    each = lambda h: float(h['ref'].split()[0]) if h['sm'] and h['ref'] else h['price']   # a peso: €/kg
    ok = sorted((h for h in named if price and each(h) and abs(each(h) - price) <= 0.3 * price), key=lambda h: abs(each(h) - price))
    mine = [h for h in ok if h['id'] in known]
    if mine: return mine[0]
    return ok[0] if len(ok) == 1 or (ok and abs(each(ok[0]) - price) <= 0.02) else None


def tickets_sync(m, known, limit=10):
    """Trae los tickets nuevos y pone en `pending` los nombres que no sabe casar. Devuelve el estado guardado."""
    st = load(TICKETS, {'uid': 0, 'tickets': [], 'map': {}, 'pending': {}})
    new = gmail_pdfs(st['uid'], limit)
    for uid, pdf in new:
        st['uid'] = max(st['uid'], uid)
        t = ticket(pdf) if pdf else None
        if not t or not t['date'] or not t['lines']: continue
        st['tickets'].append({'date': t['date'], 'lines': [[l['name'], l['kg'] or l['qty']] for l in t['lines']]})
        for l in t['lines']:
            n = l['name']
            if n in st['map'] or n in st['pending']: continue
            try: hit = guess(m, n, l['price'], known)
            except Exception: hit = None
            if hit: st['map'][n] = hit
            else: st['pending'][n] = l['price']
    if new: save(TICKETS, st)
    return st


def buscar(m, q):
    meta = web()
    if not m.s.get('warehouse') and m.s.get('customer_id'):
        try: m.api('GET', '/customers/:me/')     # la cabecera x-customer-wh dice el almacén de la zona
        except Exception: pass
    wh = (m.s.get('warehouse') or 'mad1').lower()
    st, res, _ = http('POST', f"https://{meta['app'].lower()}-dsn.algolia.net/1/indexes/{meta['index']}_{wh}_es/query",
                      {'params': urllib.parse.urlencode({'query': q, 'hitsPerPage': 12})},
                      {'X-Algolia-Application-Id': meta['app'], 'X-Algolia-API-Key': meta['key'], 'content-type': 'application/json'})
    if st == 403: os.remove(WEB)                 # la clave cambió: la próxima vez se vuelve a leer de la web
    if st != 200: raise Exception(f'Búsqueda -> {st}')
    return {'ok': True, 'items': [item(h) for h in res.get('hits') or [] if h.get('published', True)]}


def sesion(dato):
    dato = dato.strip()
    o = json.loads(dato) if dato.startswith('{') else {'refresh_token': dato}
    s = {'refresh_token': o.get('refresh_token') or o.get('refreshToken'),
         'customer_id': o.get('customer_id') or o.get('customer_uuid') or o.get('uuid')}
    if not s['refresh_token']: raise Exception('Eso no parece el MO-user de Mercadona')
    save(SESSION, {k: v for k, v in s.items() if v}, secret=True)
    m = Mercadona()
    m.refresh()
    me = m.api('GET', '/customers/:me/')
    return {'ok': True, 'name': me.get('name'), 'email': me.get('email')}


def ocultar(pid, volver=False):
    ids = set(load(OCULTOS, []))
    (ids.discard if volver else ids.add)(str(pid))
    save(OCULTOS, sorted(ids))
    return {'ok': True, 'ocultos': sorted(ids)}


def sin_ocultos(data):
    ids = set(load(OCULTOS, []))
    return {**data, 'items': [i for i in data['items'] if str(i['id']) not in ids]}


def main(arg):
    req = json.loads(base64.b64decode(arg))
    cmd = req.get('cmd')
    if cmd == 'sesion': return sesion(req.get('dato') or '')
    if cmd == 'ocultar': return ocultar(req['id'], req.get('volver'))
    m = Mercadona()
    if cmd == 'lista': return cart_view(m.api('GET', '/customers/:me/cart/'))
    if cmd == 'cambiar': return cambiar(m, req['id'], req['delta'], req.get('min') or 1)
    if cmd == 'habituales': return sin_ocultos(habituales(m))
    if cmd == 'buscar': return buscar(m, str(req.get('q') or '')[:80])
    raise Exception('Orden desconocida')


if __name__ == '__main__':
    try: out = main(sys.argv[1])
    except AuthError as e: out = {'ok': False, 'auth': True, 'error': str(e)}
    except Exception as e: out = {'ok': False, 'error': str(e) or type(e).__name__}
    print(json.dumps(out, ensure_ascii=False))
