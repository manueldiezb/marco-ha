// Tarjeta «Avión» del Marco para los dashboards de HA (type: custom:avion-card). Misma pinta que #plane en dashboard.html,
// a escala de móvil. Lee sensor.avion_cercano (atributo info, ver aviones.jinja). Sin tokens: el estado llega por hass.
const PHASE = { despegue: ['Despegando', '#E8743B'], vuelo: ['En vuelo', '#29A3D6'], frustrada: ['Go-around', '#D9483B'], aterrizaje: ['Aterrizando', '#8E5BC8'], desviado: ['Desviado', '#D9483B'] };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => `&#${c.charCodeAt(0)};`);
const n = x => (+x || 0).toLocaleString('es-ES', { useGrouping: 'always' });
const stat = (l, v, u) => `<div><div class="sl">${l}</div><div class="sv">${esc(v)}</div><div class="su">${esc(u) || '&nbsp;'}</div></div>`;
const dur = m => m < 60 ? `${m} min` : `${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60} min` : ''}`;

if (!document.querySelector('link[href*="family=Geist"]'))   // las @font-face no funcionan dentro del shadow DOM
  document.head.insertAdjacentHTML('beforeend', '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&display=swap">');

const CSS = `
:host { display: block; }
.c { position: relative; overflow: hidden; border-radius: 22px; background: #FFFDF9; color: #221D18; padding: 14px 18px 12px;
  font-family: Geist, -apple-system, system-ui, sans-serif; transition: background-color .6s ease, color .6s ease; }
.c::before { content: ''; position: absolute; inset: 0; background: url(/local/marco/fondos/avion.webp) right center / cover no-repeat; opacity: .22; filter: sepia(.6); pointer-events: none; }
.c > * { position: relative; }
.th { display: flex; align-items: center; font-size: 19px; gap: 8px; }
.th > span { font-size: 12px; font-weight: 600; letter-spacing: 2px; color: #29A3D6; }
.ph { margin-left: auto; font-size: 12px; font-weight: 700; padding: 2px 9px; border-radius: 99px; white-space: nowrap; }
.ph + .ph { margin-left: 4px; }
.pb { display: flex; align-items: center; gap: 12px; margin: 8px 0 10px; }
.px { flex: 1; min-width: 0; }
.pm { font-size: 22px; line-height: 26px; font-weight: 700; letter-spacing: -.3px; }
.pd { font-size: 16px; line-height: 21px; font-weight: 600; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pd small { font-size: 14px; color: #6E6358; }
.pd a { color: inherit; text-decoration: none; }
.pmo { font-size: 13px; line-height: 17px; font-weight: 600; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; opacity: .9; }
.pl { width: 30%; max-width: 120px; max-height: 48px; object-fit: contain; flex: none; }
.pl.t { width: auto; max-width: 34%; font-size: 14px; font-weight: 700; color: #6E6358; text-align: right; }
.pst { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: 8px; }
.sl { font-size: 10px; line-height: 13px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #A6998A; }
.sv { font-size: 15px; line-height: 19px; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
.su { font-size: 12px; line-height: 15px; font-weight: 600; color: #6E6358; font-variant-numeric: tabular-nums; white-space: nowrap; }
.p0 { font-size: 16px; font-weight: 600; color: #6E6358; margin-top: 6px; }
.p0 small { display: block; font-size: 13px; font-weight: 500; color: #A6998A; margin-top: 3px; }
.c + .c { margin-top: 10px; }
.fbar.mio { background: repeating-linear-gradient(90deg, #29A3D6 0 5px, transparent 5px 9px); }
.fr b.mio { color: #29A3D6; }
.sv s { font-size: .75em; color: #A6998A; }
.sv.cambio { color: #C98A0E; }
.c > .fsrc { position: absolute; right: 14px; bottom: 4px; font-size: 10px; color: #A6998A; }
.fcap { margin: -4px 0 10px; font-size: 13px; line-height: 17px; font-weight: 600; color: #6E6358; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.th > span { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fr { display: flex; align-items: center; gap: 10px; margin: 2px 0 10px; font-size: 15px; font-weight: 700; }
.fr b { max-width: 32%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fbar { flex: 1; position: relative; height: 3px; border-radius: 2px; background: #E7DED3; }
.fbar i { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 2px; background: #29A3D6; }
.fbar span { position: absolute; top: 50%; transform: translate(-50%, -52%); font-size: 18px; line-height: 1; color: #29A3D6; }
.ga { background: #C9483B; color: #fff; }
.ga::before { background-image: url(/local/marco/fondos/avion-ga.webp); filter: invert(1); mix-blend-mode: screen; opacity: .4; }
.ga .th > span, .ga .ph { color: #fff !important; background: rgba(255,255,255,.22) !important; }
.ga .th > span { background: none !important; }
.ga .pd small, .ga .su { color: rgba(255,255,255,.8); }
.ga .sl { color: rgba(255,255,255,.7); }
.ga .pl { background: #fff; border-radius: 10px; padding: 4px 8px; width: 26%; }
.ga .pl.t { background: none; color: #fff; }
`;

class AvionCard extends HTMLElement {
  setConfig(c) { this.entity = c.entity || 'sensor.avion_cercano'; }
  set hass(h) {
    const s = h.states[this.entity], p = this.extra && h.states[this.extra];
    if (s === this._s && p === this._p) return;   // solo repinta si cambió el sensor
    this._s = s; this._p = p;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    this.shadowRoot.innerHTML = `<style>${CSS}</style><ha-card style="background:none;border:none;box-shadow:none">${this.render(s, p)}</ha-card>`;
    this.shadowRoot.querySelectorAll('img.pl').forEach(img => img.onerror = () => {
      if (img.dataset.next) { img.src = img.dataset.next; img.dataset.next = ''; }
      else img.outerHTML = `<div class="pl t">${esc(img.alt)}</div>`;
    });
  }
  render(s) {
    // go-around desviado (atributo desvio, 5 min): foto fija en rojo, como el Marco, salvo que haya otro go-around en curso
    const dv = s?.attributes.desvio, i = s?.attributes.info?.fase !== 'frustrada' && dv ? { ...dv, fase: 'desviado' } : s?.attributes.info;
    if (!i) {
      const near = (s?.attributes.frase || '').match(/El más próximo es un (.*)\.$/);
      return `<div class="c"><div class="th">✈️<span>AVIÓN</span></div>
        <div class="p0">${s ? 'Ningún avión sonando' : 'Sin datos de Flightradar'}${near ? `<small>El más próximo: ${esc(near[1])}</small>` : ''}</div></div>`;
    }
    const [ph, c] = PHASE[i.fase] || PHASE.vuelo, ga = i.fase === 'frustrada', dsv = i.fase === 'desviado';
    const r = i.retraso, late = r >= 15, dc = late ? '#C98A0E' : '#3BA55C';
    const urls = [i.iata && `https://pics.avs.io/400/160/${encodeURIComponent(i.iata)}.png`,
      i.icao && `https://www.flightradar24.com/static/images/data/operators/${encodeURIComponent(i.icao)}_logo0.png`].filter(Boolean);
    const logo = urls.length ? `<img class="pl" alt="${esc(i.aerolinea)}" src="${urls[0]}" data-next="${urls[1] || ''}">` : `<div class="pl t">${esc(i.aerolinea)}</div>`;
    const vuelo = i.vuelo ? ` <small>${i.fr24 ? `<a href="${esc(i.fr24)}" target="_blank" rel="noopener">(${esc(i.vuelo)})</a>` : `(${esc(i.vuelo)})`}</small>` : '';
    return `<div class="c${ga || dsv ? ' ga' : ''}"><div class="th">✈️<span>AVIÓN</span>
        <div class="ph" style="background:${c}24;color:${c}">${ph}</div>${r == null ? '' : `<div class="ph" style="background:${dc}24;color:${dc}">${late ? `Retrasado (${dur(r)})` : 'En hora'}</div>`}</div>
      <div class="pb"><div class="px"><div class="pm">${esc(i.modelo)}</div>
        <div class="pd">${ga ? (i.origen ? `← ${esc(i.origen)}` : '') : i.destino ? `→ ${esc(i.destino)}` : ''}${vuelo}</div>${i.motivo ? `<div class="pmo">${i.motivo === 'Desconocido' ? 'Motivo desconocido' : 'Probable: ' + esc(i.motivo)}</div>` : ''}</div>${logo}</div>
      ${dsv ? '</div>' : `<div class="pst">${stat('Altitud', i.ft ? n(i.ft) + ' ft' : 'En pista', '')}
        ${stat('Velocidad', n(i.kmh) + ' km/h', '')}
        ${i.pista ? stat(ga ? 'Iba a pista' : 'Pista', i.pista, 'Barajas') : ''}
        ${stat('Desde casa', String(i.km).replace('.', ',') + ' km', (i.km / 1.609).toFixed(1).replace('.', ',') + ' mi')}</div></div>`}`;
  }
  getCardSize() { return 3; }
  getGridOptions() { return { columns: 12, min_columns: 6 }; }
}
customElements.define('avion-card', AvionCard);
window.customCards = [...(window.customCards || []), { type: 'avion-card', name: 'Avión (Marco)', description: 'El avión que se oye desde casa' }];

// Vuelo seguido (type: custom:vuelo-seguido-card): los de sensor.vuelo_seguido (lista en Ajustes del Marco) que FR24 ve en directo,
// uno debajo de otro. Misma pinta que las .fol del Marco. Sin ninguno no ocupa sitio (y en el dashboard lleva visibility).
const FPHASE = { rodando: ['Rodando', '#E8743B'], vuelo: ['En vuelo', '#29A3D6'], aterrizado: ['Ha aterrizado', '#3BA55C'] };
// minutos sobre la hora programada: verde si es en hora o antes, rojo si tarde; sin dato, el aeropuerto
const fstat = (l, v, m, ap) => `<div><div class="sl">${l}</div><div class="sv">${esc(v)}</div>${m == null ? `<div class="su">${esc(ap) || '&nbsp;'}</div>`
  : `<div class="su" style="color:${m > 0 ? '#D9483B' : '#3BA55C'}">${m > 0 ? `${dur(m)} tarde` : m < 0 ? `${dur(-m)} antes` : 'En hora'}</div>`}</div>`;
const hm = t => t ? new Date(t * 1e3).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }) : '–';
// Antes de salir (sensor.vuelo_previo): como previoHTML del Marco
const PEST = { prog: ['Programado', '#8A7E72'], hora: ['En hora', '#3BA55C'], retraso: ['Retrasado', '#C98A0E'], cancelado: ['Cancelado', '#D9483B'], embarque: ['Embarcando', '#29A3D6'] };
function previo(i, logo) {
  const now = Date.now() / 1e3, emb = i.previsto - 2400, cad = i.cadena || [], prev = cad.length > 1 ? cad[cad.length - 2] : null;
  let [et, ec] = PEST[i.estado] || PEST.prog;
  if (!['cancelado', 'retraso'].includes(i.estado) && now >= emb) [et, ec] = PEST.embarque;
  const seg = t => {
    const c = t.r >= 15 ? '#D9483B' : '#3BA55C', p = t.est === 'fin' ? 1 : t.est === 'aire' && t.llega > t.sale ? Math.min(1, Math.max(0, (now - t.sale) / (t.llega - t.sale))) : 0;
    return t.mio ? '<div class="fbar mio"></div>' : `<div class="fbar"><i style="width:${p * 100}%;background:${c}"></i>${t.est === 'aire' ? `<span style="left:${Math.min(p, .85) * 100}%;color:${c}">✈</span>` : ''}</div>`;
  };
  const tu = i.causa ? esc(i.causa) : i.aviso ? esc(i.aviso) : !prev ? '' : prev.est === 'fin' ? `Tu avión ya está en ${esc(prev.a)}` : `Tu avión llega a ${esc(prev.a)} a las ${hm(i.avion_llega)}`
    + (prev.est === 'prog' && !cad.some(t => t.est === 'aire') ? ` · sale de ${esc(prev.de)} a las ${hm(prev.sale)}` : '');
  const mins = t => dur(Math.max(1, Math.round((t - now) / 60)));
  return `<div class="c"><div class="th">✈️<span>SIGUIENDO${i.quien ? ' · ' + esc(i.quien).toUpperCase() : ''}</span><div class="ph" style="background:${ec}24;color:${ec}">${et}</div></div>
    <div class="pb"><div class="px"><div class="pm"><a href="${esc(i.fr24)}" target="_blank" rel="noopener" style="color:inherit;text-decoration:none">${esc(i.vuelo)}</a></div>
      <div class="pd">${i.modelo ? esc(i.modelo.replace(/^Boeing (7\d7)-(\d)00/, 'B$1-$2').replace(/^(Airbus|Boeing|Embraer) /, '')) : 'Avión sin asignar'}${i.reg ? ` <small>· ${esc(i.reg)}${i.anos != null ? ` · ${Math.round(i.anos)} años` : ''}</small>` : ''}</div></div>${logo}</div>
    <div class="fr">${cad.map(t => `<b${t.mio ? ' class="mio"' : ''}>${esc(t.de)}</b>${seg(t)}`).join('')}<b class="mio">${esc(i.a)}</b></div>${tu ? `<div class="fcap">${tu}</div>` : ''}
    <div class="pst">${i.estado === 'cancelado' ? stat('Iba a salir', hm(i.sale), i.destino) : `${fstat('Sale', hm(i.previsto), i.estado === 'prog' ? null : i.r, i.de)}
      <div><div class="sl">Puerta</div><div class="sv${i.puerta_antes ? ' cambio' : ''}">${esc(i.puerta) || '–'}${i.puerta_antes ? ` <s>${esc(i.puerta_antes)}</s>` : ''}</div><div class="su">${i.terminal ? 'Terminal ' + esc(i.terminal) : '&nbsp;'}</div></div>
      ${now < emb ? stat('Embarque', 'en ' + mins(emb), 'a las ' + hm(emb)) : stat('Sale en', mins(i.previsto), i.puerta ? 'Puerta ' + i.puerta : '')}`}</div><div class="fsrc">FR24 · AeroDataBox</div></div>`;
}
class VueloSeguidoCard extends AvionCard {
  setConfig(c) { this.entity = c.entity || 'sensor.vuelo_seguido'; this.extra = c.previo || 'sensor.vuelo_previo'; }
  render(s, pv) {
    const l = [...s?.attributes.vuelos || [], ...pv?.attributes.vuelos || []];
    this.style.display = l.length ? '' : 'none';
    return l.map(i => {
      const now = Date.now() / 1e3, [ph, c] = FPHASE[i.fase] || FPHASE.vuelo, r = i.retraso, late = r >= 15, dc = late ? '#C98A0E' : '#3BA55C';
      const p = i.fase === 'aterrizado' ? 1 : i.fase === 'rodando' || !(i.llega > i.sale) ? 0 : Math.min(1, Math.max(0, (now - i.sale) / (i.llega - i.sale)));
      const queda = Math.round((i.llega - now) / 60);
      const urls = [i.iata && `https://pics.avs.io/400/160/${encodeURIComponent(i.iata)}.png`,
        i.icao && `https://www.flightradar24.com/static/images/data/operators/${encodeURIComponent(i.icao)}_logo0.png`].filter(Boolean);
      const logo = urls.length ? `<img class="pl" alt="${esc(i.aerolinea)}" src="${urls[0]}" data-next="${urls[1] || ''}">` : `<div class="pl t">${esc(i.aerolinea)}</div>`;
      if (i.previo) return previo(i, logo);
      return `<div class="c"><div class="th">✈️<span>SIGUIENDO${i.quien ? ' · ' + esc(i.quien).toUpperCase() : ''}</span>
          ${i.fase === 'vuelo' ? '' : `<div class="ph" style="background:${c}24;color:${c}">${ph}</div>`}${r == null || i.fase === 'aterrizado' ? '' : `<div class="ph" style="background:${dc}24;color:${dc}">${late ? `Retrasado (${dur(r)})` : 'En hora'}</div>`}</div>
        <div class="pb"><div class="px"><div class="pm"><a href="${esc(i.fr24)}" target="_blank" rel="noopener" style="color:inherit;text-decoration:none">${esc(i.vuelo)}</a></div>
          <div class="pd">${esc(i.modelo)}</div></div>${logo}</div>
        <div class="fr"><b>${esc(i.origen)}</b><div class="fbar"><i style="width:${p * 100}%"></i><span style="left:${p * 100}%">✈</span></div><b>${esc(i.destino)}</b></div>
        <div class="pst">${fstat(i.fase === 'rodando' ? 'Sale' : 'Salió', hm(i.sale), i.r_sale, i.de)}${fstat(i.fase === 'aterrizado' ? 'Llegó' : 'Llega', hm(i.llega), i.retraso, i.a)}
          ${i.fase === 'vuelo' ? stat('Queda', queda > 0 ? dur(queda) : '–', `${n(i.ft)} ft · ${n(i.kmh)} km/h`) : ''}</div></div>`;
    }).join('');
  }
}
customElements.define('vuelo-seguido-card', VueloSeguidoCard);
window.customCards.push({ type: 'vuelo-seguido-card', name: 'Vuelo seguido (Marco)', description: 'Los vuelos de la familia: 12 h antes de salir y en el aire' });
