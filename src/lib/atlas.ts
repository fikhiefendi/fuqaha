// Client-side map styling shared by the map, the mini maps and the time map:
// a parchment base map, red-ink city rings in the manner of the classical
// Islamic geographers, region names, a compass rose and curved routes.
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import '../styles/atlas-map.css';

export type Region = { name: string; nameAr: string; lat: number; lng: number };

export function atlasMap(el: HTMLElement, options: L.MapOptions = {}) {
  const map = L.map(el, { zoomControl: false, worldCopyJump: true, minZoom: 3, maxZoom: 9, ...options });
  el.classList.add('atlas-map');
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Esri, US National Park Service · al-Ṯurayyā (CC BY 4.0)',
    maxNativeZoom: 8,
    maxZoom: 9,
    className: 'atlas-tiles',
  }).addTo(map);
  map.attributionControl?.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
  const veil = document.createElement('div');
  veil.className = 'atlas-veil';
  el.append(veil);
  return map;
}

/** City marker: a red ink ring with a paper-coloured centre, sized by weight. */
export function cityIcon(weight = 1, opts: { approx?: boolean; on?: boolean } = {}) {
  const r = Math.min(3 + 1.35 * Math.sqrt(weight), 11);
  const d = Math.ceil(r * 2 + 8);
  const cls = ['city', opts.approx ? 'approx' : '', opts.on ? 'on' : ''].join(' ');
  return L.divIcon({
    className: cls,
    iconSize: [d, d],
    html: `<svg width="${d}" height="${d}" viewBox="${-d / 2} ${-d / 2} ${d} ${d}" aria-hidden="true">
      <circle class="halo" r="${r + 3}"/>
      <circle class="ring" r="${r}"/>
      <circle class="core" r="${Math.max(r * 0.42, 1.8)}"/>
    </svg>`,
  });
}

/** Two-line label: Arabic name over the reader's name (Arabic only on Arabic pages). */
export function cityLabel(name: string, nameAr: string, rtl: boolean) {
  return rtl || !nameAr ? `<span class="ar">${esc(nameAr || name)}</span>` : `<span class="ar">${esc(nameAr)}</span><span>${esc(name)}</span>`;
}

export function regionLabels(map: L.Map, regions: Region[], rtl: boolean) {
  const layer = L.layerGroup(
    regions.map((r) =>
      L.marker([r.lat, r.lng], {
        interactive: false,
        keyboard: false,
        icon: L.divIcon({
          className: 'region-label',
          iconSize: [0, 0],
          html: `<span>${esc(rtl ? r.nameAr : r.name)}</span>`,
        }),
      }),
    ),
  ).addTo(map);
  const sync = () => map.getContainer().classList.toggle('show-regions', map.getZoom() <= 6);
  map.on('zoomend', sync);
  sync();
  return layer;
}

/** Compass rose with the Arabic cardinal points. */
export function compass(map: L.Map, position: L.ControlPosition = 'bottomleft') {
  const C = L.Control.extend({
    onAdd() {
      const div = L.DomUtil.create('div', 'compass');
      div.setAttribute('aria-hidden', 'true');
      const ray = (a: number, long: boolean) => {
        const rad = (a * Math.PI) / 180;
        const len = long ? 34 : 20;
        const w = long ? 5 : 3.5;
        const tip = [Math.sin(rad) * len, -Math.cos(rad) * len];
        const l = [Math.sin(rad - Math.PI / 2) * w, -Math.cos(rad - Math.PI / 2) * w];
        const r = [Math.sin(rad + Math.PI / 2) * w, -Math.cos(rad + Math.PI / 2) * w];
        return `<path class="dark" d="M0 0L${l[0]} ${l[1]}L${tip[0]} ${tip[1]}Z"/><path class="light" d="M0 0L${r[0]} ${r[1]}L${tip[0]} ${tip[1]}Z"/>`;
      };
      div.innerHTML = `<svg width="104" height="104" viewBox="-52 -52 104 104">
        <circle r="40" class="rim"/><circle r="36" class="rim thin"/>
        ${[45, 135, 225, 315].map((a) => ray(a, false)).join('')}
        ${[0, 90, 180, 270].map((a) => ray(a, true)).join('')}
        <circle r="3" class="pin"/>
        <text y="-43">شمال</text><text y="50">جنوب</text>
        <text x="45" y="3" transform="rotate(90 45 3)">شرق</text><text x="-45" y="3" transform="rotate(-90 -45 3)">غرب</text>
      </svg>`;
      return div;
    },
  });
  return new C({ position }).addTo(map);
}

/** A gently curved, dotted route through the given points (a caravan road). */
export function route(points: L.LatLngExpression[], className = 'route') {
  const pts = points.map((p) => L.latLng(p));
  const path: L.LatLng[] = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    const mx = (a.lat + b.lat) / 2;
    const my = (a.lng + b.lng) / 2;
    const dx = b.lng - a.lng;
    const dy = b.lat - a.lat;
    const c = L.latLng(mx + dx * 0.18, my - dy * 0.18);
    for (let t = 0; t <= 1; t += 0.05) {
      const u = 1 - t;
      path.push(L.latLng(u * u * a.lat + 2 * u * t * c.lat + t * t * b.lat, u * u * a.lng + 2 * u * t * c.lng + t * t * b.lng));
    }
  }
  return L.polyline(path, { className, interactive: false });
}

/** How many links a city needs for a permanent name at the current zoom. */
export const labelThreshold = (zoom: number) => (zoom <= 4 ? 18 : zoom === 5 ? 7 : zoom === 6 ? 3 : 1);

export function zoomButtons(map: L.Map, position: L.ControlPosition = 'topright') {
  return L.control.zoom({ position, zoomInTitle: '+', zoomOutTitle: '−' }).addTo(map);
}

export const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);

export { L };
