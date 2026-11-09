import { useEffect, useState } from 'react';
import { Info } from 'lucide-react';

interface Report {
  obsTime: number;
  temp: number | null;
  dewp: number | null;
  wdir: string | number | null;
  wspd: number | null;
  wgst: number | null;
  altim: number | null;
  visibility: string | null;
  wxString: string | null;
  clouds: { cover: string; base: number | null }[] | null;
  rawOb: string | null;
  metarType: string | null;
}

const phenomena: Record<string, string> = {
  RA: 'rain', DZ: 'drizzle', SN: 'snow', HZ: 'haze', BR: 'mist', FG: 'fog',
  TS: 'thunderstorm', SH: 'showers', GR: 'hail', FU: 'smoke', DU: 'dust',
  SA: 'sand', SQ: 'squall', FC: 'funnel cloud', FZ: 'freezing', VA: 'volcanic ash',
};

function condition(token: string) {
  const intensity = token.startsWith('-') ? 'light ' : token.startsWith('+') ? 'heavy ' : '';
  const code = token.replace(/^[+-]/, '');
  const parts = code.match(/.{2}/g) ?? [];
  if (parts.join('') !== code || parts.some(p => !phenomena[p])) return token;
  const phrase = code === 'SHRA' ? 'rain showers' : parts.map(p => phenomena[p]).join(' ');
  return intensity + phrase;
}

function wind(r: Report) {
  if (r.wspd == null) return '—';
  if (r.wspd === 0 && !r.wgst) return 'calm';
  const dir = typeof r.wdir === 'number' ? String(r.wdir).padStart(3, '0') + '°T' : r.wdir;
  return [dir, r.wspd + (r.wgst != null ? 'G' + r.wgst : '') + ' kt'].filter(Boolean).join(' ');
}

export default function WeatherStrip({ icao }: { icao: string }) {
  const [report, setReport] = useState<Report | null>(null);
  const [status, setStatus] = useState('loading');
  const [now, setNow] = useState(Date.now);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    async function refresh() {
      try {
        const response = await fetch('/api/weather/observation/' + encodeURIComponent(icao), {signal: controller.signal});
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (controller.signal.aborted || data.icao !== icao) return;
        if (data.report) setReport(data.report);
        setStatus(data.status);
        setNow(Date.now());
      } catch {
        if (!controller.signal.aborted) setStatus('refresh_failed');
      }
    }
    void refresh();
    const refreshId = window.setInterval(refresh, 300_000);
    const ageId = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => { controller.abort(); clearInterval(refreshId); clearInterval(ageId); };
  }, [icao]);
  const age = report && Math.max(0, Math.floor((now / 1000 - report.obsTime) / 60));
  const observed = report && new Date(report.obsTime * 1000);
  return <section aria-label="Airport weather" className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-edge bg-panel px-5 py-1 text-xs tabular-nums">
    <span className="relative flex items-center gap-1 font-semibold"
      onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}
      onBlur={() => setOpen(false)} onKeyDown={e => { if (e.key === 'Escape') setOpen(false); }}>
      WX {icao}
      <button type="button" aria-label="Weather details" aria-expanded={open} aria-controls="wx-details"
        className="rounded p-1 text-mut" onFocus={() => setOpen(true)} onClick={() => setOpen(true)}>
        <Info size={15} aria-hidden="true" />
      </button>
      {open && <span id="wx-details" role="tooltip" className="absolute left-0 top-full z-50 grid w-80 max-w-[90vw] gap-1 rounded border border-edge bg-panel2 p-3 font-normal shadow-lg">
        <strong>Aviation Weather Center · {report?.metarType ?? 'METAR'}</strong>
        {observed && <span>Observed {observed.toISOString().slice(0, 16).replace('T', ' ')} UTC</span>}
        {report?.dewp != null && <span>Dew point {report.dewp} °C</span>}
        {!!report?.clouds?.length && <span>Clouds {report.clouds.map(c => c.cover + (c.base != null ? ' ' + c.base + ' ft' : '')).join(' · ')}</span>}
        {report?.rawOb && <span className="font-mono">{report.rawOb}</span>}
        {status === 'refresh_failed' && <span>Weather refresh failed.</span>}
        {status === 'no_recent_report' && <span>No recent station report received.</span>}
      </span>}
    </span>
    {report ? <>
      <span>Wind {wind(report)}</span><span>Vis {report.visibility ?? '—'}</span>
      {report.wxString && <span className="capitalize">{report.wxString.split(/\s+/).map(condition).join(' · ')}</span>}
      <span>Temp {report.temp == null ? '—' : report.temp + ' °C'}</span>
      <span>QNH {report.altim == null ? '—' : Math.round(report.altim) + ' hPa'}</span>
      <span className={age! >= 60 || status !== 'ok' ? 'text-warn' : 'text-mut'}>
        {age! >= 60 ? 'Stale · ' : status !== 'ok' ? 'Cached · ' : ''}{age} min ago
      </span>
    </> : <span className="text-mut">{status === 'loading' ? 'Loading…' : 'Unavailable'}</span>}
  </section>;
}
