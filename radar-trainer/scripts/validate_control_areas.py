"""Validate reviewed control-area files, including arc geometry, without API calls."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from airport_profiles import get_profile
from control_area import DATA, ControlAreas

if __name__ == '__main__':
    for path in sorted(DATA.glob('*.json')):
        model = ControlAreas(get_profile(path.stem))
        print(f'{path.stem}: {len(model.areas)} validated volumes')
