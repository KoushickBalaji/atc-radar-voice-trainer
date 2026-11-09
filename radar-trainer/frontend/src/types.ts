/** Types partages : miroirs des payloads du serveur FastAPI (atc_app.py). */

export interface Aircraft {
  role?: 'arrival' | 'departure' | 'overflight';
  phase?: string;
  ils?: SimState['ils'];
  control_area?: {status: string; areas: string[]; uncertain: string[]; exit_in_s?: number | null};
  msaw?: {status: 'warning' | 'clear' | 'unavailable' | 'outside_coverage' | 'approach_suspended' | 'invalid_position'; minimum_ft: number | null; deficit_ft: number; regions: string[]};
  id: string;
  x: number;          // NM est, autour du centre secteur
  y: number;          // NM nord
  lat: number;
  lon: number;
  hdg: number;
  trk: number;        // route sol (effet du vent)
  alt_ft: number;
  fl: number;
  gs: number;         // vitesse sol (kt)
  vs_fpm: number;     // vitesse verticale (ft/min)
  sel_alt_ft: number | null;  // altitude autorisee (autopilote)
  type: string;
  conflict: boolean;
  alert: "" | "los" | "predicted";
  inzone: string;
  route: [number, number][];
  actwp: number;
  cas_kt?: number | null;
  tas_kt?: number | null;
  lnav?: boolean | null;
  vnav?: boolean | null;
  route_names?: string[];
}

export interface Predicted { pair: [string, string]; t: number; d: number }

export interface Zone {
  name: string;
  type: "storm" | "restricted";
  shape: "CIRCLE" | "POLY";
  cx?: number; cy?: number; r?: number;
  points?: [number, number][];
  color: string;
}

export interface Wind { dir: number; spd: number; alt: number | null }

export interface ExerciseScore {
  total: number; grade: string;
  separation: number; conflits: number; zones: number; radio: number;
  n_los: number; t_los_s: number;
  conflits_predits: number; conflits_resolus: number;
  n_zone: number; t_zone_s: number;
  cmd_acceptees: number; cmd_rejetees: number;
}

export interface ExerciseBrief { elapsed_s: number; remaining_s: number; score: ExerciseScore }

export interface SimState {
  airport_id?: string | null;
  ils?: { go_around_on_handoff?: boolean; phase: string; message: string; along_nm?: number; cross_nm?: number; intercept_deg?: number; glide_alt_ft?: number; glide_error_ft?: number; speed_ok?: boolean; level_ok?: boolean; stable_s?: number;
    holding?: {fix:string; phase:string; entry:string|null; circuits:number; altitude_ft:number; expected:string|null};
    missed_approach?: {name:string; source:string; approach_id:string; runway:string; legs:string[]; max_kias:number; overrides:Record<string,number>} | null } | null;
  t: number;
  running: boolean;
  paused: boolean;
  speed: number;
  traffic?: {id:string; title:string; brief:string; complete:boolean; flights:{callsign:string; role:string; phase:string; overdue?:boolean}[]} | null;
  traffic_calls?: {id:string; callsign:string; text:string}[];
  pilot_call?: {id: string; callsign: string; text: string} | null;
  aircraft: Aircraft[];
  conflicts: [string, string][];
  predicted: Predicted[];
  cd_engine?: string;
  wind?: Wind | null;
  turbulence?: number;
  zones?: Zone[];
  exercise?: ExerciseBrief;
  sim_alive?: boolean;
  last_error?: string | null;
  pending_commands?: number;
  advance_failures?: number;
  command_errors?: { kind: string; message: string }[];
}

export interface NavPoint { x: number; y: number; name: string; type?: string }

export interface AirportProfile {
  scenarios?: {id:string; title:string}[];
  entry?: {status: string; boundary: string | null; buffer_nm: number | null; note: string; incomplete?: boolean};
  tower?: {name: string; frequency_mhz: string; source_file: string; source_page: number} | null;
  mode?: 'ils' | 'vectoring'; scope_note?: string | null;
  icao: string; name: string; elevation_ft: number; range_nm: number;
  runway: {name: string; length_m: number; width_m: number; ends: {bearing_magnetic_chart?: number | null}[]};
  approach: {runway: string; course_true: number; course_magnetic: number; glide_deg: number; intercept_alt_ft: number} | null;
  training: Record<string, number>;
  tower_handover?: {request_nm: number; go_around_nm: number} | null;
  aircraft: {callsign: string};
  examples: string[];
}

export interface NavData {
  ats_routes?: {points:[number,number][]; waypoint:string|null; routes:string[]}[];
  holds?: {id:string; fix:string; xy:[number,number]; inbound_magnetic_deg:number; variation_east_deg:number;
    turn:'left'|'right'; leg_seconds:number; minimum_ft:number; max_kias:number}[];
  entry_areas?: {name: string; points: [number, number][]}[];
  control_areas?: {name: string; points: [number, number][]; lower: {reference: string; value?: number}; upper: {reference: string; value?: number}}[];
  msaw?: {source: {chart: string; effective_date: string}; regions: {id: string; minimum_ft: number; points: [number, number][]; label: [number, number]}[]} | null;
  profile?: AirportProfile;
  navaids?: NavPoint[];
  approach?: { runway: string; course_true: number; course_magnetic: number; glide_deg: number; intercept_alt_ft: number; line: [number, number][]; fixes: NavPoint[]; distance_markers?: NavPoint[] } | null;
  runways?: { name: string; length_m: number; width_m: number; ends: NavPoint[] }[];
  waypoints: NavPoint[];
  airports: NavPoint[];
  fixes: NavPoint[];
  routes: [number, number][];
  sector: [number, number][];
  range_nm: number;
  center: [number, number];
}

/** Etat de sante des trois fournisseurs IA (contrat OpenAI-compatible). */
export interface Providers { stt: boolean; llm: boolean; tts: boolean }

export interface Order { callsign: string; action: string; value?: number; wpt?: string }

export interface Exchange {
  transcript: string;
  orders: Order[];
  trafscript: string[];
  rejected: string[];
  readback: string;
  audio_b64?: string | null;
  tts_error?: string | null;
}

export interface ExerciseState {
  active: boolean;
  label?: string;
  difficulty?: string;
  duration_s?: number;
  elapsed_s?: number;
  remaining_s?: number;
  objectives?: string[];
  aircraft?: string[];
  conflicts_built?: { pair: [string, string]; fl: number; t_cross_s: number }[];
  wind?: Wind | null;
  storm?: { x: number; y: number; r: number } | null;
  turbulence?: number;
  score?: ExerciseScore;
  last_report?: boolean;
}

export interface ExerciseReport extends Omit<ExerciseState, "score" | "active"> {
  ended_iso: string;
  started_iso: string;
  auto_ended: boolean;
  elapsed_s: number;
  score: ExerciseScore;
  minsep_series: [number, number | null][];
  los_events: { pair: string[]; t_start: number; t_end: number; min_nm: number | null }[];
  predicted_events: { pair: string[]; t_first: number; d_min: number | null }[];
  zone_events: { callsign: string; zone: string; t_start: number; t_end: number }[];
  commands: { t: number; text: string; accepted: number; rejected: number }[];
}

export interface LogEntry {
  exchangeId?: number;
  exchange?: Omit<Exchange, 'audio_b64'>;
  callsigns?: string[];
  id: number;
  t: string;             // horodatage local hh:mm:ss
  kind: "info" | "tx" | "cmd" | "pilot" | "rej" | "warn" | "ok";
  text: string;
}

export interface ScenarioMeta { name: string; title: string; description: string }

export type PlaceMode = "storm" | "restricted" | null;
