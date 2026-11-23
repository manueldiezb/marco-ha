# Marco familiar para Home Assistant

Un panel para un iPad colgado en la pared (o en la cocina): hora y tiempo, la agenda de la semana, lo próximo de cada calendario, cuentas atrás, la casa (clima, luces, persianas), el coche, el carrito de Mercadona, tareas, fútbol, aviones que pasan por encima y algunas cosas más.

Es **una sola página** (`dashboard.html`) que sirve tu propio Home Assistant desde `/local/`. Se entra con tu usuario y contraseña de HA, como en la app. No hay servidor aparte ni tokens guardados en ficheros.

## Instalación

1. Copia la carpeta a tu HA, en `/config/www/marco/` (con Samba, File editor, Studio Code Server, o `scp`):
   `dashboard.html`, `sw.js`, `icono-*.png`, `fondos/` y `logos/`.
2. Abre `dashboard.html` y rellena el bloque **`CONFIG`** del principio del `<script>` (está todo comentado). Lo que dejes vacío no sale.
3. En el iPad, abre `https://<tu-ha>/local/marco/dashboard.html`, entra con tu usuario de HA y, en Safari, *Compartir → Añadir a pantalla de inicio*. Así se abre a pantalla completa y la pantalla no se apaga.

HA guarda `/local/` en caché 31 días, pero la página mira cada 5 min si ha cambiado y se recarga sola.

## Qué necesita cada parte

| Parte | Qué hace falta en HA | En `CONFIG` |
|---|---|---|
| Tiempo | Nada (Open-Meteo, con la posición de tu HA) | `ciudad` |
| Agenda, Lo próximo | Integración de calendario (Google, CalDAV, local…) | `calendarios`, `cumpleanos`, `trabajo`, `fotos` |
| Cuentas atrás | Un evento con «Cuenta atrás» en la descripción (opcional: un color y efectos, p. ej. «Cuenta atrás · rojo · nieve») | — |
| Casa: clima | Un `climate.*` (y sensores de temperatura/humedad si quieres gráfico) | `clima` |
| Casa: luces | Las `light.*` (sin grupos); estancias opcionales | `estancias`, `lucesIgnorar`, `lucesEncender`, `buenasNoches` |
| Casa: persianas | `cover.*` | `persianas`, `persianasTodas`, `persianasMedias` |
| Tareas | Una lista `todo.*` | `tareas` |
| Fútbol | Nada (ESPN). Pon el id de ESPN de tu equipo | `futbol` |
| Gasolina | Nada (Geoportal del Ministerio, solo España) | `provincia`, `gasolineras` |
| Compra (Mercadona) | `packages/mercadona.yaml` + `mercadona.py` en `/config/marco/` | `mercadona` |
| Coche | La integración de tu coche | `coche` |
| Talentos | Sensores `sensor.talentos_*` de la app Talentos | `talentos` |
| Oración | `packages/oracion.yaml` + `liturgia.py` en `/config/marco/` | `oracion` |
| Aviones | Ver abajo | `aviones`, `aeropuerto` |

### Compra (Mercadona)

El carrito de la app de Mercadona, compartido por toda la casa: se ve, se busca en el catálogo y se suben o bajan cantidades. **No pide ni paga nada**: solo toca el carrito. Usa la API interna (no oficial) de tienda.mercadona.es, así que puede romperse si Mercadona la cambia.

1. `mercadona.py` en `/config/marco/` (solo Python estándar) y `packages/mercadona.yaml` en tus packages. Reinicia HA (un `shell_command` nuevo no se recarga solo).
2. `mercadona: true` en `CONFIG`.
3. Conectar: en el ordenador, entra en tienda.mercadona.es con tu cuenta, abre la consola del navegador y ejecuta `copy(localStorage.getItem('MO-user'))`. Pega eso en **Ajustes → Mercadona** del Marco. La sesión queda en `/config/.mercadona` (fuera de `www/`) y vale para todos los dispositivos.

«Lo de siempre» sale de tus pedidos online. Opcional: también de los tickets de tienda que llegan al correo, si creas `/config/.mercadona-gmail` con `{"user": "...", "password": "<contraseña de aplicación>"}` (modo 600). Solo lee los correos de `ticket_digital@mail.mercadona.com`, en modo lectura, y no guarda ningún correo: lee el PDF en memoria y se queda con fecha, producto y cantidad.

### Coche

La página Coche (estado, cierre, puertas y ventanillas, gasolina y su previsión, dónde está y dónde aparcó, salud) y el coche en la tarjeta de gasolina. Se hizo con la integración **kia_uvo** (Hyundai/Kia Bluelink), pero vale para cualquiera: cada dato tiene una clave y tú dices qué entidad es.

```js
coche: {
  nombre: 'Mi coche',
  prefijo: 'mi_coche',          // con kia_uvo y similares: <dominio>.<prefijo>_<clave>
  entidades: {                  // lo que no siga ese patrón, una a una
    'sensor.fuel_level': 'sensor.mi_coche_combustible',
    'device_tracker.location': 'device_tracker.mi_coche',
  },
  deposito: 50,                 // litros, para «llenar ≈ X €»
  modelo3d: '',                 // id de un modelo de Sketchfab (opcional)
},
```

Lo que no exista en HA no sale (sin cierre no hay botón de abrir/cerrar, sin ubicación no hay mapa…). Claves que usa:

- `sensor`: `fuel_level` (%), `fuel_driving_range` o `autonomia_total` (km), `odometer`, `car_battery_level` (12 V, %), `last_updated_at`, `geocoded_location`, `location_last_updated`, `vehicle_identification_number`
- `lock`: `door_lock` · `device_tracker`: `location`
- `binary_sensor`: `engine`, `accesorios`, `front_left_door`, `front_right_door`, `back_left_door`, `back_right_door`, `*_window`, `hood`, `trunk`, `tire_pressure_all`, `tire_pressure_front_left`…, `brake_fluid_warning`, `washer_fluid_warning`, `smart_key_battery_warning`, `air_conditioner`, `defrost`, `back_window_heater`, `luces_de_emergencia`, fallos de luces (`headlamp_left_low_fault`…)
- `button`: `force_refresh`, `close_all_windows`, `vent_all_windows`, `start_valet_mode`, `stop_valet_mode`

El mapa de las gasolineras con minutos en coche usa la integración **Waze Travel Time** (si no está, sale sin minutos). Los mapas son del IGN (solo España).

### Aviones (lo más trabajoso)

Está hecho para una casa cerca de **Barajas**: las pistas, la altura de casa y los umbrales están en `aviones.jinja`. Si vives cerca de otro aeropuerto hay que adaptarlo (es buen trabajo para Claude: los tests de `test_aviones.py` dicen qué se espera).

- Integración **Flightradar24** de HA (da `sensor.flightradar24_current_in_area`).
- `aviones.jinja` en `/config/custom_templates/`, `templates/aviones.yaml` en tus plantillas y `packages/vuelos.yaml` en tus packages.
- «Vuelos que sigo» (en Ajustes) usa AeroDataBox (RapidAPI, plan gratuito): la clave en `secrets.yaml` como `aerodatabox_key`, y `fr24_matricula.py` en `/config/marco/`.
- `avion-card.js` es la misma tarjeta para los dashboards normales de HA (opcional).

Para usar `packages/`, en `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

### Persianas que no dicen su posición

`templates/persianas_estado.yaml` + `persianas.jinja` son un ejemplo de persianas Tuya con interruptor (no informan de la posición): crean un `cover.estado_persiana_*` que la calcula por tiempo. Solo si tienes algo parecido; hay que cambiar los nombres de las persianas.

## Fondos

`fondos/` son fotos de Madrid (Wikimedia Commons, los créditos salen en la esquina). Puedes poner las tuyas con los mismos nombres: `dia`, `dia-nubes`, `dia-invierno`, `nublado`, `niebla`, `lluvia`, `nieve`, `amanecer`, `atardecer`, `atardecer-nubes`, `noche`, `noche-nubes`, `noche-navidad` (y cambiar los créditos en `PHOTOS`).

## Pruebas

```sh
./test.sh     # necesita node y python3 con jinja2
```

## Adaptarlo con Claude

`CLAUDE.md` le explica a Claude Code cómo está hecho esto. Ábrelo en la carpeta y pídele lo que quieras («añade una tarjeta con el consumo de la casa», «adapta los aviones a El Prat»…).
