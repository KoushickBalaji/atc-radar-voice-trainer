import os
import shutil

BASE_DIR = 'd:/ATC/design/ui-references'
INDRA_DIR = os.path.join(BASE_DIR, 'indra-aircon-2100')
STARS_DIR = os.path.join(BASE_DIR, 'raytheon-stars')
AUTOTRAC_DIR = os.path.join(BASE_DIR, 'raytheon-autotrac')

# 1. Clean raytheon-stars
bad_stars = [
    os.path.join(STARS_DIR, 'stars_tracon_workstation_faa.jpg'),
    os.path.join(STARS_DIR, 'vstars_operational_scope.jpg')
]
for f in bad_stars:
    if os.path.exists(f):
        os.remove(f)
        print(f"Removed bad file: {os.path.basename(f)}")

# Add verified real STARS photos
shutil.copy('d:/ATC/design/test_rtx_stars.jpg', os.path.join(STARS_DIR, 'raytheon_stars_cwp_console.jpg'))
shutil.copy('d:/ATC/design/test_tracon_dfw.gif', os.path.join(STARS_DIR, 'faa_tracon_radar_facility.gif'))
print("Added verified STARS console and TRACON photos.")

# 2. Clean raytheon-autotrac
bad_autotrac = [
    os.path.join(AUTOTRAC_DIR, 'atc_houston_artcc_workstations.jpg'),
    os.path.join(AUTOTRAC_DIR, 'atc_enroute_scope_artcc.png'),
    os.path.join(AUTOTRAC_DIR, 'atc_radar_screen_elements.png')
]
for f in bad_autotrac:
    if os.path.exists(f):
        os.remove(f)
        print(f"Removed bad file: {os.path.basename(f)}")

# Add verified real AutoTrac photos
shutil.copy('d:/ATC/design/test_autotrac_platform.jpg', os.path.join(AUTOTRAC_DIR, 'raytheon_autotrac_controller_position.jpg'))
shutil.copy('d:/ATC/design/test_atc_operations.jpg', os.path.join(AUTOTRAC_DIR, 'raytheon_nextgen_atm_operations_center.jpg'))
shutil.copy('d:/ATC/design/test_caps_video_poster.jpg', os.path.join(AUTOTRAC_DIR, 'raytheon_caps_atm_overview.jpg'))
print("Added verified Raytheon AutoTrac & ATM operations photos.")

# Clean test files from design root
for f in [
    'd:/ATC/design/test_crop.png',
    'd:/ATC/design/test_crop_obj1.png',
    'd:/ATC/design/test_rtx_stars.jpg',
    'd:/ATC/design/test_tracon_dfw.gif',
    'd:/ATC/design/test_autotrac_platform.jpg',
    'd:/ATC/design/test_atc_operations.jpg',
    'd:/ATC/design/test_caps_video_poster.jpg'
]:
    if os.path.exists(f):
        os.remove(f)

print("Cleanup complete!")
