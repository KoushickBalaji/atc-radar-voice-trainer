# Air Traffic Management (ATM) UI Reference Guide for Coding Agents

This directory contains visually verified reference images, operational screen captures, and UI component diagrams for **Indra AIRCON 2100** and **Raytheon ATM Systems (STARS and AutoTrac III)**.

Every image in this folder has been inspected and verified against operational ATC specifications to ensure accuracy for UI development and styling.

---

## Directory Overview

```
d:/ATC/design/ui-references/
├── indra-aircon-2100/          # 17 cleanly cropped UI components from Indra AIRCON 2100 SDD
├── raytheon-stars/             # 32 verified Raytheon STARS radar scope & TCW console assets
├── raytheon-autotrac/          # 3 verified Raytheon / Collins Aerospace ATM operational images
└── README.md                   # This verification & design guide
```

---

## 1. Indra AIRCON 2100 (Situation Data Display - SDD)

*Source: Official Indra Sistemas AIRCON 2100 Situation Data Display (SDD) documentation (SDD-UM).*  
*All images are tightly cropped to the actual UI panels, with documentation headers and text margins removed.*

### Directory: `indra-aircon-2100/`

| Filename | Visual Content & Verification |
| :--- | :--- |
| `indra_sdd_screen_overview.png` | **Full Radar CWP Scope:** Live radar scope showing aircraft targets with leader lines, sector polygon boundaries (teal), restricted areas (solid dark polygon), fixes (cyan), and docked windows: ARRIVALS, DEPARTURES, TOWER, EXECUTIVE list, PLANNER list, and bottom toolbar. |
| `indra_extended_track_label.png` | **Extended Label Window:** Detailed flight plan window (`FAU7552 WY`, `C310/L`, route `SUAA SUAG AG11A RWY11`, cleared altitude `090 080`, and speed vectors). |
| `indra_leader_line.png` | **Leader Line & Symbology:** Connecting line between aircraft position symbol and track data block with orientation angles. |
| `indra_history_velocity_vector.png`| **History & Speed Vectors:** Multi-dot radar history trail and speed vector extrapolation tick marks. |
| `indra_callsign_menu.png` | **Target Context Pop-Up:** Full dropdown action menu displayed when clicking a track callsign. |
| `indra_stca_warning_alert.png` | **STCA Conflict Styling:** Side-by-side comparison of **STCA Warning** (yellow data block, yellow tie-line with distance `79`) vs **STCA Alert** (red data block, red diamond track symbol, and red collision line). |
| `indra_mtcd_conflict_zones.png` | **MTCD Trajectories:** Medium Term Conflict Detection displaying predicted intersecting routes and shaded conflict zones. |
| `indra_apw_proximity_alert.png` | **Area Proximity Warning (APW):** Visual alert for aircraft approaching or violating restricted airspace boundaries. |
| `indra_msaw_alert_list.png` | **MSAW Alert & List:** Minimum Safe Altitude Warning pop-up alert and active terrain alert list. |
| `indra_clam_ram_heading_alerts.png`| **Conformance Monitoring:** Cleared Level Adherence (CLAM), Route Adherence (RAM), and Heading deviation alert tags. |
| `indra_rie_alarm.png` | **Route Inactive / Deviation:** Route Inactive Estimate (RIE) warning badges on flight strips. |
| `indra_main_menu_toolbar.png` | **Full Bottom CWP Toolbar:** Complete button strip: `EXECUTIVE`, `PLANNER`, `TWR`, `ARR`, `DEP`, `CPDLC`, `RANGE` presets (`20` to `500 NM`), pan controls, `EXP+`/`EXP-`, and position ID `SDD13 ACC`. |
| `indra_executive_flight_list.png` | **Executive Controller List:** Strip list table with columns: `D`, `OET`, `OEP`, `PEL`, `WARN`, `C/S`, `AFL`, `CFL`, `SSR`, `ATYP`, `ADEP`, `ADES`, `RFL`, `SECTOR EXIT`. |
| `indra_planner_flight_list.png` | **Planner Controller List:** Inbound boundary coordination flight list. |
| `indra_arrival_flight_plan_list.png`| **Arrival Flight Plan List:** Runway sequencing table with ETAs and landing runways. |
| `indra_departure_flight_plan_list.png`| **Departure Flight Plan List:** Outbound sequencing table with CTOT, SID, and initial climb levels. |
| `indra_qnh_and_altimeter_menu.png`| **Altimeter Pop-Up:** QNH pressure setting matrix and transition level control. |

---

## 2. Raytheon STARS (Standard Terminal Automation Replacement System)

*Source: FAA TRACON / Raytheon STARS Automation Standard Baseline & RTX Collins Aerospace.*

### Directory: `raytheon-stars/`

| Filename | Visual Content & Verification |
| :--- | :--- |
| `stars_full_radar_screen.png` | **Complete STARS Radar Scope (1510x929):** Authentic full terminal scope. Includes top Display Control Bar (`RANGE 23`, `RR 5`, `MAPS`, `WX1-WX6`, `BRITE`), System Status Area (`0315/19 30.16`), `BOS TOWER` list, `COAST/SUSPEND` list, `FLIGHT PLAN` list, concentric 5NM range rings, runway alignments, and Full Data Blocks (`AAL506 016 15`, `DAL628 028 16`, etc.). |
| `raytheon_stars_cwp_console.jpg` | **Physical STARS Console (RTX Official):** Female air traffic controller with headset operating a modern widescreen STARS console with active radar display, right-side touch controls, and color-coded ATC mechanical keyboard. |
| `faa_tracon_radar_facility.gif` | **FAA TRACON Operational Room:** Controllers actively seated at green CRT/LED radar consoles in a darkened TRACON facility. |
| `stars_system_status_area_ssa.png` | **System Status Area (SSA):** Header containing Zulu time, altimeter setting, active runway, and sector frequency. |
| `stars_dcb_main_menu.png` | **Display Control Bar (DCB):** Top navigation buttons: `RANGE`, `MAPS`, `BRITE`, `CHAR SIZE`, `PREF`. |
| `stars_fdb_full_data_block.png` | **Full Data Block (FDB):** Standard 3-line terminal radar label. |
| `stars_ldb_limited_data_block.png` | **Limited Data Block (LDB):** Uncorrelated target (Mode C altitude + beacon code). |
| `stars_conflict_alert_ca.png` | **Conflict Alert (CA):** Flashing `CA` label on converging aircraft targets. |
| `stars_weather_nexrad_l1.png` to `l6.png`| **Weather Reflectivity Levels 1-6:** Six distinct stippled/hatched weather radar overlays. |
| `stars_atpa_warning_cone.png` | **ATPA Warning Cone:** Amber terminal spacing predictor cone. |
| `stars_atpa_alert_cone.png` | **ATPA Alert Cone:** Red terminal separation violation cone. |
| `stars_flight_plan_list.png` & `stars_tower_list.png` | **System Lists:** Floating text columns for arrivals and departures. |

---

## 3. Raytheon AutoTrac III & ATM Operations

*Source: Raytheon Technologies / Collins Aerospace ATM Portfolio.*

### Directory: `raytheon-autotrac/`

| Filename | Visual Content & Verification |
| :--- | :--- |
| `raytheon_autotrac_controller_position.jpg` | **AutoTrac III CWP Console:** Controller working position showing the large radar scope on the left, stripless electronic flight progress strip columns on the upper right, and the softkey touchscreen comms console (`ADMIN`, `DOOR`, `PHONE`, etc.) on the lower right with specialized trackball and keyboard. |
| `raytheon_nextgen_atm_operations_center.jpg` | **NextGen Operations Center:** High-performance curved widescreen CWP showing composite weather radar overlays (precipitation intensity, echo tops), sector routes, and auxiliary tablet flight viewer. |
| `raytheon_caps_atm_overview.jpg` | **Common Automation Platform Overview:** Controller perspective seated at the multi-window widescreen ATM console. |

---

## Coding Agent Quick Reference: Style & Format Comparison

| Attribute | **Indra AIRCON 2100** | **Raytheon STARS** | **Raytheon AutoTrac III** |
| :--- | :--- | :--- | :--- |
| **Canvas Background** | Slate/charcoal gray (`#11161d`) | Pure black (`#000000`) | Deep charcoal (`#10141a`) |
| **Track Data Block Style** | Green callsign, white text, colored status box (`#00ff00`, `#ffffff`) | Monochromatic bright green (`#00ff66`) or white (`#ffffff`) | Crisp white & cyan with colored urgency badges |
| **STCA / Conflict Alert** | Amber box (Warning), Red box with diamond target & line (Alert) | Flashing `CA` text above callsign with audible alert tone | Red target highlight and predictive conflict vector line |
| **Toolbar Placement** | Bottom horizontal toolbar with boxed buttons (`EXECUTIVE`, `PLANNER`, `RANGE`) | Top horizontal Display Control Bar (DCB) (`RANGE`, `MAPS`, `WX1-6`) | Dockable horizontal / perimeter taskbars with softkey touchscreen |
| **Flight Lists** | Floating titled windows (`ARRIVALS`, `DEPARTURES`, `EXECUTIVE`, `PLANNER`) | Perimeter text blocks (`TOWER`, `FLIGHT PLAN`, `COAST/SUSPEND`) | Stripless electronic flight strips integrated into right-side column |
