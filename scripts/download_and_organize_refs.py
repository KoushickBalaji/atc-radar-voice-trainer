import os
import urllib.request
import pypdfium2 as pdfium
import shutil

BASE_DIR = 'd:/ATC/design/ui-references'
INDRA_DIR = os.path.join(BASE_DIR, 'indra-aircon-2100')
STARS_DIR = os.path.join(BASE_DIR, 'raytheon-stars')
AUTOTRAC_DIR = os.path.join(BASE_DIR, 'raytheon-autotrac')

os.makedirs(INDRA_DIR, exist_ok=True)
os.makedirs(STARS_DIR, exist_ok=True)
os.makedirs(AUTOTRAC_DIR, exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def download_file(url, out_path):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            with open(out_path, 'wb') as f:
                f.write(data)
            print(f"Downloaded: {os.path.basename(out_path)} ({len(data)} bytes)")
            return True
    except Exception as e:
        print(f"Failed {url}: {e}")
        return False

# =========================================================================
# 1. INDRA AIRCON 2100 (Extract high-res pages & diagrams from SDD Manual)
# =========================================================================
print("\n--- Processing Indra Aircon 2100 Reference Images ---")
pdf_path = 'd:/ATC/design/MANUAL_SDD_2014.pdf'
if os.path.exists(pdf_path):
    pdf = pdfium.PdfDocument(pdf_path)
    
    # Selected high-value pages:
    # Page 24: Global Architecture
    # Page 39: Figure 2-5 SDD Screen (Main Situation Display Example)
    # Page 60: Callsign Menu
    # Page 65: STCA Warning and Alert Tracks
    # Page 73: APW List & Prediction, MSAW Alert Prediction
    # Page 74: MSAW Violation & List
    # Page 114: Figure 2-45 SDD Screen Layout
    # Page 116: CFL (Cleared Flight Level) Menu
    # Page 137: Options Menu
    # Page 139: Presentation Range Menu
    # Page 205: Maps Selection Menu
    # Page 217: Main Menu Area
    # Page 224: Executive List
    # Page 227: Planner List
    # Page 234: Arrival Flight Plan List
    # Page 237: Departure Flight Plan List
    # Page 302: QNH and Zone Selection
    # Page 346: MSAW List
    # Page 370: STCA Warning & Alert Tracks
    
    pages_to_render = {
        24: "indra_system_architecture.png",
        39: "indra_sdd_screen_overview.png",
        60: "indra_callsign_menu.png",
        65: "indra_stca_warning_alert_tracks.png",
        73: "indra_apw_msaw_prediction_alerts.png",
        74: "indra_msaw_violation_and_list.png",
        114: "indra_sdd_operational_screen.png",
        116: "indra_cfl_cleared_level_menu.png",
        137: "indra_options_menu.png",
        139: "indra_range_selection_menu.png",
        205: "indra_maps_selection_menu.png",
        217: "indra_main_menu_area_layout.png",
        224: "indra_executive_flight_list.png",
        227: "indra_planner_flight_list.png",
        234: "indra_arrival_flight_plan_list.png",
        237: "indra_departure_flight_plan_list.png",
        302: "indra_qnh_and_altimeter_menu.png",
        346: "indra_msaw_warning_list.png",
        370: "indra_stca_conflict_tracks_detail.png"
    }
    
    for page_num, filename in pages_to_render.items():
        out_path = os.path.join(INDRA_DIR, filename)
        page = pdf[page_num - 1]
        # render at scale 2.5 for crisp high-dpi text and graphics
        img = page.render(scale=2.5).to_pil()
        img.save(out_path)
        print(f"Rendered Indra Ref: {filename} ({img.size[0]}x{img.size[1]})")

# =========================================================================
# 2. RAYTHEON STARS (Download official & pixel-accurate radar images)
# =========================================================================
print("\n--- Downloading Raytheon STARS Reference Images ---")

stars_urls = {
    # Main screen & workstation
    "stars_full_radar_screen.png": "https://docs.virtualnas.net/crc/img/stars/stars-main.png",
    "vstars_operational_scope.jpg": "https://vstars.rosscarlson.dev/index_files/screenshot.jpg",
    "stars_tracon_workstation_faa.jpg": "https://upload.wikimedia.org/wikipedia/commons/c/cc/Tracon_2013_06.jpg",
    "stars_system_status_area_ssa.png": "https://docs.virtualnas.net/crc/img/stars/ssa.png",
    "stars_system_status_area_ssa2.png": "https://docs.virtualnas.net/crc/img/stars/ssa2.png",
    "stars_preview_area.png": "https://docs.virtualnas.net/crc/img/stars/preview-area.png",
    "stars_dcb_main_menu.png": "https://docs.virtualnas.net/crc/img/stars/dcb/main-menu.png",
    "stars_dcb_aux_menu.png": "https://docs.virtualnas.net/crc/img/stars/dcb/aux-menu.png",
    "stars_dcb_maps_submenu.png": "https://docs.virtualnas.net/crc/img/stars/dcb/maps-submenu.png",
    "stars_dcb_brightness_menu.png": "https://docs.virtualnas.net/crc/img/stars/dcb/brite-submenu.png",
    
    # Flight Data Blocks (FDB, LDB, PDB)
    "stars_fdb_full_data_block.png": "https://docs.virtualnas.net/crc/img/stars/data-blocks/fdb.png",
    "stars_ldb_limited_data_block.png": "https://docs.virtualnas.net/crc/img/stars/data-blocks/ldb.png",
    "stars_pdb_partial_data_block.png": "https://docs.virtualnas.net/crc/img/stars/data-blocks/pdb.png",
    "stars_fdb_owned_other.png": "https://docs.virtualnas.net/crc/img/stars/data-blocks/fdb-owned-other.png",
    "stars_handoff_data_block.png": "https://docs.virtualnas.net/crc/img/stars/data-blocks/handoff.png",
    "stars_conflict_alert_ca.png": "https://docs.virtualnas.net/crc/img/stars/data-blocks/conflict-alert.png",
    "stars_assigned_altitude_block.png": "https://docs.virtualnas.net/crc/img/stars/data-blocks/assigned-altitude.png",
    "stars_ptl_predicted_track_line.png": "https://docs.virtualnas.net/crc/img/stars/data-blocks/ptl.png",
    
    # System Lists
    "stars_flight_plan_list.png": "https://docs.virtualnas.net/crc/img/stars/system-lists/flight-plan.png",
    "stars_tower_list.png": "https://docs.virtualnas.net/crc/img/stars/system-lists/tower.png",
    "stars_coast_suspend_list.png": "https://docs.virtualnas.net/crc/img/stars/system-lists/coast-suspend.png",
    "stars_vfr_list.png": "https://docs.virtualnas.net/crc/img/stars/system-lists/vfr.png",
    "stars_geo_maps_list.png": "https://docs.virtualnas.net/crc/img/stars/system-lists/geo-maps.png",
    
    # Weather overlays (NEXRAD levels 1-6)
    "stars_weather_nexrad_l1.png": "https://docs.virtualnas.net/crc/img/stars/nexrad/l1.png",
    "stars_weather_nexrad_l2.png": "https://docs.virtualnas.net/crc/img/stars/nexrad/l2.png",
    "stars_weather_nexrad_l3.png": "https://docs.virtualnas.net/crc/img/stars/nexrad/l3.png",
    "stars_weather_nexrad_l4.png": "https://docs.virtualnas.net/crc/img/stars/nexrad/l4.png",
    "stars_weather_nexrad_l5.png": "https://docs.virtualnas.net/crc/img/stars/nexrad/l5.png",
    "stars_weather_nexrad_l6.png": "https://docs.virtualnas.net/crc/img/stars/nexrad/l6.png",
    
    # Separation & Warning Cones
    "stars_atpa_warning_cone.png": "https://docs.virtualnas.net/crc/img/stars/atpa-warning-cone.png",
    "stars_atpa_alert_cone.png": "https://docs.virtualnas.net/crc/img/stars/atpa-alert-cone.png",
    "stars_tpa_j_rings.png": "https://docs.virtualnas.net/crc/img/stars/tpa-j-rings.png"
}

for fname, url in stars_urls.items():
    out_file = os.path.join(STARS_DIR, fname)
    download_file(url, out_file)

# =========================================================================
# 3. RAYTHEON AUTOTRAC & GENERAL ATC RADAR REFERENCES
# =========================================================================
print("\n--- Downloading Raytheon AutoTrac / General Radar References ---")

autotrac_urls = {
    "atc_radar_screen_elements.png": "https://upload.wikimedia.org/wikipedia/commons/c/c1/ATC_radar_screen_1.png",
    "atc_enroute_scope_artcc.png": "https://upload.wikimedia.org/wikipedia/commons/1/15/Scope_of_an_ARTCC_controller.png",
    "atc_houston_artcc_workstations.jpg": "https://upload.wikimedia.org/wikipedia/commons/3/30/HoustonARTCC.JPG"
}

for fname, url in autotrac_urls.items():
    out_file = os.path.join(AUTOTRAC_DIR, fname)
    download_file(url, out_file)

print("\nAll downloads and renders completed!")
