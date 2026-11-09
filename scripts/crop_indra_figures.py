import pypdfium2 as pdfium
from PIL import Image
import os

pdf = pdfium.PdfDocument('d:/ATC/design/MANUAL_SDD_2014.pdf')
out_dir = 'd:/ATC/design/ui-references/indra-aircon-2100'
os.makedirs(out_dir, exist_ok=True)

# List of figures to extract with (page_number_1_based, output_filename, padding)
figures_to_extract = [
    (39, "indra_sdd_screen_overview.png"),
    (49, "indra_extended_track_label.png"),
    (56, "indra_leader_line.png"),
    (58, "indra_history_velocity_vector.png"),
    (60, "indra_callsign_menu.png"),
    (65, "indra_stca_warning_alert.png"),
    (67, "indra_mtcd_conflict_zones.png"),
    (72, "indra_apw_proximity_alert.png"),
    (74, "indra_msaw_alert_list.png"),
    (76, "indra_clam_ram_heading_alerts.png"),
    (77, "indra_rie_alarm.png"),
    (217, "indra_main_menu_toolbar.png"),
    (224, "indra_executive_flight_list.png"),
    (227, "indra_planner_flight_list.png"),
    (234, "indra_arrival_flight_plan_list.png"),
    (237, "indra_departure_flight_plan_list.png"),
]

scale = 2.5 # crisp high-res

for pno, fname in figures_to_extract:
    page = pdf[pno - 1]
    w_pts, h_pts = page.get_size()
    image_objs = [obj for obj in page.get_objects() if obj.type == 3]
    if not image_objs:
        print(f"No image objs on page {pno}")
        continue
    
    # Bounding box in PDF coords (bottom-left origin)
    min_x = min(obj.get_bounds()[0] for obj in image_objs)
    min_y = min(obj.get_bounds()[1] for obj in image_objs)
    max_x = max(obj.get_bounds()[2] for obj in image_objs)
    max_y = max(obj.get_bounds()[3] for obj in image_objs)
    
    # Add a slight 6pt padding
    pad = 6
    min_x = max(0, min_x - pad)
    min_y = max(0, min_y - pad)
    max_x = min(w_pts, max_x + pad)
    max_y = min(h_pts, max_y + pad)
    
    # Render page
    page_img = page.render(scale=scale).to_pil()
    
    # Convert to PIL coords (top-left origin)
    crop_x0 = int(min_x * scale)
    crop_x1 = int(max_x * scale)
    crop_y0 = int((h_pts - max_y) * scale)
    crop_y1 = int((h_pts - min_y) * scale)
    
    cropped = page_img.crop((crop_x0, crop_y0, crop_x1, crop_y1))
    target_path = os.path.join(out_dir, fname)
    cropped.save(target_path)
    print(f"Extracted {fname:35} from Page {pno:3d} | Size: {cropped.size}")

print("Indra extraction complete!")
