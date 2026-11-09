"""Compatibility facade; airport data lives in data/airports/VOCB.json."""
from airport_profiles import get_profile
_profile = get_profile('VOCB')
ICAO, NAME, LAT, LON = _profile.ICAO, _profile.NAME, _profile.LAT, _profile.LON
THRESHOLDS = _profile.THRESHOLDS
COURSE, GLIDE_ANGLE, RDH_FT = _profile.COURSE, _profile.GLIDE_ANGLE, _profile.RDH_FT
INTERCEPT_ALT_FT, FT_PER_NM = _profile.INTERCEPT_ALT_FT, _profile.FT_PER_NM
ELEVATION_FT = _profile.data['elevation_ft']
to_nm, nav, aircraft = _profile.to_nm, _profile.nav, _profile.aircraft
approach_point, approach_geometry = _profile.approach_point, _profile.approach_geometry
glide_altitude, navaids, approach_nav = _profile.glide_altitude, _profile.navaids, _profile.approach_nav
