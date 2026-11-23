# Marco familiar (Home Assistant)

Panel para un iPad, servido por Home Assistant desde `/config/www/marco/` (`/local/marco/dashboard.html`). Todo en español: código, comentarios y textos.

## Cómo está hecho

- **Un solo fichero**: `dashboard.html` (CSS + HTML + un `<script>` clásico, sin build ni dependencias). No partirlo en módulos.
- **`CONFIG`** al principio del `<script>`: todo lo que depende de la casa (entity_id, calendarios, equipos, gasolineras). Lo vacío no se enseña. Cualquier entidad nueva va ahí, nunca escrita a fuego en el código. Las del coche pasan siempre por `carId(dominio, clave)` (prefijo o `CONFIG.coche.entidades`); lo que no existe no se pinta.
- Login con usuario y contraseña de HA (su `login_flow`, como la app); el refresh token se guarda en el navegador. **Nunca** pongas tokens ni claves en ficheros de `www/` (los sirve `/local/` sin login).
- Acceso a HA: `ha(path, datos?)` es el único GET/POST a la API REST (tope de 20 s). `allStates()` comparte `/api/states` 2 s entre quienes lo piden. `historia()` y `serie()` para el historial, `calendario()` para los eventos, `svc(dominio, servicio, datos)` y `act()` para órdenes.
- Push: un WebSocket (`connectPush`) se suscribe a `homeWatch` y repinta Hogar al cambiar algo. Además, `refresh()` cada 5 min; cada bloque falla por su cuenta (lo que falla sale abajo a la derecha en `#status`).
- Páginas: Hoy (portada), Casa, Coche, Oración, Compra, Tareas, Ajustes (`nav(p)`). La portada es una rejilla de 3 filas; los carriles que turnan tarjetas usan `hueco()` + `turno()`; `hoyVisible()` para no animar lo que no se ve.
- Escala: el escenario mide 1920 de ancho y se escala (`fit()`); en vertical y en iPhone cambia la maqueta (`body.p`, `body.m`).
- Modo oscuro (`html.dark`), modo noche (Dormir) y ajustes por dispositivo en `localStorage` (`AJ`).

## Compra (Mercadona)

`mercadona.py` (en HA, vía `shell_command.marco_mercadona`, órdenes en base64) solo lee y cambia el carrito: a propósito no hay nada para pedir ni pagar; no añadirlo. Las lecturas y cambios van en fila (`cmp.chain`) y los toques seguidos de un producto se juntan; mientras hay cambios pendientes (`cmp.ops`) no se aplican lecturas. Tickets de Gmail: solo el remitente de Mercadona, solo lectura, nada del correo a disco.

## Lado de Home Assistant

- `packages/*.yaml` (con `packages: !include_dir_named packages`), `templates/*.yaml`, `*.jinja` en `/config/custom_templates/`, scripts Python en `/config/marco/`.
- Plantillas con disparadores: en `actions` **no existe `this`**; el estado anterior se lee por nombre (`state_attr('sensor.avion_cercano', 'ga')`). Al recargar plantillas el sensor nace un instante sin atributos: comprobar `'ga' in trigger.to_state.attributes` antes de usarlo.
- La macro de una plantilla con disparadores se calcula una vez (`actions: variables: r`) y estado y atributos salen de `r`.

## Pruebas

`./test.sh` corre todo: sintaxis del `<script>`, los `*_test.js` (node, extraen funciones del HTML) y los `test_*.py` (jinja2; `test_mercadona.py` con `python3 -I`). Ejecutarlo tras cada cambio. Si añades lógica con ramas (fechas, parseo), deja una prueba pequeña al lado.

## iPad

- Pensado para un iPad viejo con iPadOS 16-17: nada de APIs recientes sin comprobar (`URL.parse` no existe; Wake Lock en web app no funciona hasta 18.4, por eso el vídeo invisible).
- HA sirve `/local/` con caché de 31 días: `checkUpdate()` recarga si cambia la página; si cambias `sw.js`, sube su `?v=`.
