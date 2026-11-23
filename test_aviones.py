# Comprueba aviones.jinja con jinja2 y los filtros de HA imitados. python3 test_aviones.py -> "ok"
import json, re, jinja2
env = jinja2.Environment(loader=jinja2.FileSystemLoader("."), extensions=["jinja2.ext.loopcontrols"])
env.filters["regex_replace"] = lambda v, f, t: re.sub(f, t, v)
env.filters["to_json"] = lambda v: json.dumps(v, ensure_ascii=False)
env.filters["from_json"] = json.loads
env.tests["match"] = lambda v, p: bool(re.match(p, v))
import math
env.tests["search"] = lambda v, p: bool(re.search(p, v))
env.globals.update(cos=math.cos, sin=math.sin, pi=math.pi)
from datetime import datetime
env.globals["now"] = datetime.now   # HA la da; aquí, la del Mac
env.globals["as_timestamp"] = lambda v, d=None: datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp() if v else d
pos = lambda lat, lon, hdg: dict(latitude=lat, longitude=lon, heading=hdg)
def run(flights, ahora=None, ga=()):
    t = env.from_string("{% from 'aviones.jinja' import avion_cercano %}{{ avion_cercano(fl, ahora=ahora, ga_prev=ga) }}")
    return json.loads(t.render(fl=flights, ahora=ahora, ga=list(ga)))
rodando = dict(callsign="IBE1", aircraft_model="Airbus A320-214", aircraft_code="A320", on_ground=1, ground_speed=15, altitude=0, distance=4.0)
crucero = dict(callsign="RYR2", aircraft_model="Boeing 737-8AS", aircraft_code="B738", on_ground=0, altitude=36000, distance=1.0)
despega = dict(callsign="VLG3", flight_number="VY1003", aircraft_model="Airbus A321-271NX", aircraft_code="A21N", airline_short="Vueling",
               airport_origin_code_iata="MAD", airport_origin_city="Madrid", airport_destination_city="Barcelona",
               on_ground=0, altitude=4500, distance=3.2, vertical_speed=2500, latitude=40.53, longitude=-3.5747, heading=2)
llega = dict(callsign="AEA4", aircraft_model="Boeing 787-9 Dreamliner", aircraft_code="B789", airline_short="Air Europa",
             airport_destination_code_iata="MAD", on_ground=0, altitude=5000, distance=6.5, vertical_speed=-800)
carrera = dict(callsign="IBE5", aircraft_model="Airbus A350-941", aircraft_code="A359", airline_short="Iberia",
               airport_origin_code_iata="MAD", on_ground=1, ground_speed=140, altitude=0, distance=5.0, latitude=40.505, longitude=-3.5747, heading=2)

r = run([rodando, crucero, despega, llega])
assert r["modelo"] == "Airbus A321neo", r
assert r["frase"].startswith("Airbus A321neo de Vueling, que acaba de despegar de Barajas. Vuelo VY1003 de Madrid a Barcelona."), r
assert "Está a 2500 pies de altura y a 3,2 kilómetros" in r["frase"] and "Cerca también" not in r["frase"], r
assert [c.split()[0] for c in r["candidatos"]] == ["VLG3", "RYR2"], r   # el de crucero sobrevuela (detrás); ni el que rueda ni el que baja lejos
assert run([rodando, crucero])["modelo"] == "Boeing 737"   # crucero justo encima de casa
assert run([dict(despega, distance=15)])["frase"].startswith("No hay ninguno muy cerca. El más próximo es un Airbus A321neo de Vueling, a 15 kilómetros"), run([dict(despega, distance=15)])
assert "pies de altura" not in run([dict(despega, altitude=2100)])["frase"]
assert run([carrera])["frase"].startswith("Airbus A350 de Iberia, despegando de Barajas."), run([carrera])
assert run([dict(despega, callsign="X", airline_short="Iberia", distance=3.0), dict(despega, distance=3.3)])["frase"].count("Cerca también hay un Airbus A321neo de Vueling") == 1
assert run([llega])["modelo"] == "ninguno"   # aterrizando: no cuenta
assert run([dict(carrera, ground_speed=35)])["modelo"] == "ninguno"   # rodando a 35 kt: no cuenta
assert run([dict(carrera, airport_destination_code_iata="MAD", airport_origin_code_iata="BCN")])["modelo"] == "ninguno"   # frenando tras aterrizar
assert run([dict(despega, vertical_speed=0)])["modelo"] == "Airbus A321neo"   # nivelado tras despegar (sigue en el eje)
assert run([dict(crucero, vertical_speed=0, distance=3.5)])["modelo"] == "ninguno"   # a 3,5 km: fuera del radio de sobrevuelo
assert run([dict(despega, distance=12.5)])["modelo"] == "Airbus A321neo"   # radio 13 km
assert run([dict(crucero, altitude=6000, distance=2, vertical_speed=1500)])["modelo"] == "Boeing 737"   # sobrevuela casa a ~1100 m
assert run(None)["modelo"] == "ninguno"
assert run([dict(crucero, aircraft_model="Boeing 777-323(ER)", altitude=6000, distance=2, vertical_speed=1500)])["modelo"] == "Boeing 777"
i = run([rodando, crucero, despega, llega])["info"]
assert (i["modelo"], i["aerolinea"], i["destino"], i["fase"], i["alt"], i["km"]) == ("Airbus A321neo", "Vueling", "Barcelona", "vuelo", 800, 3.2), i
assert run([carrera])["info"]["fase"] == "despegue"
assert run([despega])["info"]["de"] == "MAD" and run([despega])["info"]["tipo"] == "A21N"
assert run([dict(despega, airport_origin_code_iata="BCN", airport_destination_code_iata="MAD", ground_speed=150, **pos(40.47, -3.561, 324))])["info"]["fase"] == "frustrada"
assert "info" not in run([llega])
# pista: en carrera por la 36L (rumbo 2, sobre su eje), por la 36R, la 14R, y nada si ya ha virado
assert run([dict(carrera, **pos(40.505, -3.5747, 2))])["info"]["pista"] == "36L"
assert run([dict(despega, distance=2.5, **pos(40.545, -3.5593, 1))])["info"]["pista"] == "36R"   # por la 36R solo si sobrevuela
assert run([dict(despega, distance=2.5, **pos(40.445, -3.535, 144))])["info"]["pista"] == "14R"
assert run([dict(despega, distance=2.5, **pos(40.60, -3.50, 60))])["info"]["pista"] == ""
assert run([dict(despega, airport_origin_code_iata="BCN", airport_destination_code_iata="MAD", ground_speed=150, **pos(40.47, -3.561, 324))])["info"]["pista"] == "32L"   # go-around
i = run([dict(despega, ground_speed=160)])["info"]
assert (i["ft"], i["m"], i["kt"], i["kmh"]) == (4500, 1372, 160, 296), i
# Cuatro Vientos fuera, salga o llegue
assert run([dict(despega, airport_origin_code_iata="QYU")])["modelo"] == "ninguno"
assert run([dict(despega, airport_origin_code_iata=None, airport_destination_code_icao="LECU")])["modelo"] == "ninguno"
# retraso: llegada estimada si la hay; si no, salida real/estimada; sin horarios, None
t0 = 1792936800
# salida de la T4 por la 36L: rodaje 17 min; despega 27 min después de la hora de puerta -> 10 min de retraso
sale = dict(despega, airport_origin_terminal="4", time_scheduled_departure=t0)
assert run([sale], ahora=t0 + 27 * 60)["info"]["retraso"] == 10
assert run([sale], ahora=t0 + 27 * 60)["info"]["rodaje"] == 17
assert run([dict(sale, airport_origin_terminal="4S")], ahora=t0 + 27 * 60)["info"]["retraso"] == 13
assert run([dict(sale, airport_origin_terminal=None)], ahora=t0 + 27 * 60)["info"]["retraso"] == 9   # sin terminal: 18
assert run([dict(sale, time_scheduled_departure=0)], ahora=t0)["info"]["retraso"] is None
# llegadas (go-around): estimada contra prevista
assert run([dict(despega, airport_origin_code_iata="BCN", airport_destination_code_iata="MAD", ground_speed=150, time_scheduled_arrival=t0, time_estimated_arrival=t0 + 1500, **pos(40.47, -3.561, 324))])["info"]["retraso"] == 25
# reglas: despegues solo por 36L/18R; go-arounds; y lo que pasa por encima de casa
assert run([dict(despega, **pos(40.545, -3.5593, 1))])["info"]["secundario"] is False   # 36R a 3,2 km: pasa cerca de casa, cuenta como principal
assert run([dict(carrera, **pos(40.47, -3.5747, 181))])["info"]["pista"] == "18R"   # configuración sur
assert run([dict(despega, distance=9, **pos(40.60, -3.50, 60))])["modelo"] == "ninguno"   # ya ha virado y está lejos de casa
assert run([dict(despega, distance=2.8, **pos(40.60, -3.50, 270))])["modelo"] == "Airbus A321neo"   # ha virado hacia casa
assert run([dict(llega, distance=1.5)])["modelo"] == "Boeing 787-9 Dreamliner"   # llegada que pasa por encima de casa
assert run([dict(llega, distance=1.5, altitude=43000)])["modelo"] == "Boeing 787-9 Dreamliner"   # sobrevuelo a cualquier altura
# reversas: avión grande frenando en la 32L (rumbo 324, sobre su eje); uno pequeño, en otra pista o ya rodando, no
frena = dict(llega, aircraft_code="B789", on_ground=1, ground_speed=110, altitude=0, distance=5.5, vertical_speed=0, **pos(40.468, -3.559, 324))
r = run([frena])
assert r["info"]["fase"] == "aterrizaje" and r["info"]["pista"] == "32L", r
assert "aterrizando en Barajas por la 32L" in r["frase"], r
assert run([dict(frena, aircraft_code="A320", aircraft_model="Airbus A320-214")])["modelo"] == "ninguno"
assert run([dict(frena, aircraft_code="A359")])["modelo"] == "Boeing 787-9 Dreamliner"
assert run([dict(frena, **pos(40.482, -3.541, 324))])["modelo"] == "ninguno"   # 32R
assert run([dict(frena, ground_speed=30)])["modelo"] == "ninguno"
assert run([dict(despega, id="3c1a2b4f")])["info"]["fr24"] == "https://www.flightradar24.com/VLG3/3c1a2b4f"
assert run([despega])["info"]["fr24"] == ""
# go-around (opción B): sube ≥ 500 ft/min a ≥ 130 kt. Los falsos de la toma (+64 ft/min a 70-146 kt) no cuentan
ga = dict(despega, id="ga1", callsign="AFR1", airport_origin_code_iata="CDG", airport_destination_code_iata="MAD", ground_speed=150,
          vertical_speed=1800, distance=9, **pos(40.47, -3.561, 324))
r = run([ga])
assert r["info"]["fase"] == "frustrada" and r["ga"] == ["ga1"] and "go-around" in r["frase"], r
assert run([dict(ga, vertical_speed=64, ground_speed=140, altitude=1650)])["modelo"] == "ninguno"   # tomando tierra (a la altura de la pista)
assert run([dict(ga, vertical_speed=1800, ground_speed=110, altitude=1700)])["modelo"] == "ninguno"   # lento y a la altura de la pista: no
# ya marcado: sigue aunque nivele, baje o esté lejos, y manda sobre un despegue más cercano; al aterrizar se olvida
r = run([dict(ga, vertical_speed=-300, distance=11.5), despega], ga=["ga1"])
assert r["info"]["fase"] == "frustrada" and r["info"]["vuelo"] == "VY1003" and r["ga"] == ["ga1"], r
assert run([dict(ga, on_ground=1, ground_speed=20)], ga=["ga1"])["ga"] == []
r = run([dict(ga, on_ground=1, altitude=0, ground_speed=120)], ga=["ga1"])   # tomando tierra tras el go-around: sigue (En tierra)
assert r["ga"] == ["ga1"] and r["info"]["fase"] == "aterrizaje" and r["info"]["ft"] == 0, r
r = run([dict(ga, vertical_speed=-700, heading=324)], ga=["ga1"])   # alineado con la 32L y bajando: Aproximando
assert r["info"]["pista"] == "32L" and r["info"]["vs"] == -700, r
assert run([despega], ga=["ga1"])["ga"] == []   # ni en el área ni seguido en FR24: se olvida (falsos de despegue que se quedaban, 09-11)
# 36R: solo si no hay nada mejor, y marcado como secundario
r36 = dict(despega, callsign="R36", flight_number="IB36", distance=6, **pos(40.545, -3.5593, 1))
r = run([r36])
assert r["info"]["vuelo"] == "IB36" and r["info"]["secundario"] is True and r["info"]["pista"] == "36R", r
r = run([r36, dict(despega, distance=9)])
assert r["info"]["vuelo"] == "VY1003" and r["info"]["secundario"] is False, r   # el de la 36L manda aunque esté más lejos
assert run([despega])["info"]["secundario"] is False
# configuración sur (12-11, BEL2UE y AEA57SF): la 14R es principal y la 14L secundaria, igual que 36L/36R
s14L = dict(despega, callsign="S14L", flight_number="UX14", altitude=2600, distance=8.4, **pos(40.468, -3.53, 140))
s14R = dict(despega, callsign="S14R", flight_number="SN14", altitude=2975, distance=7.0, **pos(40.459, -3.55, 143))
r = run([s14L]); assert r["info"]["pista"] == "14L" and r["info"]["secundario"] is True, r
r = run([s14R]); assert r["info"]["pista"] == "14R" and r["info"]["secundario"] is False, r
r = run([dict(s14R, distance=9), s14L]); assert r["info"]["vuelo"] == "SN14" and r["info"]["secundario"] is False, r   # la 14R manda aunque esté más lejos
r = run([dict(carrera, **pos(40.475, -3.567, 144))]); assert r["info"]["pista"] == "14R" and r["info"]["fase"] == "despegue" and r["info"]["secundario"] is False, r   # en carrera
# go-around con viento de cara (VLG30VT): 120 kt pero ya a 3200 ft subiendo
assert run([dict(ga, ground_speed=120, altitude=3200)])["info"]["fase"] == "frustrada"
assert run([dict(ga, ground_speed=120, altitude=1700)])["modelo"] == "ninguno"   # tocando tierra con un bote: no
# salidas de Barajas cerca de casa, por cualquier pista (AR1133): grande hasta 8 km, el resto hasta 5
gira = dict(despega, callsign="ARG1133", flight_number="AR1133", aircraft_code="A332", aircraft_model="Airbus A330-202", altitude=8000, vertical_speed=1500, **pos(40.53, -3.55, 290))
assert run([dict(gira, distance=7.5)])["info"]["vuelo"] == "AR1133"
assert run([dict(gira, distance=8.5)])["modelo"] == "ninguno"
assert run([dict(gira, aircraft_code="A320", distance=7.5)])["modelo"] == "ninguno"
assert run([dict(gira, aircraft_code="A320", distance=4.5)])["info"]["vuelo"] == "AR1133"
assert run([dict(gira, distance=4.5, vertical_speed=-500)])["modelo"] == "ninguno"   # bajando: no es una salida
# registro de llegadas que suben
assert run([dict(ga, vertical_speed=64, ground_speed=140)])["subiendo"] == ["AFR1 64fpm 140kt 4500ft 9km"], run([dict(ga, vertical_speed=64, ground_speed=140)])["subiendo"]
# VLG30VT (26-10, datos reales de FR24): cruza Barajas a 5700 ft nivelado, rumbo 322 -> go-around; se queda marcado en la vuelta
vy = dict(callsign="VLG30VT", id="424b6188", flight_number="VY1006", aircraft_code="A320", aircraft_model="Airbus A320-232", airline_short="Vueling",
          airport_origin_code_iata="BCN", airport_destination_code_iata="MAD", on_ground=0, vertical_speed=0, ground_speed=231)
assert run([dict(vy, altitude=5700, distance=6.9, **pos(40.4832, -3.5463, 322))])["info"]["fase"] == "frustrada"
assert run([dict(vy, altitude=5700, distance=9.8, **pos(40.5661, -3.6596, 265))], ga=["424b6188"])["info"]["fase"] == "frustrada"   # dando la vuelta
assert run([dict(vy, altitude=1625, distance=6.1, ground_speed=134, **pos(40.4675, -3.5584, 321))])["modelo"] == "ninguno"   # aterrizaje normal: no
assert run([dict(vy, altitude=5700, distance=11.5, **pos(40.4401, -3.5026, 322))])["modelo"] == "ninguno"   # aún fuera del recinto
assert run([dict(vy, altitude=5700, vertical_speed=-900, distance=6.9, **pos(40.4832, -3.5463, 322))])["modelo"] == "ninguno"   # bajando: aproximación
assert run([dict(carrera, callsign="FAUNA1", aircraft_code="GRND", aircraft_model="Airport Ground Vehicle", **pos(40.505, -3.5747, 2))])["modelo"] == "ninguno"
b7 = dict(carrera, callsign="B7", aircraft_code="", aircraft_model="", airline_short="", airport_destination_code_iata="", ground_speed=46)
assert run([dict(b7, **pos(40.505, -3.5747, 2))])["modelo"] == "ninguno"   # vehículo sin clasificar (10-11)
assert run([dict(b7, airport_destination_code_iata="SCQ", **pos(40.505, -3.5747, 2))])["modelo"] != "ninguno"   # sin modelo pero con destino: avión
# AR1133, 30-10: FR24 quita on_ground rodando a 126 kt con 1800 ft y vs 0 -> sigue en pista; al subir, en vuelo
i = run([dict(carrera, on_ground=0, ground_speed=126, altitude=1800, vertical_speed=0)])["info"]
assert i["fase"] == "despegue" and i["ft"] == 0 and i["m"] == 0, i
i = run([dict(carrera, on_ground=0, ground_speed=181, altitude=1850, vertical_speed=1472)])["info"]
assert i["fase"] == "vuelo" and i["ft"] == 1850, i
# FR2064, 01-11: frustra, sale del área (desaparece de flights) y vuelve a aterrizar: sigue siendo go-around hasta frenar
ga_fr = dict(llega, id="ga1", callsign="RYR2064", flight_number="FR2064", aircraft_code="B38M", on_ground=0, altitude=3000, vertical_speed=1500, ground_speed=180, distance=7.0, **pos(40.47, -3.561, 324))
assert run([ga_fr])["ga"] == ["ga1"]
assert run([crucero], ga=["ga1"])["ga"] == []   # fuera del área y sin seguir: se olvida (seguido: ver run2 más abajo)
vuelve = dict(ga_fr, altitude=3000, vertical_speed=-700, ground_speed=150, distance=9.0)
r = run([vuelve], ga=["ga1"]); assert r["info"]["vuelo"] == "FR2064" and r["info"]["fase"] == "frustrada", r
r = run([dict(vuelve, on_ground=1, altitude=0, vertical_speed=0, ground_speed=120)], ga=["ga1"]); assert r["info"]["fase"] == "aterrizaje" and r["info"]["ft"] == 0, r
assert run([dict(vuelve, on_ground=1, altitude=0, ground_speed=20)], ga=["ga1"])["ga"] == []   # ya frenado: se olvida
# seguido fuera del área (rastreados de FR24): la tarjeta se queda con él aunque esté lejos; los seguidos que no son go-around no cuentan
def run2(flights, seguidos, ga=()):
    t = env.from_string("{% from 'aviones.jinja' import avion_cercano %}{{ avion_cercano(fl, ga_prev=ga, seguidos=sg) }}")
    return json.loads(t.render(fl=flights, sg=seguidos, ga=list(ga)))
lejos = dict(ga_fr, altitude=5700, vertical_speed=0, distance=25.0)
r = run2([despega], [lejos], ga=["ga1"]); assert r["info"]["vuelo"] == "FR2064" and r["info"]["fase"] == "frustrada" and r["ga"] == ["ga1"], r
assert run2([despega], [lejos])["info"]["vuelo"] == "VY1003"
r = run2([despega], [dict(lejos, airport_destination_code_iata="VLC")], ga=["ga1"])   # desviado: se olvida
assert r["info"]["vuelo"] == "VY1003" and r["ga"] == [], r
# desvío tras el go-around (IB1334 → VLC, 18-11): foto fija 5 min con destino y motivo; luego se olvida
def run4(flights, seguidos, ga=(), prev=None, ahora=None, mp=None):
    t = env.from_string("{% from 'aviones.jinja' import avion_cercano %}{{ avion_cercano(fl, ga_prev=ga, seguidos=sg, desvio_prev=dp, ahora=ah, motivo_prev=mp) }}")
    return json.loads(t.render(fl=flights, sg=seguidos, ga=list(ga), dp=prev, ah=ahora, mp=mp))
vlc = dict(lejos, airport_destination_code_iata="VLC", airport_destination_city="Valencia")
r = run4([despega], [vlc], ga=["ga1"], ahora=1000, mp=dict(id="ga1", texto="Viento de cola"))
d = r["desvio"]; assert (d["id"], d["a"], d["destino"], d["vuelo"], d["t"], d["motivo"]) == ("ga1", "VLC", "Valencia", "FR2064", 1000, "Viento de cola"), d
assert r["ga"] == [] and r["info"]["vuelo"] == "VY1003", r
assert run4([despega], [], prev=d, ahora=1200)["desvio"] == d          # a los 200 s sigue
assert run4([despega], [], prev=d, ahora=1400)["desvio"] is None       # a los 400 s se va
assert run4([despega], [vlc], ahora=1000)["desvio"] is None            # sin go-around previo no es desvío
# IB1334 real (18-11): FR24 seguía con destino MAD; a 288 km, rumbo 114 sobre Requena, bajando -> desviado a Valencia
ib = dict(lejos, id="ib", flight_number="IB1334", callsign="ANE60XM", latitude=39.3957, longitude=-0.5573, heading=114, altitude=7525, vertical_speed=-2496, distance=288.2)
r = run4([despega], [ib], ga=["ib"], ahora=1000); assert r["ga"] == [] and (r["desvio"]["a"], r["desvio"]["destino"]) == ("VLC", "Valencia"), r["desvio"]
r = run4([despega], [dict(ib, latitude=39.95, longitude=-2.05, distance=120)], ga=["ib"], ahora=1000); assert r["desvio"]["a"] == "VLC", r["desvio"]   # a 120 km, camino de Valencia
r = run4([despega], [dict(lejos, distance=60)], ga=["ga1"], ahora=1000); assert r["ga"] == ["ga1"] and r["desvio"] is None, r   # en espera a 60 km: sigue
r = run2([dict(lejos, distance=6.0)], [lejos], ga=["ga1"]); assert r["info"]["km"] == 6.0, r   # en el área y seguido: sin duplicar
# go-around alineado con la 32R a ~20 km del centro de la pista (final larga): ya es «Aproximando»; un despegue ahí no tiene pista
c32 = (40.4825, -3.5452)   # centro de la 32R; se aleja 20 km hacia el SE (rumbo 144)
lejos32 = dict(ga_fr, latitude=c32[0] - 20 / 111.13 * 0.809, longitude=c32[1] + 20 / 84.65 * 0.588, heading=324, vertical_speed=-700, altitude=6000, distance=24)
r = run([lejos32], ga=["ga1"]); assert r["info"]["pista"] == "32R", r["info"]
assert run([dict(lejos32, vertical_speed=1500, airport_origin_code_iata="MAD", airport_destination_code_iata="BCN", heading=144, distance=4)])["info"]["pista"] == "", "despegue a 20 km no debe tener pista"
# motivo probable del go-around (01-11): pista ocupada, muy cerca del de delante, viento de cola; se conserva mientras siga marcado
def run3(flights, metar=None, ga=(), prev=None):
    t = env.from_string("{% from 'aviones.jinja' import avion_cercano %}{{ avion_cercano(fl, ga_prev=ga, motivo_prev=mp, metar=mt) }}")
    return json.loads(t.render(fl=flights, ga=list(ga), mp=prev, mt=metar))
def en_final(km, **kw):   # sobre la prolongación de la 32R, km desde su centro hacia el SE (eje real: 142,3°)
    return dict(llega, latitude=40.48245 - km / 111.13 * 0.791, longitude=-3.54523 + km / 84.65 * 0.612, heading=324, **kw)
ga32 = en_final(3, id="g", callsign="RYR2064", flight_number="FR2064", aircraft_code="B38M", on_ground=0, altitude=3000, vertical_speed=1500, ground_speed=160, distance=9)
calma = dict(rawOb="METAR LEMD 010830Z 35003KT CAVOK 08/04 Q1024 NOSIG", wdir=350, wspd=3, visib="6+")
r = run3([ga32], calma); assert r["info"]["motivo"] == "Desconocido" and r["motivo"] == {"id": "g", "texto": "Desconocido"}, r
ocupa = en_final(-1, id="o", flight_number="IB3121", on_ground=1, altitude=0, ground_speed=60, vertical_speed=0, distance=8)
assert run3([ga32, ocupa], calma)["info"]["motivo"] == "Pista ocupada: IB3121 aterrizando"
lado = dict(ocupa, longitude=ocupa["longitude"] - 0.004)   # en la calle de rodaje paralela (~300 m): no ocupa
assert run3([ga32, lado], calma)["info"]["motivo"] == "Desconocido"
ga_lejos = dict(ga32, **{k: en_final(7)[k] for k in ("latitude", "longitude")})
delante = en_final(4, id="d", flight_number="UX1023", on_ground=0, altitude=3500, vertical_speed=-700, distance=9)
assert run3([ga_lejos, delante], calma)["info"]["motivo"] == "Muy cerca del UX1023 (3,0 km)", run3([ga_lejos, delante], calma)["info"]
cola = dict(calma, rawOb="METAR LEMD 011600Z 14012G25KT 9999 FEW040 18/04 Q1012", wdir=144, wspd=12, wgst=25)
assert run3([ga32], cola)["info"]["motivo"] == "Viento de cola de 12 kt · Rachas de 25 kt"
niebla = dict(calma, rawOb="METAR LEMD 010600Z 00000KT 0300 R32R/0450 FG VV001 05/05 Q1023", visib=0.19)
assert run3([ga32], niebla)["info"]["motivo"] == "Niebla o poca visibilidad"
# se conserva: luego la pista ya está libre, pero sigue el motivo de cuando frustró; y se mantiene aunque salga del área
r = run3([ga32], calma, ga=["g"], prev={"id": "g", "texto": "Pista ocupada: IB3121 aterrizando"}); assert r["info"]["motivo"] == "Pista ocupada: IB3121 aterrizando", r
assert run3([despega], calma, ga=["g"], prev={"id": "g", "texto": "X"})["motivo"] is None   # ni en el área ni seguido: se olvida con él
assert run3([despega], calma)["info"]["motivo"] is None and run3([despega], calma)["motivo"] is None
assert run([dict(despega, aircraft_code="B77W")])["info"]["grande"] is True and run([despega])["info"]["grande"] is False   # para la Live Activity
# falsos go-arounds del 1 al 9-11 (revisión del 2026-11-09)
fase = lambda r: (r.get("info") or {}).get("fase")
sube = dict(llega, id="x", on_ground=0, ground_speed=140, vertical_speed=1300, altitude=1800, distance=5)
assert fase(run([dict(sube, airport_origin_code_iata="CLE", **pos(40.505, -3.5747, 2))])) != "frustrada"   # EQE906: despega de la 36L con el vuelo anterior
assert fase(run([dict(sube, airport_origin_code_iata="MAD", **pos(40.47, -3.561, 324))])) != "frustrada"   # IBS901P: MAD→MAD
assert fase(run([dict(sube, airport_origin_code_iata="CDG", vertical_speed=576, **pos(40.47, -3.561, 324))])) != "frustrada"   # GES121L: repunte en la final
assert fase(run([dict(sube, airport_origin_code_iata="MUC", altitude=9350, vertical_speed=2624, ground_speed=199, distance=11, **pos(40.40, -3.70, 290))])) != "frustrada"   # VL1800: lejos de la pista
assert fase(run([dict(sube, airport_origin_code_iata="LBG", time_real_arrival=1000, **pos(40.47, -3.561, 324))], ahora=5000)) != "frustrada"   # ya aterrizó: vuelo anterior
assert fase(run([dict(sube, airport_origin_code_iata="CDG", **pos(40.47, -3.561, 324))])) == "frustrada"   # el de verdad sigue saliendo
sobre = dict(sube, airport_origin_code_iata="CDG", vertical_speed=0, altitude=4500, ground_speed=200)
assert fase(run([dict(sobre, **pos(40.50, -3.56, 1))])) != "frustrada" and fase(run([dict(sobre, **pos(40.47, -3.55, 324))])) == "frustrada"
# «Aproximando»: alineado con una pista de llegada y ANTES del umbral, hasta 40 km (QY8340 se alineó a ~28 km de casa)
lejos35 = en_final(35, id="g", on_ground=0, altitude=5000, vertical_speed=0, ground_speed=220, distance=30)
assert run([lejos35], ga=["g"])["info"]["alineada"] == "32R"
assert run([en_final(-6, id="g", on_ground=0, altitude=4500, vertical_speed=2000, ground_speed=180, distance=8)], ga=["g"])["info"]["alineada"] == ""   # tras frustrar, se aleja
assert run([dict(lejos35, heading=144)], ga=["g"])["info"]["alineada"] == ""   # rumbo contrario
# vuelos seguidos (14-11): la lista de input_text y los rastreados de FR24; solo en directo, sin go-arounds
lv = lambda s: json.loads(env.from_string("{% from 'aviones.jinja' import lista_vuelos %}{{ lista_vuelos(s) }}").render(s=s))
assert lv("ib6830 2026-11-20 Papá y mamá;  UX1093/ec-mqp 2026-11-22 ;") == [dict(n="IB6830", m="", d="2026-11-20", q="Papá y mamá"), dict(n="UX1093", m="EC-MQP", d="2026-11-22", q="")]
assert lv("unknown") == [] and lv("") == []
def vs(seguidos, s, ga=()):
    return json.loads(env.from_string("{% from 'aviones.jinja' import vuelo_seguido %}{{ vuelo_seguido(sg, s, ga) }}").render(sg=seguidos, s=s, ga=list(ga)))
ib = dict(id="v1", flight_number="IB6830", callsign="IBE6830", tracked_type="live", aircraft_model="Airbus A350-941", aircraft_code="A359",
          airline_short="Iberia", airline_iata="IB", airport_origin_code_iata="MAD", airport_origin_city="Madrid", airport_destination_city="Bogota",
          time_real_departure=1000, time_scheduled_arrival=40000, time_estimated_arrival=40720, on_ground=0, altitude=39000, ground_speed=490)
r = vs([ib, dict(ib, id="v2", flight_number="UX1", callsign="AEA1")], "IB6830 2026-11-14 Papá")
assert len(r) == 1 and r[0]["quien"] == "Papá" and r[0]["modelo"] == "Airbus A350" and r[0]["retraso"] == 12 and r[0]["fase"] == "vuelo" and r[0]["ft"] == 39000 and r[0]["kmh"] == 907, r
assert r[0]["r_sale"] is None and vs([dict(ib, time_scheduled_departure=1300)], "IB6830 x")[0]["r_sale"] == -5, r   # salió 5 min antes
assert r[0]["sale"] == 1000 and r[0]["llega"] == 40720 and r[0]["fr24"].endswith("/IBE6830/v1"), r
assert len(vs([ib], "IB6830 2026-11-14 Papá; IB6830 2026-11-15")) == 1   # el mismo vuelo en dos fechas: una vez
assert vs([dict(ib, tracked_type="schedule")], "IB6830 2026-11-14") == []   # aún sin despegar en FR24: no sale
assert vs([ib], "IB6830 2026-11-14", ga=["v1"]) == []   # go-around: es de la tarjeta Avión
assert vs([dict(ib, has_landed=True)], "IBE6830 2026-11-14")[0]["fase"] == "aterrizado" and vs([dict(ib, time_real_arrival=1)], "IB6830 x")[0]["fase"] == "vuelo"   # por indicativo; time_real_arrival del tramo anterior no cuenta
# fase previa (15-11): AeroDataBox recortado, previsión por el tramo anterior del avión y la tarjeta
J = lambda src, **kw: json.loads(env.from_string("{% from 'aviones.jinja' import adb_tramo, prevision, vuelo_previo %}" + src).render(**kw))
adb = {"number": "UX 5054", "status": "Expected", "callSign": "AEA17LZ", "aircraft": {"reg": "EC-MXV", "model": "Airbus A320neo (sharklets)"},
       "airline": {"name": "Air Europa", "iata": "UX", "icao": "AEA"},
       "departure": {"airport": {"iata": "MAD", "municipalityName": "Madrid"}, "scheduledTime": {"utc": "2026-11-15 18:00Z"}, "terminal": "1", "gate": "B12"},
       "arrival": {"airport": {"iata": "LIS", "municipalityName": "Lisbon"}, "scheduledTime": {"utc": "2026-11-15 19:20Z"}}}
mio = J("{{ adb_tramo(f) }}", f=adb)
T = mio["sp"]
assert mio["modelo"] == "Airbus A320neo", mio
assert (mio["n"], mio["reg"], mio["puerta"], mio["de"], mio["destino"], mio["se"], mio["lp"] - T) == ("UX5054", "EC-MXV", "B12", "MAD", "Lisbon", 0, 4800), mio
antes = dict(mio, n="UX1234", estado="EnRoute", de="BCN", a="MAD", sp=T - 7200, lp=T - 2400, se=T - 4200, le=T - 600)   # salió y llega 30 min tarde
p = J("{{ prevision(c, m) }}", c=[antes, mio], m=mio)
assert (p["r"], p["motivo"], p["prev"]["n"]) == (25, "avion", "UX1234"), p
assert p["llega"] == T - 600, p   # llega a las T-10 min + 35 de rotación
assert J("{{ prevision(c, m) }}", c=[dict(antes, le=T - 3600), mio], m=mio)["r"] == 0   # llega con tiempo
assert J("{{ prevision(c, m) }}", c=[mio], m=dict(mio, se=T + 1200))["motivo"] == "aerolinea"
assert J("{{ prevision(c, m) }}", c=[dict(antes, se=0, le=0, estado="Expected", sp=T - 6000, lp=T - 1200)], m=mio)["r"] == 15   # sin estimadas: duración programada
d = {"UX5054 2026-11-15": dict(fl=mio, cadena=[antes, mio], anos=6.2, puerta_antes="B8")}
v = J("{{ vuelo_previo(d, s, [], a) }}", d=d, s="UX5054 2026-11-15 Ana", a=T - 3600)
assert len(v) == 1 and (v[0]["estado"], v[0]["r"], v[0]["quien"], v[0]["anos"], v[0]["puerta_antes"]) == ("retraso", 25, "Ana", 6.2, "B8"), v
assert v[0]["fr24"].endswith("/UX1234") and [t["de"] for t in v[0]["cadena"]] == ["BCN", "MAD"] and v[0]["cadena"][0]["est"] == "aire" and v[0]["cadena"][1]["mio"], v
vid = {"UX5054 2026-11-15": dict(fl=mio, cadena=[dict(antes, id="4295e739", cs="AEA1234"), mio])}
assert J("{{ vuelo_previo(d, s, [], a) }}", d=vid, s="UX5054 2026-11-15", a=T - 3600)[0]["fr24"] == "https://www.flightradar24.com/AEA1234/4295e739"
sin = {"UX5054 2026-11-15": dict(fl=dict(mio, reg=""), cadena=[dict(antes, estado="Arrived"), mio])}
assert J("{{ vuelo_previo(d, s, [], a) }}", d=sin, s="UX5054 2026-11-15", a=T - 3600)[0]["fr24"].endswith("/UX5054")   # sin matrícula ni avión en el aire
assert J("{{ vuelo_previo(d, s, [], a) }}", d=d, s="UX5054 2026-11-15", a=T - 13 * 3600) == []   # aún faltan más de 12 h
assert J("{{ vuelo_previo(d, s, ['UX5054'], a) }}", d=d, s="UX5054 2026-11-15", a=T) == []   # FR24 ya lo ve: tarjeta en directo
assert J("{{ vuelo_previo(d, s, [], a) }}", d={"UX5054 2026-11-15": dict(fl=dict(mio, estado="Departed"))}, s="UX5054 2026-11-15", a=T) == []
c = J("{{ vuelo_previo(d, s, [], a) }}", d={"UX5054 2026-11-15": dict(fl=dict(mio, estado="Canceled"))}, s="UX5054 2026-11-15", a=T)
assert c[0]["estado"] == "cancelado" and c[0]["fr24"].endswith("/EC-MXV") and c[0]["cadena"][0]["mio"], c
# a AeroDataBox le falta la vuelta del avión (15-11, EC-NUZ): tramo sin horas hasta mi origen, sin previsión por él
v = J("{{ vuelo_previo(d, s, [], a) }}", d={"UX5054 2026-11-15": dict(fl=mio, cadena=[dict(antes, a="MXP", destino="Milan")])}, s="UX5054/EC-MXV 2026-11-15", a=T - 3600)
assert v[0]["aviso"] == "Tu avión va a Milan y vuelve a Madrid" and v[0]["r"] == 0, v
assert [(t["de"], t["a"], t["est"]) for t in v[0]["cadena"]] == [("BCN", "MXP", "aire"), ("MXP", "MAD", "prog"), ("MAD", "LIS", "prog")], v
assert J("{{ vuelo_previo(d, s, [], a) }}", d=d, s="UX5054 2026-11-15", a=T - 3600)[0]["aviso"] == ""
_suelto = dict(antes, n="UX1", estado="Arrived", de="MAD", a="SVQ", sp=T - 30000, lp=T - 26000, se=0, le=0)   # sin la vuelta SVQ-BCN: no se pinta
assert [t["de"] for t in J("{{ vuelo_previo(d, s, [], a) }}", d={"UX5054 2026-11-15": dict(fl=mio, cadena=[_suelto, antes])}, s="UX5054 2026-11-15", a=T - 3600)[0]["cadena"]] == ["BCN", "MAD"]
# hora estimada de FR24 y causa probable (15-11)
J2 = lambda src, **kw: env.from_string("{% from 'aviones.jinja' import tiempo_metar, causa, prevision %}" + src).render(**kw)
p24 = J("{{ prevision(c, m) }}", c=[mio], m=dict(mio, se24=T + 1080))
assert (p24["r"], p24["fuente"], p24["motivo"]) == (18, "fr24", "aerolinea"), p24   # AeroDataBox «en hora», FR24 19:38
assert J("{{ prevision(c, m) }}", c=[antes, mio], m=dict(mio, se24=T + 600))["fuente"] == ""   # manda el avión (T+25)
for raw, k in [("LEMD 151430Z 22011KT 9000 SCT022 14/10 Q1019 NOSIG", ""), ("LEZL 151630Z 24012KT 6000 +TSRA BKN020CB 18/16 Q1009", "Tormenta"),
               ("LEMD 150630Z 00000KT 0300 FG VV001 05/05 Q1025", "Niebla"), ("LEBB 150630Z 18032G48KT 9999 FEW030 Q1000", "Viento fuerte"),
               ("LEMD 150630Z VRB02KT 1200 BR 05/05 Q1025 TEMPO 0200 FG", "Poca visibilidad"), ("LEMD 151430Z 22011KT 9999 Q1019 TEMPO TSRA", "")]:
    assert J2("{{ tiempo_metar(r) }}", r=raw) == k, (raw, J2("{{ tiempo_metar(r) }}", r=raw))
f_ = dict(mio, origen="Madrid", destino="Seville", reg="EC-NUZ")
pa = dict(motivo="avion", prev=dict(antes, origen="Barcelona"))
pn = dict(motivo="aerolinea", prev=None)
C = lambda p, ctx=None, ra="": J2("{{ causa(f, p, ctx, ra) }}", f=f_, p=p, ctx=ctx or {}, ra=ra)
assert C(pa, ra="EC-MQP") == "Cambio de avión (EC-MQP → EC-NUZ)"
assert C(pa) == "Tu avión llega tarde de Barcelona"
assert C(pn, dict(destino=dict(metar="LEZL 151630Z 24012KT 6000 +TSRA", media=40))) == "Tormenta en Seville"
assert C(pn, dict(origen=dict(media=10), destino=dict(media=31))) == "Probable regulación: llegadas a LIS +31 min"
assert C(pn, dict(origen=dict(media=25), destino=dict(media=3))) == "Probable regulación: salidas de MAD +25 min"
assert C(pn) == "Sin causa visible (aerolínea)"
v = J("{{ vuelo_previo(d, s, [], a) }}", d={"UX5054 2026-11-15": dict(fl=dict(mio, se24=T + 1080), cadena=[mio])}, s="UX5054 2026-11-15", a=T - 3600)[0]
assert (v["estado"], v["r"], v["fuente_prev"], v["causa"]) == ("retraso", 18, "fr24", "Sin causa visible (aerolínea)"), v
assert J("{{ vuelo_previo(d, s, [], a) }}", d={"UX5054 2026-11-15": dict(fl=mio, cadena=[dict(antes, origen="Barcelona"), mio])}, s="UX5054 2026-11-15", a=T - 3600)[0]["causa"] == "Tu avión llega tarde de Barcelona"
print(run([rodando, crucero, despega, llega])["frase"]); print("ok")

