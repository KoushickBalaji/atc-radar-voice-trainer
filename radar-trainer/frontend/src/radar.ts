/** Rendu du scope radar (canvas 2D) : fonctions pures de dessin.
 *  Repere : x = NM est, y = NM nord autour du centre secteur ; l'ecran est
 *  obtenu par la vue (pan en NM + zoom en px/NM). */
import type { Aircraft, NavData, SimState } from "./types";

export interface View {
  panX: number;        // decalage du centre vue, en NM
  panY: number;
  scale: number;       // px par NM
  w: number;           // taille CSS du canvas
  h: number;
}

export interface RadarOptions {
  sweep: boolean;
  labels: boolean;
  trails: boolean;
  rings: boolean;
  routes: boolean;
  waypoints: boolean;
  approachMarkers?: boolean;
  hiddenMarkers?: string[];
  exitPulse?: number;
}

export const DEFAULT_RADAR_OPTIONS: RadarOptions = {
  sweep: false, labels: true, trails: true, rings: true, routes: true, waypoints: true, approachMarkers: true,
};

const C = {
  bg: "#101b18",
  grid: "#21382d",
  gridText: "#6a8976",
  sector: "#789586",
  route: "#2f463b",
  wpt: "#83a797",
  fix: "#b1c6aa",
  apt: "#caa54e",
  ok: "#a4d4b0",
  warn: "#ffb454",
  dang: "#ff5868",
  sel: "#9ad9ff",
  fms: "#8f7bff",
  wind: "#69d0ff",
  mag: "#ff5ab0",                     // marqueur "aeronef dans une zone"
};

export const colorOf = (a: Aircraft) =>
  a.msaw?.status === 'warning' || a.alert === "los" ? C.dang : a.alert === "predicted" ? C.warn : C.ok;

export const sx = (v: View, x: number) => v.w / 2 + (x - v.panX) * v.scale;
export const sy = (v: View, y: number) => v.h / 2 - (y - v.panY) * v.scale;
export const toNm = (v: View, px: number, py: number): [number, number] => [
  (px - v.w / 2) / v.scale + v.panX,
  -(py - v.h / 2) / v.scale + v.panY,
];

export function drawScope(
  ctx: CanvasRenderingContext2D,
  v: View,
  nav: NavData,
  st: SimState,
  trails: Map<string, [number, number][]>,
  selected: string | null,
  sweepDeg: number,
  opt: RadarOptions,
) {
  ctx.clearRect(0, 0, v.w, v.h);
  ctx.fillStyle = C.bg;
  ctx.fillRect(0, 0, v.w, v.h);
  ctx.font = "11px Consolas, monospace";
  ctx.textBaseline = "alphabetic";

  // Visibility only: keep the original navigation and simulator state intact.
  const hidden = new Set(opt.hiddenMarkers ?? []);
  const visible = (group: string, name: string) => !hidden.has(`${group}:${name}`);
  const shownNav: NavData = {
    ...nav,
    waypoints: nav.waypoints.filter(p => visible('waypoint', p.name)),
    fixes: nav.fixes.filter(p => visible('fix', p.name)),
    airports: nav.airports.filter(p => visible('airport', p.name)),
    runways: nav.runways?.filter(p => visible('runway', p.name)),
    navaids: nav.navaids?.filter(p => visible('navaid', p.name)),
    msaw: nav.msaw ? {...nav.msaw, regions: nav.msaw.regions.filter(p => visible('msaw', p.id))} : nav.msaw,
    approach: nav.approach ? {
      ...nav.approach, line: hidden.has('approach:line') ? [] : nav.approach.line,
      fixes: nav.approach.fixes.filter(p => visible('approachFix', p.name)),
      distance_markers: nav.approach.distance_markers?.filter(p => visible('distance', p.name)),
    } : null,
  };
  if (opt.rings && !hidden.has('scope:rings')) drawRings(ctx, v, nav.range_nm);
  if (!hidden.has('scope:sector')) {
    drawSector(ctx, v, nav.sector);
    for (const area of nav.entry_areas ?? []) drawSector(ctx, v, [...area.points, area.points[0]]);
  }
  if (!hidden.has('scope:control')) {
    for (const area of nav.control_areas ?? []) drawSector(ctx, v, [...area.points, area.points[0]]);
  }
  drawMinimumAltitudes(ctx, v, shownNav);
  if (!hidden.has("ats:routes")) drawAtsRoutes(ctx, v, nav.ats_routes ?? []);
  for (const hold of nav.holds ?? []) {
    if (!visible('hold', hold.id)) continue;
    const x = sx(v, hold.xy[0]), y = sy(v, hold.xy[1]);
    const scale = sx(v, 1) - sx(v, 0);
    // Nominal footprint at 180 knots and a three-degree-per-second turn.
    const radius = scale * 180 / (3600 * Math.PI / 60);
    const leg = scale * 180 * hold.leg_seconds / 3600;
    ctx.save(); ctx.translate(x, y);
    ctx.strokeStyle = '#f3bb78'; ctx.fillStyle = '#f3bb78';
    ctx.fillText(hold.fix+' hold', 5, 14);
    ctx.rotate((hold.inbound_magnetic_deg + hold.variation_east_deg) * Math.PI / 180);
    ctx.scale(hold.turn === 'left' ? -1 : 1, 1);
    ctx.beginPath(); ctx.arc(radius, 0, radius, Math.PI, 2*Math.PI);
    ctx.lineTo(2*radius, leg); ctx.arc(radius, leg, radius, 0, Math.PI);
    ctx.closePath(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-3, leg/2+4); ctx.lineTo(0, leg/2); ctx.lineTo(3, leg/2+4); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, 0, 2.5, 0, Math.PI*2); ctx.fill(); ctx.restore();
  }
  drawRunways(ctx, v, shownNav);
  drawApproach(ctx, v, shownNav, opt.approachMarkers !== false);
  if (opt.waypoints) { drawRoutes(ctx, v, nav); drawWaypoints(ctx, v, shownNav); }
  drawZones(ctx, v, st);
  if (opt.routes) drawFmsRoutes(ctx, v, st);
  if (opt.sweep) drawSweep(ctx, v, nav.range_nm, sweepDeg);
  drawConflictLines(ctx, v, st);
  for (const a of st.aircraft ?? [])
    drawAircraft(ctx, v, a, trails.get(a.id) ?? [], a.id === selected, opt);
  if (!hidden.has('scope:center')) drawCenterMark(ctx, v);
}

function drawAtsRoutes(ctx: CanvasRenderingContext2D, v: View, branches: NonNullable<NavData['ats_routes']>) {
  if (!branches.length) return;
  ctx.save();
  ctx.strokeStyle = '#fff';
  ctx.fillStyle = '#fff';
  ctx.lineWidth = 1.2;
  ctx.lineCap = 'round';
  ctx.setLineDash([1, 4]);
  for (const branch of branches) {
    ctx.beginPath();
    branch.points.forEach(([x,y], i) => {
      if (i === 0) ctx.moveTo(sx(v,x), sy(v,y));
      else ctx.lineTo(sx(v,x), sy(v,y));
    });
    ctx.stroke();
  }
  ctx.setLineDash([]);
  ctx.font = '11px Consolas, monospace';
  ctx.textBaseline = 'middle';
  const boxes: {left:number; right:number; y:number}[] = [];
  for (const branch of branches) {
    if (!branch.waypoint) continue;
    const [x,y] = branch.points[branch.points.length - 1];
    const px = sx(v,x), py = sy(v,y);
    if (px < 0 || px > v.w || py < 0 || py > v.h) continue;
    const label = branch.waypoint + ' · ' + branch.routes.join('/');
    const width = ctx.measureText(label).width;
    const left = Math.max(2, Math.min(v.w-width-2, x < 0 ? px-width-4 : px+4));
    let labelY = Math.max(8, Math.min(v.h-8, py));
    for (const offset of [0,-14,14,-28,28,-42,42]) {
      const candidate = Math.max(8, Math.min(v.h-8, py+offset));
      if (!boxes.some(b => left < b.right+2 && left+width+2 > b.left && Math.abs(candidate-b.y)<13)) {
        labelY = candidate;
        break;
      }
    }
    boxes.push({left,right:left+width,y:labelY});
    ctx.strokeStyle = C.bg;
    ctx.lineWidth = 3;
    ctx.strokeText(label,left,labelY);
    ctx.fillText(label,left,labelY);
  }
  ctx.restore();
}

function drawMinimumAltitudes(ctx: CanvasRenderingContext2D, v: View, nav: NavData) {
  ctx.save();
  ctx.strokeStyle = '#ad8bc7'; ctx.fillStyle = '#ceb2e2'; ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]); ctx.font = '11px Consolas, monospace';
  for (const region of nav.msaw?.regions ?? []) {
    ctx.beginPath();
    region.points.forEach(([x, y], i) => {
      if (i === 0) ctx.moveTo(sx(v, x), sy(v, y)); else ctx.lineTo(sx(v, x), sy(v, y));
    });
    ctx.closePath(); ctx.stroke();
    ctx.fillText(`MIN ${region.minimum_ft} ft`, sx(v, region.label[0]), sy(v, region.label[1]));
  }
  ctx.restore();
}

function drawApproach(ctx: CanvasRenderingContext2D, v: View, nav: NavData, showMarkers: boolean) {
  ctx.save();
  ctx.strokeStyle = '#64cddb'; ctx.fillStyle = '#98e2eb'; ctx.lineWidth = 1.5;
  ctx.font = '11px Consolas, monospace';
  if (nav.approach) {
    ctx.setLineDash([7, 5]); ctx.beginPath();
    nav.approach.line.forEach((p, i) => i ? ctx.lineTo(sx(v,p[0]), sy(v,p[1])) : ctx.moveTo(sx(v,p[0]), sy(v,p[1])));
    ctx.stroke(); ctx.setLineDash([]);
    for (const fix of showMarkers ? [...nav.approach.fixes, ...(nav.approach.distance_markers ?? [])] : []) {
      const x = sx(v,fix.x), y = sy(v,fix.y);
      ctx.beginPath(); ctx.moveTo(x-5,y-5); ctx.lineTo(x+5,y+5); ctx.moveTo(x-5,y+5); ctx.lineTo(x+5,y-5); ctx.stroke();
      ctx.textAlign = fix.type === 'distance' ? 'left' : 'right';
      ctx.fillText(fix.name, x + (fix.type === 'distance' ? 10 : -10), y-8); ctx.textAlign = 'left';
    }
    const tip = nav.approach.line[1];
    if (tip) { ctx.textAlign = 'right'; ctx.fillText(`ILS ${nav.approach.runway} · ${nav.approach.course_magnetic}°M · ${nav.approach.glide_deg}° GS`, sx(v,tip[0])-8, sy(v,tip[1])-8); ctx.textAlign = 'left'; }
  }
  (nav.navaids ?? []).forEach((aid, i) => {
    const x = sx(v,aid.x), y = sy(v,aid.y);
    ctx.beginPath();
    if (aid.type === 'ndb') ctx.arc(x,y,4,0,Math.PI*2);
    else { ctx.moveTo(x,y-5); ctx.lineTo(x+5,y); ctx.lineTo(x,y+5); ctx.lineTo(x-5,y); ctx.closePath(); }
    ctx.stroke();
    // Offset labels to keep the closely spaced airport antennas readable.
    const lx = sx(v,0)-190, ly = sy(v,0)+60+i*19;
    ctx.globalAlpha = .4; ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(lx+145,ly-4); ctx.stroke(); ctx.globalAlpha = 1;
    ctx.fillText(aid.name,lx,ly);
  });
  ctx.restore();
}

function drawRunways(ctx: CanvasRenderingContext2D, v: View, nav: NavData) {
  ctx.save();
  ctx.strokeStyle = C.apt;
  ctx.fillStyle = C.apt;
  ctx.font = 'bold 11px Consolas, monospace';
  for (const runway of nav.runways ?? []) {
    const [a, b] = runway.ends;
    if (!a || !b) continue;
    const ax = sx(v, a.x), ay = sy(v, a.y), bx = sx(v, b.x), by = sy(v, b.y);
    ctx.lineWidth = Math.max(3, runway.width_m / 1852 * v.scale);
    ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
    const length = Math.hypot(bx - ax, by - ay) || 1;
    const dx = (bx - ax) / length, dy = (by - ay) / length;
    ctx.textAlign = 'center';
    ctx.fillText(a.name, ax - dx * 14, ay - dy * 14 + 4);
    ctx.fillText(b.name, bx + dx * 14, by + dy * 14 + 4);
  }
  ctx.restore();
}

function drawRings(ctx: CanvasRenderingContext2D, v: View, range: number) {
  // pas adaptatif : ~80 px entre anneaux
  const step = [5, 10, 20, 40].find((s) => s * v.scale > 70) ?? 80;
  ctx.strokeStyle = C.grid;
  ctx.fillStyle = C.gridText;
  ctx.lineWidth = 1;
  const cx = sx(v, 0), cy = sy(v, 0);
  for (let r = step; r <= Math.max(range, 80) + step; r += step) {
    ctx.beginPath();
    ctx.arc(cx, cy, r * v.scale, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.fillText(`${r}`, cx + 4, cy - r * v.scale - 3);
  }
  // graduations de cap tous les 30 degres sur l'anneau exterieur
  const R = range * v.scale;
  for (let deg = 0; deg < 360; deg += 30) {
    const a = ((90 - deg) * Math.PI) / 180;
    ctx.beginPath();
    ctx.moveTo(cx + (R - 6) * Math.cos(a), cy - (R - 6) * Math.sin(a));
    ctx.lineTo(cx + R * Math.cos(a), cy - R * Math.sin(a));
    ctx.stroke();
    ctx.fillText(String(deg).padStart(3, "0"),
      cx + (R + 14) * Math.cos(a) - 9, cy - (R + 14) * Math.sin(a) + 4);
  }
}

function drawSector(ctx: CanvasRenderingContext2D, v: View, sector: [number, number][]) {
  if (!sector?.length) return;
  ctx.save();
  ctx.strokeStyle = C.sector;
  ctx.globalAlpha = 0.55;
  ctx.lineWidth = 1.2;
  ctx.setLineDash([7, 6]);
  ctx.beginPath();
  sector.forEach((p, i) => (i ? ctx.lineTo(sx(v, p[0]), sy(v, p[1])) : ctx.moveTo(sx(v, p[0]), sy(v, p[1]))));
  ctx.stroke();
  ctx.restore();
}

function drawRoutes(ctx: CanvasRenderingContext2D, v: View, nav: NavData) {
  ctx.strokeStyle = C.route;
  ctx.lineWidth = 0.8;
  for (const [i, j] of nav.routes ?? []) {
    const a = nav.waypoints[i], b = nav.waypoints[j];
    if (!a || !b) continue;
    ctx.beginPath();
    ctx.moveTo(sx(v, a.x), sy(v, a.y));
    ctx.lineTo(sx(v, b.x), sy(v, b.y));
    ctx.stroke();
  }
}

function drawWaypoints(ctx: CanvasRenderingContext2D, v: View, nav: NavData) {
  ctx.font = "9.5px Consolas, monospace";
  ctx.lineWidth = 1;
  for (const w of nav.waypoints ?? []) {
    const x = sx(v, w.x), y = sy(v, w.y);
    ctx.strokeStyle = C.wpt;
    ctx.fillStyle = C.wpt;
    ctx.globalAlpha = 0.8;
    tri(ctx, x, y, 3.5);
    ctx.globalAlpha = 0.6;
    ctx.fillText(w.name, x + 5, y + 3);
    ctx.globalAlpha = 1;
  }
  ctx.font = "10px Consolas, monospace";
  for (const f of nav.fixes ?? []) {
    const x = sx(v, f.x), y = sy(v, f.y);
    ctx.strokeStyle = C.fix;
    ctx.fillStyle = C.fix;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(x - 4, y); ctx.lineTo(x, y - 4); ctx.lineTo(x + 4, y); ctx.lineTo(x, y + 4);
    ctx.closePath();
    ctx.stroke();
    ctx.fillText(f.name, x + 6, y - 4);
  }
  ctx.font = "bold 10.5px Consolas, monospace";
  for (const p of nav.airports ?? []) {
    const x = sx(v, p.x), y = sy(v, p.y);
    ctx.strokeStyle = C.apt;
    ctx.fillStyle = C.apt;
    ctx.lineWidth = 1.2;
    ctx.strokeRect(x - 4, y - 4, 8, 8);
    ctx.fillText(p.name, x + 6, y + (nav.runways?.length ? 30 : -4));
  }
}

function drawZones(ctx: CanvasRenderingContext2D, v: View, st: SimState) {
  for (const z of st.zones ?? []) {
    ctx.save();
    ctx.strokeStyle = z.color;
    ctx.fillStyle = z.color + "22";
    ctx.lineWidth = 1.4;
    if (z.shape === "CIRCLE" && z.cx != null && z.cy != null && z.r != null) {
      const x = sx(v, z.cx), y = sy(v, z.cy), r = z.r * v.scale;
      // hachures meteo (cellule orageuse) / liseret zone interdite
      ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI);
      ctx.fill(); ctx.stroke();
      ctx.fillStyle = z.color;
      ctx.font = "10px Consolas, monospace";
      ctx.fillText(z.type === "storm" ? "CB" : "P-ZONE", x - 12, y + 3);
    } else if (z.points?.length) {
      ctx.beginPath();
      z.points.forEach((p, i) => (i ? ctx.lineTo(sx(v, p[0]), sy(v, p[1])) : ctx.moveTo(sx(v, p[0]), sy(v, p[1]))));
      ctx.closePath(); ctx.fill(); ctx.stroke();
    }
    ctx.restore();
  }
}

function drawFmsRoutes(ctx: CanvasRenderingContext2D, v: View, st: SimState) {
  ctx.save();
  for (const a of st.aircraft ?? []) {
    const r = a.route ?? [];
    if (!r.length) continue;
    ctx.strokeStyle = C.fms;
    ctx.lineWidth = 0.9;
    ctx.setLineDash([2, 4]);
    ctx.beginPath();
    ctx.moveTo(sx(v, a.x), sy(v, a.y));
    for (const p of r) ctx.lineTo(sx(v, p[0]), sy(v, p[1]));
    ctx.stroke();
    ctx.setLineDash([]);
    if (a.actwp >= 0 && a.actwp < r.length) {
      const w = r[a.actwp];
      ctx.strokeStyle = C.fms;
      ctx.beginPath();
      ctx.arc(sx(v, w[0]), sy(v, w[1]), 3, 0, 2 * Math.PI);
      ctx.stroke();
    }
  }
  ctx.restore();
}

function drawSweep(ctx: CanvasRenderingContext2D, v: View, range: number, deg: number) {
  const cx = sx(v, 0), cy = sy(v, 0), R = range * v.scale;
  ctx.save();
  for (let k = 16; k >= 0; k--) {
    const a = ((90 - (deg - k * 2.2)) * Math.PI) / 180;
    ctx.strokeStyle = C.ok;
    ctx.globalAlpha = k === 0 ? 0.5 : Math.max(0, 0.12 - k * 0.007);
    ctx.lineWidth = k === 0 ? 1.2 : 1.6;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + R * Math.cos(a), cy - R * Math.sin(a));
    ctx.stroke();
  }
  ctx.restore();
}

function drawConflictLines(ctx: CanvasRenderingContext2D, v: View, st: SimState) {
  const pos = new Map((st.aircraft ?? []).map((a) => [a.id, a]));
  for (const pair of st.conflicts ?? []) {
    const a = pos.get(pair[0]), b = pos.get(pair[1]);
    if (!a || !b) continue;
    ctx.strokeStyle = C.dang;
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(sx(v, a.x), sy(v, a.y));
    ctx.lineTo(sx(v, b.x), sy(v, b.y));
    ctx.stroke();
  }
  for (const p of st.predicted ?? []) {
    const a = pos.get(p.pair[0]), b = pos.get(p.pair[1]);
    if (!a || !b) continue;
    ctx.save();
    ctx.strokeStyle = C.warn;
    ctx.lineWidth = 1.1;
    ctx.setLineDash([5, 4]);
    ctx.beginPath();
    ctx.moveTo(sx(v, a.x), sy(v, a.y));
    ctx.lineTo(sx(v, b.x), sy(v, b.y));
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = C.warn;
    ctx.font = "10px Consolas, monospace";
    ctx.fillText(`${p.t}s · ${p.d} NM`,
      (sx(v, a.x) + sx(v, b.x)) / 2 + 4, (sy(v, a.y) + sy(v, b.y)) / 2 - 4);
  }
}

function drawAircraft(
  ctx: CanvasRenderingContext2D,
  v: View,
  a: Aircraft,
  trail: [number, number][],
  isSel: boolean,
  opt: RadarOptions,
) {
  const col = colorOf(a);
  const x = sx(v, a.x), y = sy(v, a.y);

  if (opt.trails) {
    ctx.fillStyle = col;
    trail.forEach(([tx, ty], i) => {
      ctx.globalAlpha = 0.06 + (0.3 * i) / Math.max(1, trail.length);
      ctx.fillRect(sx(v, tx) - 1.5, sy(v, ty) - 1.5, 3, 3);
    });
    ctx.globalAlpha = 1;
  }

  // vecteur vitesse : projection a 1 minute (gs / 60 NM)
  const lead = (a.gs / 60) * v.scale;
  const ah = ((90 - (a.trk ?? a.hdg)) * Math.PI) / 180;
  ctx.strokeStyle = col;
  ctx.lineWidth = 1.1;
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + lead * Math.cos(ah), y - lead * Math.sin(ah));
  ctx.stroke();

  // blip
  ctx.lineWidth = 1.7;
  ctx.strokeRect(x - 4, y - 4, 8, 8);
  if (a.inzone) {
    ctx.strokeStyle = C.mag;          // marqueur "dans une zone" (palette)
    ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.arc(x, y, 10, 0, 2 * Math.PI); ctx.stroke();
  }
  if (isSel) {
    ctx.strokeStyle = C.sel;
    ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.arc(x, y, 13, 0, 2 * Math.PI); ctx.stroke();
  }

  if (a.control_area?.exit_in_s != null) {
    ctx.strokeStyle = C.warn;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, 16 + 5 * (opt.exitPulse ?? 0), 0, 2 * Math.PI);
    ctx.stroke();
    if (!opt.labels) {
      ctx.fillStyle = C.warn;
      ctx.font = 'bold 11px Consolas, monospace';
      ctx.fillText(a.id + ' EXIT', x + 22, y - 6);
    }
  }

  if (!opt.labels) return;
  // bloc de donnees : CS / FL(tendance)CFL / GS - ligne d'attache + fond
  const lx = x + 14, ly = y - 22;
  const trend = a.vs_fpm > 300 ? "↑" : a.vs_fpm < -300 ? "↓" : "";
  const cfl = a.sel_alt_ft != null && Math.abs(a.sel_alt_ft - a.alt_ft) > 200
    ? String(Math.round(a.sel_alt_ft / 100)).padStart(3, "0") : "";
  const l1 = [a.id, a.msaw?.status === 'warning' && 'MSAW', a.control_area?.exit_in_s != null && 'EXIT'].filter(Boolean).join(' ');
  const l2 = `${String(a.fl).padStart(3, "0")}${trend}${cfl ? " " + cfl : ""} ${String(a.gs).padStart(3, "0")}`;
  ctx.font = "11px Consolas, monospace";
  const wd = Math.max(ctx.measureText(l1).width, ctx.measureText(l2).width);
  ctx.strokeStyle = col;
  ctx.globalAlpha = 0.5;
  ctx.lineWidth = 0.8;
  ctx.beginPath(); ctx.moveTo(x + 5, y - 5); ctx.lineTo(lx - 2, ly + 12); ctx.stroke();
  ctx.globalAlpha = 1;
  ctx.fillStyle = "rgba(5,8,13,0.72)";
  ctx.fillRect(lx - 3, ly - 10, wd + 7, 26);
  ctx.fillStyle = a.msaw?.status === 'warning' ? C.dang : isSel ? C.sel : col;
  ctx.fillText(l1, lx, ly);
  ctx.fillText(l2, lx, ly + 12);
}

function drawCenterMark(ctx: CanvasRenderingContext2D, v: View) {
  const x = sx(v, 0), y = sy(v, 0);
  ctx.strokeStyle = C.ok;
  ctx.lineWidth = 1.1;
  ctx.beginPath();
  ctx.moveTo(x - 6, y); ctx.lineTo(x + 6, y);
  ctx.moveTo(x, y - 6); ctx.lineTo(x, y + 6);
  ctx.stroke();
}

export function drawWindArrow(ctx: CanvasRenderingContext2D, v: View, st: SimState) {
  const w = st.wind;
  if (!w) return;
  const ox = 60, oy = v.h - 100, len = 24; // Leave room for the keyboard/pointer help.
  const a = ((90 - (w.dir + 180)) * Math.PI) / 180;   // fleche orientee "vers ou va" le vent
  ctx.save();
  ctx.strokeStyle = C.wind;
  ctx.fillStyle = C.wind;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(ox, oy);
  ctx.lineTo(ox + len * Math.cos(a), oy - len * Math.sin(a));
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(ox + len * Math.cos(a), oy - len * Math.sin(a), 2.5, 0, 2 * Math.PI);
  ctx.fill();
  ctx.font = "11px Consolas, monospace";
  ctx.fillText(
    `VENT ${String(w.dir).padStart(3, "0")}/${w.spd} kt${w.alt ? " FL" + Math.round(w.alt / 100) : ""}`,
    ox - 32, oy + 18);
  ctx.restore();
}

function tri(ctx: CanvasRenderingContext2D, x: number, y: number, s: number) {
  ctx.beginPath();
  ctx.moveTo(x, y - s);
  ctx.lineTo(x - s, y + s);
  ctx.lineTo(x + s, y + s);
  ctx.closePath();
  ctx.stroke();
}
