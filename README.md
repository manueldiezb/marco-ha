# Marco familiar para Home Assistant

Un panel para un iPad colgado en la pared (o en la cocina): hora y tiempo, la agenda de la semana, lo próximo de cada calendario, cuentas atrás, la casa (clima, luces, persianas), tareas, fútbol, aviones que pasan por encima y algunas cosas más.

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
| Talentos | Sensores `sensor.talentos_*` de la app Talentos | `talentos` |
| Oración | `packages/oracion.yaml` + `liturgia.py` en `/config/marco/` | `oracion` |
| Aviones | Ver abajo | `aviones`, `aeropuerto` |

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
